"""Point-in-time leakage test for TradingAgents tools: trade_date fixed, model 'asks' for later dates."""
import re, json, sys, inspect
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.config import set_config
from tradingagents.agents import tools as T
cfg = DEFAULT_CONFIG.copy(); cfg["data_cache_dir"]="/workspace/fin-llm-eval/results/ta_cache"; set_config(cfg)
TD = sys.argv[1] if len(sys.argv)>1 else "2026-08-20"
LATE = "2026-10-07"
DATE = re.compile(r"(20\d\d-\d\d-\d\d)")
def check(name, fn, **kw):
    try:
        out = str(fn.func(**kw))
    except Exception as e:
        out = f"EXC {e!r}"
    ds = sorted(set(DATE.findall(out)))
    late = [d for d in ds if d > TD]
    print(json.dumps(dict(tool=name, trade_date=TD, chars=len(out), max_date=ds[-1] if ds else None,
                          dates_after_trade_date=late[:8], head=out[:160].replace("\n"," | "))))
for sym in ["NVDA", "SOL-USD"]:
    print("=====", sym)
    check("get_stock_data", T.get_stock_data, symbol=sym, start_date="2026-08-01", end_date=LATE, trade_date=TD)
    check("get_indicators(rsi)", T.get_indicators, symbol=sym, indicator="rsi", curr_date=LATE, look_back_days=10, trade_date=TD)
    check("get_verified_market_snapshot", T.get_verified_market_snapshot, symbol=sym, curr_date=LATE, look_back_days=5, trade_date=TD)
    check("get_fundamentals", T.get_fundamentals, ticker=sym, curr_date=LATE, trade_date=TD)
    check("get_income_statement", T.get_income_statement, ticker=sym, freq="quarterly", curr_date=LATE, trade_date=TD)
    check("get_news", T.get_news, **{k:v for k,v in dict(ticker=sym, symbol=sym, start_date="2026-08-10", end_date=LATE, trade_date=TD).items() if k in inspect.signature(T.get_news.func).parameters})
    check("get_global_news", T.get_global_news, **{k:v for k,v in dict(curr_date=LATE, look_back_days=7, limit=5, trade_date=TD).items() if k in inspect.signature(T.get_global_news.func).parameters})
    check("get_insider_transactions", T.get_insider_transactions, **{k:v for k,v in dict(ticker=sym, curr_date=LATE, trade_date=TD).items() if k in inspect.signature(T.get_insider_transactions.func).parameters})
print("===== macro/prediction")
check("get_macro_indicators(cpi)", T.get_macro_indicators, indicator="cpi", curr_date=LATE, trade_date=TD)
check("get_prediction_markets", T.get_prediction_markets, topic="Fed rate cut", limit=3, trade_date=TD)
