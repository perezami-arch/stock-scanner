"""ai-hedge-fund persona agents (blind, point-in-time) as approve/veto filter on the scanner's STOCK setups.
Same code as the box run (../../aihf_bt on the box). Data = SEC EDGAR as filed <= trade_date + Yahoo closes <= trade_date
(replaces the Financial Datasets API, which needs a key). LLM = local Ollama.
Usage (from laptop-run):  .venv\\Scripts\\python aihf\\run_aihf.py druckenmiller [--model qwen25-7b-q4km] [--limit 0]
Resumable: one JSON line per setup in results\\aihf_<persona>_<model>.jsonl."""
import sys, os, json, time, argparse, requests, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(1, os.path.dirname(HERE)); import nightwin   # night-window/AC guard + crash-safe append
import keepawake; keepawake.hold()   # no idle sleep while this runs standalone; reset at exit
from edgar_client import EdgarClient
from hedge_fund.llm.cache import PromptCache
from hedge_fund.features.snapshot import build_snapshot
from hedge_fund.signals.druckenmiller import DruckenmillerAgent
from hedge_fund.signals.buffett import BuffettAgent
ap = argparse.ArgumentParser(); ap.add_argument('persona', choices=['druckenmiller', 'buffett'])
ap.add_argument('--model', default='qwen25-7b-q4km'); ap.add_argument('--limit', type=int, default=0)
ap.add_argument('--host', default=os.getenv('OLLAMA_HOST_URL', 'http://localhost:11434')); a = ap.parse_args()
class OllamaLLM:
    model = a.model
    def __init__(self): self.last = {}
    def complete(self, system, user):
        r = requests.post(f'{a.host}/api/chat', timeout=900, json=dict(model=a.model, stream=False, format='json',
            messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], options=dict(temperature=0.2, num_predict=400)))
        r.raise_for_status(); j = r.json()
        self.last = dict(pt=j.get('prompt_eval_count'), ct=j.get('eval_count'), secs=j.get('total_duration', 0) / 1e9)
        return j['message']['content']
RES = os.path.join(os.path.dirname(HERE), 'results'); os.makedirs(RES, exist_ok=True)
OUT = os.path.join(RES, f'aihf_{a.persona}_{a.model}.jsonl')
def _done_ids(p):
    ids = set()
    if os.path.exists(p):
        for l in open(p, encoding='utf-8'):
            try: ids.add(json.loads(l)['setup_id'])
            except Exception: pass   # tolerate a fragment left by a hard kill
    return ids
done = _done_ids(OUT)
S = pd.read_csv(os.path.join(os.path.dirname(HERE), 'setups_846.csv'))
S = S[(S.asset == 'stock') & S.skip_reason.isna()].sort_values('priority')
if a.limit: S = S.head(a.limit)
client = EdgarClient(); llm = OllamaLLM()
agent = {'druckenmiller': DruckenmillerAgent, 'buffett': BuffettAgent}[a.persona](llm=llm, cache=PromptCache(os.path.join(RES, 'aihf_cache', f'prompts_{a.persona}_{a.model}')), blind=True, breakpoints=None)
agent.build_snapshot = lambda t, d, dc: build_snapshot(t, d, dc, periods=8, breakpoints=None)   # no size percentile (needs paid data)
for _, r in S.iterrows():
    if r.setup_id in done: continue
    why = nightwin.block_reason(2)
    if why: print('paused:', why, flush=True); sys.exit(3)
    t0 = time.time(); n0 = len(client.audit); llm.last = {}
    try:
        sig = agent.predict(str(r.ticker).replace('.', '-'), r.trade_date, client)
        rec = dict(ok=True, value=sig.value, signal=sig.metadata.get('signal'), confidence=sig.metadata.get('confidence'),
                   abstained=sig.metadata.get('abstained'), reason=sig.reasoning[:600])
    except Exception as e:
        rec = dict(ok=False, error=repr(e)[:300])
    used = client.audit[n0:]
    rec.update(setup_id=r.setup_id, priority=int(r.priority), ticker=r.ticker, direction=r.direction, trade_date=r.trade_date,
               max_data_date=max([u[2] for u in used], default=None), leak=any(u[2] > r.trade_date for u in used),
               runtime_s=round(time.time() - t0, 1), **{f'llm_{k}': v for k, v in llm.last.items()})
    nightwin.append_jsonl(OUT, rec)
    print(rec['priority'], r.ticker, r.direction, rec.get('signal'), rec.get('confidence'), rec['runtime_s'], rec.get('error', ''), flush=True)
