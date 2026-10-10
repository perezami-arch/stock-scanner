import json, re, sys, glob, os
E={i['id']:i for i in json.load(open('/workspace/fin-llm-eval/eval/evalset.json'))['items']}
def strip_think(t):
    t=re.sub(r'<think>.*?</think>','',t,flags=re.S)
    if '<think>' in t: t=''  # unterminated think = no answer
    return t
def extract(t):
    t=strip_think(t)
    m=re.findall(r'FINAL ANSWER\W*[:：]?\s*\**\s*\$?\s*(-?[\d,]*\.?\d+)',t,flags=re.I)
    if m: return float(m[-1].replace(',','')),'final'
    m=re.findall(r'<answer>(.*?)</answer>',t,flags=re.S)
    if m:
        n=re.findall(r'-?[\d,]*\.?\d+',m[-1])
        if n: return float(n[-1].replace(',','')),'answer_tag'
    m=re.findall(r'\\boxed\{([^}]*)\}',t)
    if m:
        n=re.findall(r'-?[\d,]*\.?\d+',m[-1])
        if n: return float(n[-1].replace(',','')),'boxed'
    return None,'none'
def ok(pred,gold,kind):
    if pred is None: return False
    cands=[pred]
    if kind=='pct': cands+= [pred*100]   # accept 0.1649 for 16.49%
    for p in cands:
        if abs(p-gold)<=(0.06 if kind=='pp' else max(0.005*abs(gold),0.006)): return True
    return False
def score(path):
    d=json.load(open(path)); rows=[]; gen_tok=0; gen_s=0; trunc=0; n=0; c=0
    for r in d['results']:
        it=E[r['id']]
        for i,t in enumerate(r['turns']):
            gen_tok+=t['eval_count'] or 0; gen_s+=t['eval_s'] or 0
            if t['done_reason']=='length': trunc+=1
        if it['kind']=='qual': rows.append((r['id'],'qual',None,None,None)); continue
        golds=it['answers'] if it['kind']=='multi' else [it['answer']]
        for i,g in enumerate(golds):
            t=r['turns'][i]; txt=(t['text'] or '')
            p,how=extract(txt)
            k='pct' if (it['kind']=='multi' and i==1) else ('num' if it['kind']=='multi' else it['kind'])
            good=ok(p,g,k); n+=1; c+=good
            rows.append((r['id']+(f'_t{i+1}' if it['kind']=='multi' else ''),k,g,p,good,how,t['done_reason'],t['eval_count']))
    return dict(model=d['model'],n=n,correct=c,acc=c/n if n else 0,avg_tok=gen_tok/max(1,sum(len(r['turns']) for r in d['results'])),
                tok_s=gen_tok/gen_s if gen_s else 0,truncated=trunc,peak_rss_gb=d['peak_rss_kb']/1024/1024,rows=rows)
if __name__=='__main__':
    out={}
    for p in sorted(glob.glob('/workspace/fin-llm-eval/results/*.json')):
        if p.endswith(('summary.json','speed.json')): continue
        s=score(p); out[s['model']]=s
        print(f"{s['model']}: {s['correct']}/{s['n']} ({s['acc']:.0%}) avg_tok={s['avg_tok']:.0f} tok/s={s['tok_s']:.2f} trunc={s['truncated']} peakRSS={s['peak_rss_gb']:.2f}GB")
        for r in s['rows']:
            if r[1]!='qual': print('   ',r)
    json.dump(out,open('/workspace/fin-llm-eval/results/summary.json','w'),indent=1)
