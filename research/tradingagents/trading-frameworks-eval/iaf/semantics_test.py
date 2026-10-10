"""Probe IAF event-backtest timing semantics with synthetic data (open=day*10, close=day*10+5)."""
import sys, logging, pandas as pd, numpy as np
from datetime import datetime, timezone
import investing_algorithm_framework as iaf
from investing_algorithm_framework import (create_app, TradingStrategy, TimeUnit, DataSource, PandasOHLCVDataProvider,
    BacktestDateRange, PortfolioConfiguration, OrderSide)
logging.disable(logging.WARNING)
LABEL_HOUR=int(sys.argv[1]) if len(sys.argv)>1 else 0
idx=pd.date_range('2026-06-01',periods=60,freq='D')+pd.Timedelta(hours=LABEL_HOUR)
n=np.arange(60)
df=pd.DataFrame({'Datetime':idx,'Open':100+n*10.,'High':100+n*10+8.,'Low':100+n*10-2.,'Close':100+n*10+5.,'Volume':1e6})
LOG=[]
class S(TradingStrategy):
    time_unit=TimeUnit.DAY; interval=1; symbols=['TST']; trading_symbol='USD'
    data_sources=[DataSource(identifier='tst',data_type='OHLCV',symbol='TST/USD',time_frame='1d',market='SIM',window_size=5)]
    def run_strategy(self, context, data):
        d=data['tst']; last=d.tail(1)
        now=context.config.get('INDEX_DATETIME')
        LOG.append((str(now), str(last['Datetime'][0]), float(last['Close'][0])))
        if len(LOG)==3 and not context.has_position('TST'):
            context.create_market_order(target_symbol='TST', order_side=OrderSide.BUY, amount=1)
app=create_app(name='sem'); app.add_strategy(S())
app.add_data_provider(PandasOHLCVDataProvider(dataframe=df,symbol='TST/USD',time_frame='1d',market='SIM',window_size=5))
app.add_portfolio_configuration(PortfolioConfiguration(market='SIM',trading_symbol='USD',initial_balance=10000))
start=datetime(2026,6,10,int(sys.argv[2]) if len(sys.argv)>2 else 0,tzinfo=timezone.utc); end=datetime(2026,6,20,tzinfo=timezone.utc)
bt=app.run_backtest(backtest_date_range=BacktestDateRange(start_date=start,end_date=end), initial_amount=10000, show_progress=False)
for l in LOG[:6]: print('index',l[0],'| last bar in window',l[1],'close',l[2])
for run in bt.get_all_backtest_runs():
    for o in run.orders: print('ORDER', o.order_side, o.status, 'created', o.created_at, 'updated', o.updated_at, 'price', o.price)
    for t in run.trades: print('TRADE open', t.opened_at, 'price', t.open_price)
