"""Run evalset against an Ollama model; record answers, tokens/s, peak RSS of the runner."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import json, sys, time, re, threading, os, subprocess, urllib.request
MODEL=sys.argv[1]; OUT=sys.argv[2]; NUM_PREDICT=int(sys.argv[3]) if len(sys.argv)>3 else 2048
ONLY=sys.argv[4].split(',') if len(sys.argv)>4 else None
E=json.load(open((_SCANNER_ROOT + '/fin-llm-eval/eval/evalset.json')))
SYS="Answer in English."
INSTR=("Show your calculation briefly, then on the last line write 'FINAL ANSWER: <number>' "
       "(a plain number only; percentages as a number of percent, e.g. 12.34 for 12.34%; round to 2 decimals).")
peak={'rss':0}; stop=False
def runner_pids():
    out=subprocess.run("pgrep -f 'lib/ollama/llama-server'",shell=True,capture_output=True,text=True).stdout.split()
    return [int(p) for p in out]
def sampler():
    while not stop:
        tot=0
        for p in runner_pids():
            try:
                for l in open(f'/proc/{p}/status'):
                    if l.startswith('VmRSS'): tot+=int(l.split()[1])
            except Exception: pass
        peak['rss']=max(peak['rss'],tot); time.sleep(0.5)
def chat(msgs):
    body=dict(model=MODEL,messages=msgs,stream=False,
              options=dict(temperature=0.3,num_predict=NUM_PREDICT,num_ctx=4096,num_thread=int(os.environ.get("NT","4")),seed=42))
    req=urllib.request.Request('http://127.0.0.1:11434/api/chat',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    t=time.time(); r=json.load(urllib.request.urlopen(req,timeout=3600)); r['_wall']=time.time()-t; return r
threading.Thread(target=sampler,daemon=True).start()
res=[]
done=set()
if os.path.exists(OUT):
    res=json.load(open(OUT))['results']; done={x['id'] for x in res}
for it in E['items']:
    if ONLY and it['id'] not in ONLY: continue
    if it['id'] in done: continue
    msgs=[{"role":"system","content":SYS}]
    turns_out=[]
    for i,t in enumerate(it['turns']):
        if it['type'] in ('table','multiturn') or it.get('table'):
            content=(E['table']+"\n\n"+t) if i==0 else t
        else: content=t
        if it['kind']!='qual': content+="\n\n"+INSTR
        msgs.append({"role":"user","content":content})
        r=chat(msgs)
        txt=r['message']['content']; think=r['message'].get('thinking','')
        msgs.append({"role":"assistant","content":txt})
        turns_out.append(dict(text=txt,thinking=think,eval_count=r.get('eval_count'),eval_s=r.get('eval_duration',0)/1e9,
                              prompt_count=r.get('prompt_eval_count'),prompt_s=r.get('prompt_eval_duration',0)/1e9,
                              wall=r['_wall'],done_reason=r.get('done_reason')))
        print(f"[{MODEL}] {it['id']} t{i}: {r.get('eval_count')} tok in {r['_wall']:.0f}s ({r.get('done_reason')})",flush=True)
    res.append(dict(id=it['id'],turns=turns_out))
    json.dump(dict(model=MODEL,num_predict=NUM_PREDICT,peak_rss_kb=peak['rss'],results=res),open(OUT,'w'),indent=1,ensure_ascii=False)
stop=True
d=json.load(open(OUT)); d['peak_rss_kb']=max(d.get('peak_rss_kb',0),peak['rss']); json.dump(d,open(OUT,'w'),indent=1,ensure_ascii=False)
print("DONE",MODEL)
