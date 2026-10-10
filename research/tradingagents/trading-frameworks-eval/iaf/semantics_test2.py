"""Probe 2: stop-loss exit timing. Rising series, then on bar 2026-06-16 open=300 close=200 (crash intraday), next bar open=150."""
import sys, logging, pandas as pd, numpy as np
from datetime import datetime, timezone
from investing_algorithm_framework import (create_app, TradingStrategy, TimeUnit, DataSource, PandasOHLCVDataProvider,
    BacktestDateRange, PortfolioConfiguration, OrderSide)
logging.disable(logging.WARNING)
idx=pd.date_range('2026-06-01',periods=40,freq='D')
o=[]; c=[]
for i,d in enumerate(idx):
    if d<pd.Timestamp('2026-06-16'): o.append(250+i); c.append(252+i)
    elif d==pd.Timestamp('2026-06-16'): o.append(300.); c.append(200.)
    else: o.append(150.); c.append(150.)
df=pd.DataFrame({'Datetime':idx,'Open':o,'High':np.maximum(o,c)+1,'Low':np.minimum(o,c)-1,'Close':c,'Volume':1e6})
LOG=[]
class S(TradingStrategy):
    time_unit=TimeUnit.DAY; interval=1; symbols=['TST']; trading_symbol='USD'
    data_sources=[DataSource(identifier='tst',data_type='OHLCV',symbol='TST/USD',time_frame='1d',market='SIM',window_size=5)]
    def run_strategy(self, context, data):
        now=context.config.get('INDEX_DATETIME')
        if str(now).startswith('2026-06-12'):
            context.create_market_order(target_symbol='TST', order_side=OrderSide.BUY, amount=1)
        for t in context.get_open_trades():
            if not t.stop_losses:
                context.add_stop_loss(trade=t, percentage=10, trailing=(sys.argv[1]=='trail'))
app=create_app(name='sem2'); app.add_strategy(S())
app.add_data_provider(PandasOHLCVDataProvider(dataframe=df,symbol='TST/USD',time_frame='1d',market='SIM',window_size=5))
app.add_portfolio_configuration(PortfolioConfiguration(market='SIM',trading_symbol='USD',initial_balance=10000))
bt=app.run_backtest(backtest_date_range=BacktestDateRange(start_date=datetime(2026,6,10,tzinfo=timezone.utc),end_date=datetime(2026,6,25,tzinfo=timezone.utc)), initial_amount=10000, show_progress=False)
print(df.iloc[10:19].to_string())
for run in bt.get_all_backtest_runs():
    for o in run.orders: print('ORDER', o.order_side, o.status, 'created', o.created_at, 'price', o.price, 'filled', getattr(o,'filled_at',None))
    for t in run.trades: print('TRADE open', t.opened_at, t.open_price, 'closed', t.closed_at, 'net_gain', t.net_gain)
