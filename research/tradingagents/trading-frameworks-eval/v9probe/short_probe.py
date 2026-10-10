"""IAF v9.0.0a20: does the EVENT engine open/close a short with a trailing stop? Synthetic falling series."""
import logging, pandas as pd, numpy as np
from datetime import datetime, timezone
from investing_algorithm_framework import (create_app, TradingStrategy, TimeUnit, DataSource, PandasOHLCVDataProvider,
    BacktestDateRange, PortfolioConfiguration, OrderSide, Schedule, Study, Universe, BacktestWindow, BacktestEngine, BacktestRunConfiguration)
logging.disable(logging.WARNING)
idx=pd.date_range('2026-06-01',periods=40,freq='D')
c=np.r_[np.full(12,300.), np.linspace(300,240,10), np.linspace(240,290,18)]
o=np.r_[c[0],c[:-1]]
df=pd.DataFrame({'Datetime':idx,'Open':o,'High':np.maximum(o,c)+1,'Low':np.minimum(o,c)-1,'Close':c,'Volume':1e6})
class S(TradingStrategy):
    schedule=Schedule.every(1, TimeUnit.DAY); symbols=['TST']; trading_symbol='USD'
    data_sources=[DataSource(identifier='tst',data_type='OHLCV',symbol='TST/USD',time_frame='1d',market='SIM',window_size=3)]
    def run_strategy(self, context, data):
        now=pd.Timestamp(context.config.get('INDEX_DATETIME'))
        px=float(data['tst']['Close'][-1])
        if now.strftime('%m-%d')=='06-12':
            o=context.create_short_order(target_symbol='TST', price=px, amount=1)
            print('short order', o.order_side, o.status, o.price)
        for t in context.get_open_trades():
            if not t.stop_losses:
                try: context.add_stop_loss(trade=t, percentage=8, trailing=True); print('stop added on', getattr(t,'is_short',None))
                except Exception as e: print('add_stop_loss failed:', e)
app=create_app(name='v9short'); app.add_strategy(S())
app.add_data_provider(PandasOHLCVDataProvider(dataframe=df,symbol='TST/USD',time_frame='1d',market='SIM',window_size=3))
app.add_portfolio_configuration(PortfolioConfiguration(market='SIM',trading_symbol='USD',initial_balance=10000))
study=Study(name='shortprobe',universe=Universe(key='tst',symbols=['TST'],market='SIM',trading_symbol='USD'),initial_capital=10000,
  engines=[BacktestEngine.EVENT_DRIVEN],backtest_windows=[BacktestWindow(name='w',train_range=BacktestDateRange(start_date=datetime(2026,6,10,tzinfo=timezone.utc),end_date=datetime(2026,7,8,tzinfo=timezone.utc)))])
res=app.run_backtest(strategy=None,study=study,run_configuration=BacktestRunConfiguration(backtest_storage_directory='./bt',use_checkpoints=False,show_progress=False))
bts=res.load_backtests(workers=1)
for run in [r for b in bts for r in b.get_all_backtest_runs()]:
    for o in run.orders: print('ORDER', o.order_side, o.status, o.created_at, o.price)
    for t in run.trades: print('TRADE', getattr(t,'is_short',None), t.opened_at, t.open_price, t.closed_at, t.net_gain)
    m=run.backtest_metrics; print('final value', getattr(m,'final_value',None), 'short trades', getattr(m,'number_of_short_trades',None))
