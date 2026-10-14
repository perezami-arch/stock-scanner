import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import sys, os, time, json, traceback, pandas as pd
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from langchain_core.callbacks import BaseCallbackHandler
class Usage(BaseCallbackHandler):
    def __init__(self): self.calls=0; self.pt=0; self.ct=0
    def on_llm_end(self, response, **kw):
        self.calls+=1
        try:
            for gens in response.generations:
                for g in gens:
                    um=getattr(g.message,'usage_metadata',None) or {}
                    self.pt+=um.get('input_tokens',0); self.ct+=um.get('output_tokens',0)
        except Exception: pass
MODEL=sys.argv[1]; START=int(sys.argv[2]); END=int(sys.argv[3])
OUT=(_SCANNER_ROOT + '/fin-llm-eval/backtest/runs'); os.makedirs(OUT,exist_ok=True)
S=pd.read_csv((_SCANNER_ROOT + '/fin-llm-eval/backtest/sample_order.csv'))
for _,r in S[(S.priority>=START)&(S.priority<END)].iterrows():
    f=f"{OUT}/{int(r.priority):03d}_{r.ticker}_{r.trade_date}.json"
    if os.path.exists(f) or os.path.exists((_SCANNER_ROOT + '/fin-llm-eval/backtest/STOP')): continue
    crypto = r.asset=='crypto'
    analysts = ("market",) if crypto else ("market","fundamentals")
    cfg=DEFAULT_CONFIG.copy()
    cfg.update(llm_provider="ollama", backend_url="http://127.0.0.1:11434/v1", deep_think_llm=MODEL, quick_think_llm=MODEL,
               max_debate_rounds=1, max_risk_discuss_rounds=1, temperature=0.3, max_tokens=int(os.environ.get("MAXTOK","500")), max_tool_rounds=3,
               news_article_limit=8, global_news_article_limit=5,
               results_dir=f"{OUT}/logs", data_cache_dir=(_SCANNER_ROOT + "/fin-llm-eval/results/ta_cache"),
               memory_log_path=f"{OUT}/mem/{int(r.priority):03d}.md")   # fresh memory per run: no cross-run outcome leakage
    t0=time.time(); rec=dict(r.to_dict(), model=MODEL, analysts=list(analysts))
    try:
        U=Usage(); ta=TradingAgentsGraph(selected_analysts=analysts, debug=False, config=cfg, callbacks=[U])
        state,dec=ta.propagate(r.ticker, r.trade_date, asset_type="crypto" if crypto else "stock")
        rec.update(ok=True, decision=str(dec))
        rec['final_trade_decision']=str(state.get('final_trade_decision',''))[:4000]
        rec['trader_plan']=str(state.get('trader_investment_plan',''))[:2000]
        rec['investment_plan']=str(state.get('investment_plan',''))[:2000]
        rec['fundamentals_report']=str(state.get('fundamentals_report',''))[:2500]
        ids=state.get('investment_debate_state') or {}
        rec['bull']=str(ids.get('bull_history',''))[-1500:]; rec['bear']=str(ids.get('bear_history',''))[-1500:]
        rec['final_rating']=str(state.get('final_rating',''))
        rec['market_report']=str(state.get('market_report',''))[:3000]
    except Exception as e:
        rec.update(ok=False, error=repr(e)[:500], tb=traceback.format_exc()[-2000:])
    rec['runtime_s']=round(time.time()-t0,1)
    try: rec.update(llm_calls=U.calls,prompt_tokens=U.pt,completion_tokens=U.ct)
    except Exception: pass
    json.dump(rec,open(f,'w'),indent=1,default=str,ensure_ascii=False)
    print(int(r.priority), r.ticker, r.trade_date, rec.get('decision'), rec['runtime_s'], rec.get('error',''), flush=True)
