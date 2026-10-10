# Laptop offline check (no LLM call): TradingAgents import + CalibGraph context injection with the laptop's TA version.
import os, sys; sys.path.insert(0, r"C:\ta-backtest"); os.chdir(r"C:\ta-backtest")
import calib_prompt as cp
row = [r for r in cp.load_csv("setups_calib.csv") if r["setup_id"] == "S0410"][0]
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
import inspect
class CalibGraph(TradingAgentsGraph):
    def resolve_instrument_context(self, ticker, asset_type="stock", trade_date=None):
        return super().resolve_instrument_context(ticker, asset_type, trade_date) + cp.instrument_addendum(row)
cfg = DEFAULT_CONFIG.copy(); cfg.update(llm_provider="ollama", backend_url="http://127.0.0.1:9/v1", deep_think_llm="x", quick_think_llm="x",
    results_dir=os.path.join(os.environ["TEMP"], "calibchk"), data_cache_dir=os.path.join(os.environ["TEMP"], "calibchk"),
    memory_log_path=os.path.join(os.environ["TEMP"], "calibchk", "m.md"))
g = CalibGraph(selected_analysts=("market",), debug=False, config=cfg)
ctx = g.resolve_instrument_context("ETH-USD", "crypto", row["trade_date"])
print("context chars", len(ctx), "| has setup block:", "SETUP UNDER REVIEW" in ctx)
print("run path calls self.resolve_instrument_context:", "self.resolve_instrument_context" in inspect.getsource(TradingAgentsGraph))
import tradingagents, importlib.metadata as md
print("tradingagents", md.version("tradingagents") if True else "")
