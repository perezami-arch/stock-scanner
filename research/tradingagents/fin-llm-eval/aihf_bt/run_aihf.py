"""ai-hedge-fund persona agents (blind, point-in-time) as approve/veto filter on scanner stock setups.
Data: EdgarClient (SEC EDGAR as filed <= trade_date + Yahoo closes <= trade_date). LLM: local Ollama Qwen2.5-3B.
Usage: run_aihf.py PERSONA N   (resumable; one jsonl line per setup)"""
import sys, os, json, time, requests, pandas as pd
sys.path.insert(0, '/workspace/fin-llm-eval/aihf_bt')
from edgar_client import EdgarClient
from hedge_fund.llm.cache import PromptCache
from hedge_fund.signals.druckenmiller import DruckenmillerAgent
from hedge_fund.signals.buffett import BuffettAgent
MODEL = os.environ.get('AIHF_MODEL', 'qwen25-3b-agent4')
class OllamaLLM:
    model = MODEL
    def __init__(self): self.last = {}
    def complete(self, system, user):
        r = requests.post('http://127.0.0.1:11434/api/chat', timeout=1800, json=dict(model=MODEL, stream=False, format='json',
            messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            options=dict(temperature=0.2, num_predict=300)))
        r.raise_for_status(); j = r.json()
        self.last = dict(pt=j.get('prompt_eval_count'), ct=j.get('eval_count'), secs=j.get('total_duration', 0) / 1e9)
        return j['message']['content']
P = {'druckenmiller': DruckenmillerAgent, 'buffett': BuffettAgent}
persona, N = sys.argv[1], int(sys.argv[2])
OUT = f'/workspace/fin-llm-eval/aihf_bt/{persona}.jsonl'
done = {json.loads(l)['setup_id'] for l in open(OUT)} if os.path.exists(OUT) else set()
S = pd.read_csv('/workspace/fin-llm-eval/backtest/sample_order.csv'); S = S[S.asset == 'stock'].head(N)
client = EdgarClient(); llm = OllamaLLM()
agent = P[persona](llm=llm, cache=PromptCache(f'/workspace/fin-llm-eval/aihf_bt/cache_{persona}'), blind=True, breakpoints=None)
# blind=True withholds ticker/dates/$ size; breakpoints=None -> no size percentile (needs FD data)
agent._breakpoints = None
from hedge_fund.features.snapshot import build_snapshot
agent.build_snapshot = lambda t, d, dc: build_snapshot(t, d, dc, periods=8, breakpoints=None)
for _, r in S.iterrows():
    if r.setup_id in done or os.path.exists('/workspace/fin-llm-eval/aihf_bt/STOP'): continue
    t0 = time.time(); n0 = len(client.audit); llm.last = {}
    try:
        sig = agent.predict(r.ticker.replace('.', '-'), r.trade_date, client)
        rec = dict(ok=True, value=sig.value, signal=sig.metadata.get('signal'), confidence=sig.metadata.get('confidence'),
                   abstained=sig.metadata.get('abstained'), reason=sig.reasoning[:600])
    except Exception as e:
        rec = dict(ok=False, error=repr(e)[:300])
    used = client.audit[n0:]
    rec.update(setup_id=r.setup_id, priority=int(r.priority), ticker=r.ticker, direction=r.direction, trade_date=r.trade_date,
               platform=r.platform, stratum=r.stratum, max_data_date=max([u[2] for u in used], default=None),
               leak=any(u[2] > r.trade_date for u in used), runtime_s=round(time.time() - t0, 1), **{f'llm_{k}': v for k, v in llm.last.items()})
    open(OUT, 'a').write(json.dumps(rec, default=str) + '\n')
    print(rec['priority'], r.ticker, r.direction, rec.get('signal'), rec.get('confidence'), rec.get('abstained'), rec['runtime_s'], rec.get('error', ''), flush=True)
