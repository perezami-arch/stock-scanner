import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import sys, time, json, os, traceback
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from langchain_core.callbacks import BaseCallbackHandler
class Usage(BaseCallbackHandler):
    def __init__(self): self.calls=0; self.pt=0; self.ct=0
    def on_llm_end(self, response, **kw):
        self.calls+=1
        for gens in response.generations:
            for g in gens:
                um=getattr(g.message,'usage_metadata',None) or {}
                self.pt+=um.get('input_tokens',0); self.ct+=um.get('output_tokens',0)
U=Usage()
ticker, date, model = sys.argv[1], sys.argv[2], sys.argv[3]
analysts = tuple(sys.argv[4].split(',')) if len(sys.argv) > 4 else ("market","social","news","fundamentals")
cfg = DEFAULT_CONFIG.copy()
cfg.update(llm_provider="ollama", backend_url="http://127.0.0.1:11434/v1",
           deep_think_llm=model, quick_think_llm=model, max_debate_rounds=1, max_risk_discuss_rounds=1,
           temperature=0.3, max_tokens=1500, max_tool_rounds=6, news_article_limit=8, global_news_article_limit=5,
           results_dir=(_SCANNER_ROOT + "/fin-llm-eval/results/ta_logs"), data_cache_dir=(_SCANNER_ROOT + "/fin-llm-eval/results/ta_cache"),
           memory_log_path=f"{_SCANNER_ROOT}/fin-llm-eval/results/ta_memory_{ticker}_{date}.md", output_language="English")
t0 = time.time()
out = dict(ticker=ticker, date=date, model=model, analysts=list(analysts))
try:
    ta = TradingAgentsGraph(selected_analysts=analysts, debug=True, config=cfg, callbacks=[U])
    state, decision = ta.propagate(ticker, date)
    out.update(ok=True, decision=str(decision))
    keep = {}
    for k, v in state.items():
        if isinstance(v, str): keep[k] = v
        elif isinstance(v, dict): keep[k] = {kk: vv for kk, vv in v.items() if isinstance(vv, str)}
    out["state"] = keep
except Exception as e:
    out.update(ok=False, error=repr(e), tb=traceback.format_exc()[-3000:])
out["runtime_s"] = round(time.time() - t0, 1); out.update(llm_calls=U.calls, prompt_tokens=U.pt, completion_tokens=U.ct)
json.dump(out, open(f"{_SCANNER_ROOT}/fin-llm-eval/results/ta_{ticker}_{date}.json", "w"), indent=1, default=str)
print("RESULT", json.dumps({k: out[k] for k in ("ticker","date","ok","runtime_s") }), out.get("decision"), out.get("error"))
