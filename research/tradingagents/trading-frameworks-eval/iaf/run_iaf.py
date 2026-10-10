"""Replay scanner setups (longs) through IAF v8 event-driven backtester.
usage: run_iaf.py <asset: stock|crypto> <policy: hold|fsetup|f8|t5|t8|t12> [limit]
Timing design (see results.md): bars are labelled by *their own close* on a gap-free clock
(stocks: trading-day clock compressed to consecutive synthetic days; crypto: UTC days).
An order for a setup is submitted at the label of its entry bar e (= first session that opens after
the alert was provably known); IAF fills market orders at the Open of the first bar with label >= order
time, i.e. the Open of bar e.  Decisions come from the precomputed point-in-time table, never from
IAF's data window (which would expose bar e's close at that moment)."""
import sys, re, time, json, logging, warnings, pandas as pd, numpy as np
from datetime import datetime, timezone, timedelta
warnings.filterwarnings('ignore'); logging.disable(logging.WARNING)
from investing_algorithm_framework import (create_app, TradingStrategy, TimeUnit, DataSource, PandasOHLCVDataProvider,
    BacktestDateRange, PortfolioConfiguration, OrderSide, SimulationBlotter, FixedBasisPointsSlippage, PercentageCommission)
ASSET=sys.argv[1]; POL=sys.argv[2]; LIMIT=int(sys.argv[3]) if len(sys.argv)>3 else None
OUT='/workspace/trading-frameworks-eval/iaf/'
COST={'stock':dict(fee=0.02, slip=0.05), 'crypto':dict(fee=0.10, slip=0.10)}[ASSET]   # percent per side
POLICY={'hold':None,'fsetup':('setup',False),'f8':(8,False),'t5':(5,True),'t8':(8,True),'t12':(12,True)}[POL]
D=pd.read_pickle(OUT+'setups_prepared.pkl'); F=pd.read_pickle(OUT+'frames.pkl')
crypto=(ASSET=='crypto')
S=D[D.has_data & (D.asset==ASSET) & (D.direction=='LONG') & D.decision_utc.notna()].copy()
# build clock
if crypto:
    cal=pd.date_range('2026-05-01','2026-10-07',freq='D')
    open_utc=lambda d: d                     # UTC day bar opens 00:00
else:
    allidx=sorted(set().union(*[set(x.index) for (t,c),x in F.items() if not c]))
    cal=pd.DatetimeIndex([d for d in allidx if d>=pd.Timestamp('2026-05-01')])
    open_utc=lambda d: d+pd.Timedelta(hours=13,minutes=30)   # NYSE open (EDT, valid May-Oct)
BASE=pd.Timestamp('2030-01-01')   # synthetic clock: bar k -> BASE + k days (labels = bar close)
lab={d:BASE+pd.Timedelta(days=k) for k,d in enumerate(cal)}
opens=np.array([open_utc(d) for d in cal],dtype='datetime64[ns]')
def entry_bar(dec):
    k=int(np.searchsorted(opens, np.datetime64(dec), side='left'))   # first bar whose open >= decision time
    return k if k<len(cal) else None
S['entry_k']=S.decision_utc.map(entry_bar)
S['entry_date']=S.entry_k.map(lambda k: cal[int(k)] if pd.notna(k) else pd.NaT)
S=S[S.entry_k.notna() & (S.entry_k<len(cal)-1)]
if LIMIT: S=S.head(LIMIT)
def sym(t): return re.sub('[^A-Z0-9]','',str(t).upper())[:20]
S['sym']=S.ticker.map(sym)
tickers=sorted(S.ticker.unique())
providers=[]; sources=[]
for t in tickers:
    x=F[(t,crypto)].reindex(cal)
    x['Close']=x.Close.ffill().bfill()
    for c in ('Open','High','Low'): x[c]=x[c].fillna(x.Close)
    x['Volume']=x.Volume.fillna(0)
    x.index=[lab[d] for d in cal]; x.index.name='Datetime'
    s=sym(t)
    providers.append(PandasOHLCVDataProvider(dataframe=x.reset_index(),symbol=f'{s}/USD',time_frame='1d',market='SIM',window_size=2))
    sources.append(DataSource(identifier=s,data_type='OHLCV',symbol=f'{s}/USD',time_frame='1d',market='SIM',window_size=2))
due={}
PREVCLOSE={}
CL={sym(t):F[(t,crypto)].reindex(cal).Close.ffill().bfill().values for t in tickers}
for _,r in S.iterrows():
    due.setdefault(lab[cal[int(r.entry_k)]],[]).append(r); PREVCLOSE[(r.sym,int(r.entry_k))]=float(CL[r.sym][int(r.entry_k)-1])
ORD={}   # order id -> setup_id
STOPPED=set()
class Replay(TradingStrategy):
    time_unit=TimeUnit.DAY; interval=1; trading_symbol='USD'
    symbols=sorted(S.sym.unique()); data_sources=sources
    def run_strategy(self, context, data):
        now=pd.Timestamp(context.config.get('INDEX_DATETIME')).tz_localize(None)
        if POLICY is not None:
            for t in context.get_open_trades():
                if t.id in STOPPED or (t.stop_losses and len(t.stop_losses)>0): continue
                sid=TRADE2SETUP(t)
                if sid is None: continue
                pct,trail=POLICY
                fill=OPENFILL.get(t.id)
                if fill is None: continue          # not filled yet
                if not trail:
                    # IAF anchors fixed stops on trade.open_price (= estimated price at order creation, not the fill);
                    # convert so the stop LEVEL is exactly fill*(1-p) or the setup's own stop.
                    r=SETUP[sid]
                    if pct=='setup':
                        if r.stop is None or np.isnan(r.stop) or r.stop>=fill: STOPPED.add(t.id); continue   # no valid stop -> hold
                        level=r.stop
                    else: level=fill*(1-pct/100)
                    pct=max(0.01,(1-level/float(t.open_price))*100)
                context.add_stop_loss(trade=t, percentage=float(pct), trailing=trail, sell_percentage=99.999)  # <100: works around IAF float drift ('order amount larger than position'); STOPPED.add(t.id)
        for r in due.get(now,[]):
            amt=round(1000.0/PREVCLOSE[(r.sym,int(r.entry_k))],4)   # size from the last completed close before entry (no lookahead)
            o=context.create_market_order(target_symbol=r.sym, order_side=OrderSide.BUY, amount=amt)
            ORD[o.id]=r.setup_id
SETUP={r.setup_id:r for _,r in S.iterrows()}
OPENFILL={}
def TRADE2SETUP(t):
    for o in (t.orders or []):
        if o.id in ORD:
            if o.price and str(o.status).upper().endswith('CLOSED'): OPENFILL[t.id]=float(o.price)
            return ORD[o.id]
    return None
app=create_app(name=f'replay_{ASSET}_{POL}')
app.add_strategy(Replay())
# NB: in v8 event backtests a SimulationBlotter is auto-installed and strategy-level TradingCost is ignored -> set costs on the blotter
app.set_blotter(SimulationBlotter(slippage_model=FixedBasisPointsSlippage(basis_points=COST['slip']*100), commission_model=PercentageCommission(COST['fee']/100)))
for p in providers: app.add_data_provider(p)
app.add_portfolio_configuration(PortfolioConfiguration(market='SIM',trading_symbol='USD',initial_balance=2_000_000))
k0=int(S.entry_k.min())
start=(BASE+pd.Timedelta(days=k0-1)).to_pydatetime().replace(tzinfo=timezone.utc)
end=(BASE+pd.Timedelta(days=len(cal)-1)).to_pydatetime().replace(tzinfo=timezone.utc)
t0=time.time()
bt=app.run_backtest(backtest_date_range=BacktestDateRange(start_date=start,end_date=end), initial_amount=2_000_000, show_progress=False, fill_missing_data=False)
el=time.time()-t0
rows=[]
inv={v:k for k,v in lab.items()}
last_close={sym(t):float(F[(t,crypto)].reindex(cal).Close.ffill().iloc[-1]) for t in tickers}
for run in bt.get_all_backtest_runs():
    m=run.backtest_metrics
    for t in run.trades:
        sid=None; buy=None; sells=[]
        for o in t.orders:
            if o.id in ORD: sid=ORD[o.id]; buy=o
            elif str(o.order_side).upper().endswith('SELL') and str(o.status).upper().endswith('CLOSED'): sells.append(o)
        if sid is None: continue
        r=SETUP[sid]; ein=float(buy.price); amt=float(buy.filled or buy.amount); efee=float(buy.order_fee or 0)
        if sells:
            so=sells[-1]; ex=float(so.price); xfee=float(so.order_fee or 0); status='stopped'
            exit_at=inv.get(pd.Timestamp(t.closed_at).tz_localize(None).normalize()) if t.closed_at else None
        else:
            ex=last_close[r.sym]*(1-COST['slip']/100); xfee=ex*amt*COST['fee']/100; status='open@end'; exit_at=cal[-1]
        net=(ex*amt-xfee)/(ein*amt+efee)-1
        rows.append(dict(setup_id=sid, policy=POL, iaf_entry_fill=ein, iaf_exit=ex, status=status, entry_date=r.entry_date, exit_date=exit_at,
                         ret_net=net, iaf_trade_open_price=t.open_price, iaf_net_gain=t.net_gain))
R=pd.DataFrame(rows)
R.to_csv(OUT+f'trades_{ASSET}_{POL}.csv',index=False)
meta=dict(asset=ASSET,policy=POL,setups_submitted=len(S),trades_mapped=len(R),symbols=len(tickers),bars=len(cal),
          iterations=int((end-start).days)+1,elapsed_sec=round(el,1),orders_total=len(ORD))
json.dump(meta,open(OUT+f'meta_{ASSET}_{POL}.json','w'),default=str); print(meta)
