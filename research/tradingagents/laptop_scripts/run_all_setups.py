"""Resumable, detached-friendly TradingAgents backtest over the scanner setups.

- Reads setups_846.csv (trade_date already = point-in-time cutoff bar; Perplexity
  task-list times capped 70 min earlier). Rows with skip_reason are skipped.
- Each setup runs in its own child process with a hard timeout, so one hung
  LLM/data call can't stall the batch; failures are retried on the next pass.
- Appends one JSON line per finished setup to results/results.jsonl; on restart,
  setup_ids already in that file (ok=True) are skipped.
- Single-instance lock (results/run.lock), so a scheduled task can relaunch it
  every 15 min as a watchdog without double-running.
- Points at local Ollama's OpenAI-compatible endpoint (default http://localhost:11434/v1).

Usage:  python run_all_setups.py [--model qwen25-ta] [--limit N] [--timeout-min 45]
"""
import argparse, json, os, sys, time, subprocess, traceback, datetime as dt
import nightwin   # night-window/AC guard + crash-safe append (active only when NIGHT_WINDOW is set)
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results"); os.makedirs(RES, exist_ok=True)
OUT = os.path.join(RES, "results.jsonl"); LOG = os.path.join(RES, "progress.log")
LOCK = os.path.join(RES, "ta.lock")

def log(msg):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    with open(LOG, "a", encoding="utf-8") as f: f.write(line + "\n")
    print(line, flush=True)

def acquire_lock():
    fh = open(LOCK, "a+")
    try:
        if os.name == "nt":
            import msvcrt; fh.seek(0); msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl; fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fh
    except OSError:
        return None

def done_ids():
    ids = set()
    if os.path.exists(OUT):
        for l in open(OUT, encoding="utf-8"):
            try:
                r = json.loads(l)
                if r.get("ok"): ids.add(r["setup_id"])
            except Exception: pass
    return ids

def run_one(row, model, base_url, deep_model=None):
    """Runs inside the child process. Returns a result dict."""
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from langchain_core.callbacks import BaseCallbackHandler
    class Usage(BaseCallbackHandler):
        def __init__(self): self.calls = self.pt = self.ct = 0
        def on_llm_end(self, response, **kw):
            self.calls += 1
            for gens in response.generations:
                for g in gens:
                    um = getattr(getattr(g, "message", None), "usage_metadata", None) or {}
                    self.pt += um.get("input_tokens", 0); self.ct += um.get("output_tokens", 0)
    os.makedirs(os.path.join(RES, "mem"), exist_ok=True); os.makedirs(os.path.join(RES, "ta_logs"), exist_ok=True)
    crypto = row["asset"] == "crypto"
    # news/social/insider feeds are withheld by TradingAgents for past dates (no point-in-time
    # vintage), so only analysts with real historical data are used.
    analysts = ("market",) if crypto else ("market", "fundamentals")
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(llm_provider="ollama", backend_url=base_url, deep_think_llm=deep_model or model, quick_think_llm=model,
               max_debate_rounds=1, max_risk_discuss_rounds=1, temperature=0.3, max_tokens=int(os.getenv("TA_MAX_TOKENS", "1500")),
               max_tool_rounds=6, results_dir=os.path.join(RES, "ta_logs"),
               data_cache_dir=os.path.join(RES, "cache"),
               memory_log_path=os.path.join(RES, "mem", f"{row['setup_id']}.md"))  # fresh memory: no cross-setup outcome leakage
    U = Usage(); t0 = time.time()
    ta = TradingAgentsGraph(selected_analysts=analysts, debug=False, config=cfg, callbacks=[U])
    state, decision = ta.propagate(row["ticker"], row["trade_date"], asset_type="crypto" if crypto else "stock")
    ids = state.get("investment_debate_state") or {}
    return dict(decision=str(decision), final_rating=str(state.get("final_rating", "")),
                final_trade_decision=str(state.get("final_trade_decision", ""))[:4000],
                trader_plan=str(state.get("trader_investment_plan", ""))[:2000],
                bull=str(ids.get("bull_history", ""))[-1500:], bear=str(ids.get("bear_history", ""))[-1500:],
                analysts=list(analysts), runtime_s=round(time.time() - t0, 1),
                llm_calls=U.calls, prompt_tokens=U.pt, completion_tokens=U.ct)

def child_main(args):
    row = json.loads(args.one)
    try:
        res = dict(ok=True, **run_one(row, args.model, args.base_url, args.deep_model))
    except Exception as e:
        res = dict(ok=False, error=repr(e)[:800], tb=traceback.format_exc()[-2000:])
    print("@@RESULT@@" + json.dumps(res, default=str))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.getenv("TA_MODEL", "qwen25-ta"))
    ap.add_argument("--base-url", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"))
    ap.add_argument("--setups", default=os.path.join(HERE, "setups_846.csv"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout-min", type=float, default=45)
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--one", default=None)
    ap.add_argument("--deep-model", default=None, help="model for research/portfolio managers (default = --model)")
    ap.add_argument("--tag", default="", help="suffix for results file, e.g. finr1deep")
    ap.add_argument("--max-priority", type=int, default=0, help="only setups with priority < N (sample order)")
    ap.add_argument("--min-left-min", type=float, default=10, help="night mode: don't start a setup with fewer minutes left in the window")
    args = ap.parse_args()
    global OUT, LOG
    if args.tag:
        OUT = os.path.join(RES, f"results_{args.tag}.jsonl"); LOG = os.path.join(RES, f"progress_{args.tag}.log")
    if args.one: return child_main(args)
    import keepawake; keepawake.hold()   # ES_CONTINUOUS|ES_SYSTEM_REQUIRED while the batch runs; reset at exit (lid/manual sleep still pauses it)
    lock = acquire_lock()
    if lock is None:
        print("another instance holds the lock; exiting"); return
    import csv
    rows = [r for r in csv.DictReader(open(args.setups, encoding="utf-8")) if not r["skip_reason"]]
    rows.sort(key=lambda r: int(r.get("priority") or 99999))   # stratified sample order: partial runs stay balanced
    if args.max_priority: rows = [r for r in rows if int(r.get("priority") or 99999) < args.max_priority]
    attempts_file = os.path.join(RES, f"attempts{('_'+args.tag) if args.tag else ''}.json")
    attempts = nightwin.read_json(attempts_file, {})
    done = done_ids()
    todo = [r for r in rows if r["setup_id"] not in done and attempts.get(r["setup_id"], 0) < args.max_attempts]
    if args.limit: todo = todo[:args.limit]
    log(f"start: model={args.model} total={len(rows)} done={len(done)} todo={len(todo)}")
    times = []
    import urllib.request
    def ollama_up():
        try:
            urllib.request.urlopen(args.base_url.rsplit("/v1", 1)[0] + "/api/version", timeout=10); return True
        except Exception: return False
    for i, r in enumerate(todo):
        why = nightwin.block_reason(args.min_left_min)   # checked BEFORE a setup starts: nothing partial is ever written
        if why:
            log(f"paused before {r['setup_id']}: {why} (resumes next night)"); return 3
        waited = 0
        while not ollama_up():          # e.g. right after the laptop wakes up: wait instead of burning attempts
            if waited == 0: log("Ollama not reachable; waiting...")
            time.sleep(30); waited += 30
            if waited > 1800: log("Ollama down for 30 min; exiting (watchdog will relaunch)"); return
        sid = r["setup_id"]; t0 = time.time()
        # the attempt is counted only once a result exists, so a setup killed at 08:00 does not burn one of its 3 attempts
        attempt_no = attempts.get(sid, 0) + 1
        cmd = [sys.executable, os.path.abspath(__file__), "--one", json.dumps(r),
               "--model", args.model, "--base-url", args.base_url] + (["--deep-model", args.deep_model] if args.deep_model else [])
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=args.timeout_min * 60, cwd=HERE)
            tag = [l for l in p.stdout.splitlines() if l.startswith("@@RESULT@@")]
            res = json.loads(tag[-1][10:]) if tag else dict(ok=False, error="child produced no result", stderr=p.stderr[-1500:])
        except subprocess.TimeoutExpired:
            res = dict(ok=False, error=f"timeout after {args.timeout_min} min")
        res.update({k: r[k] for k in ("setup_id","ticker","asset","direction","trade_date","platform","model","automation","tracker_total_return")},
                   wall_s=round(time.time() - t0, 1), finished_at=dt.datetime.now().isoformat(timespec="seconds"),
                   llm=args.model, deep_llm=args.deep_model or args.model, attempt=attempt_no)
        nightwin.append_jsonl(OUT, res)                       # one line per setup, flushed + fsynced
        attempts[sid] = attempt_no; nightwin.write_json_atomic(attempts_file, attempts)
        times.append(res["wall_s"]); avg = sum(times) / len(times)
        eta_h = avg * (len(todo) - i - 1) / 3600
        log(f"[{i+1}/{len(todo)}] {sid} {r['ticker']} {r['trade_date']} {r['direction']} -> "
            f"{res.get('decision') if res['ok'] else 'FAIL ' + res.get('error','')[:120]} "
            f"({res['wall_s']:.0f}s, avg {avg:.0f}s, ETA {eta_h:.1f}h)")
    log("finished pass")

if __name__ == "__main__":
    sys.exit(main() or 0)
