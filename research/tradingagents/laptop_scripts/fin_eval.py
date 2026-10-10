"""Financial-report calculation eval (20 scored items) for Ollama models — same prompts as the box run.
Resumable: results/fin_eval_<model>.json is rewritten after every item; finished items are skipped.
Usage: python fin_eval.py qwen25-7b-q4km fin-r1-q4km      (then: python fin_eval.py --score)"""
import json, os, re, sys, time, urllib.request, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, "results"); os.makedirs(RES, exist_ok=True)
E = json.load(open(os.path.join(HERE, "evalset.json"), encoding="utf-8"))
BASE = os.getenv("OLLAMA_HOST_URL", "http://localhost:11434")
NUM_PREDICT = int(os.getenv("FIN_EVAL_NUM_PREDICT", "3000"))   # reasoning models (Fin-R1) think long; 3000 avoids truncation on GPU
SYS = "Answer in English."
INSTR = ("Show your calculation briefly, then on the last line write 'FINAL ANSWER: <number>' "
         "(a plain number only; percentages as a number of percent, e.g. 12.34 for 12.34%; round to 2 decimals).")
def log(m):
    with open(os.path.join(RES, "fin_eval.log"), "a", encoding="utf-8") as f: f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + m + "\n")
    print(m, flush=True)
def chat(model, msgs):
    body = dict(model=model, messages=msgs, stream=False,
                options=dict(temperature=0.3, num_predict=NUM_PREDICT, num_ctx=4096, seed=42))
    req = urllib.request.Request(BASE + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t = time.time(); r = json.load(urllib.request.urlopen(req, timeout=3600)); r["_wall"] = time.time() - t; return r
def gpu_share(model):
    try:
        out = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=20).stdout
        return " ".join(l for l in out.splitlines() if l.startswith(model.split(":")[0]))
    except Exception as e: return f"ollama ps failed: {e}"
def run(model):
    out = os.path.join(RES, f"fin_eval_{model.replace(':', '_').replace('/', '_')}.json")
    res = json.load(open(out, encoding="utf-8"))["results"] if os.path.exists(out) else []
    done = {x["id"] for x in res}; ps = ""
    for it in E["items"]:
        if it["id"] in done: continue
        msgs = [{"role": "system", "content": SYS}]; turns = []
        for i, t in enumerate(it["turns"]):
            content = (E["table"] + "\n\n" + t) if (i == 0 and (it["type"] in ("table", "multiturn") or it.get("table"))) else t
            if it["kind"] != "qual": content += "\n\n" + INSTR
            msgs.append({"role": "user", "content": content})
            r = chat(model, msgs); txt = r["message"]["content"]
            msgs.append({"role": "assistant", "content": txt})
            turns.append(dict(text=txt, thinking=r["message"].get("thinking", ""), eval_count=r.get("eval_count"),
                              eval_s=r.get("eval_duration", 0) / 1e9, prompt_count=r.get("prompt_eval_count"),
                              wall=r["_wall"], done_reason=r.get("done_reason")))
            if not ps: ps = gpu_share(model); log(f"[{model}] ollama ps: {ps}")
            log(f"[{model}] {it['id']} t{i}: {r.get('eval_count')} tok in {r['_wall']:.0f}s ({r.get('done_reason')})")
        res.append(dict(id=it["id"], turns=turns))
        json.dump(dict(model=model, num_predict=NUM_PREDICT, ollama_ps=ps, results=res), open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return out
# ---- scoring (identical rules to the box run) ----
def strip_think(t):
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.S)
    return "" if "<think>" in t else t
def extract(t):
    t = strip_think(t)
    m = re.findall(r"FINAL ANSWER\W*[:：]?\s*\**\s*\$?\s*(-?[\d,]*\.?\d+)", t, flags=re.I)
    if m: return float(m[-1].replace(",", ""))
    for pat in (r"<answer>(.*?)</answer>", r"\\boxed\{([^}]*)\}"):
        m = re.findall(pat, t, flags=re.S)
        if m:
            n = re.findall(r"-?[\d,]*\.?\d+", m[-1])
            if n: return float(n[-1].replace(",", ""))
    return None
def ok(p, g, kind):
    if p is None: return False
    for c in ([p, p * 100] if kind == "pct" else [p]):
        if abs(c - g) <= (0.06 if kind == "pp" else max(0.005 * abs(g), 0.006)): return True
    return False
def score():
    items = {i["id"]: i for i in E["items"]}; summary = {}
    for f in sorted(os.listdir(RES)):
        if not (f.startswith("fin_eval_") and f.endswith(".json")): continue
        d = json.load(open(os.path.join(RES, f), encoding="utf-8")); n = c = tok = 0; secs = 0.0; trunc = 0
        for r in d["results"]:
            it = items[r["id"]]
            for t in r["turns"]:
                tok += t["eval_count"] or 0; secs += t["eval_s"] or 0; trunc += t["done_reason"] == "length"
            if it["kind"] == "qual": continue
            golds = it["answers"] if it["kind"] == "multi" else [it["answer"]]
            for i, g in enumerate(golds):
                k = "pct" if (it["kind"] == "multi" and i == 1) else ("num" if it["kind"] == "multi" else it["kind"])
                n += 1; c += ok(extract(r["turns"][i]["text"] or ""), g, k)
        summary[d["model"]] = dict(correct=c, n=n, tok_s=round(tok / secs, 1) if secs else None, truncated=trunc, ollama_ps=d.get("ollama_ps"))
        log(f"SCORE {d['model']}: {c}/{n}  gen tok/s={summary[d['model']]['tok_s']}  truncated={trunc}  ({d.get('ollama_ps')})")
    json.dump(summary, open(os.path.join(RES, "fin_eval_summary.json"), "w"), indent=1)
if __name__ == "__main__":
    if "--score" in sys.argv: score()
    else:
        for m in sys.argv[1:]: run(m)
        score()
