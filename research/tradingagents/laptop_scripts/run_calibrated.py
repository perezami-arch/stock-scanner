"""CALIBRATED TradingAgents runner (approved by Ilan 2026-10-08): TradingAgents tuned to the scanner's own question.

Differences from run_all_setups.py (the plain run, untouched):
  1. Every agent's instrument context carries the full setup (direction, reference entry, active-policy stop
     4xATR14 chandelier for stocks / fixed 3xATR14 for crypto, half at fib 1.618 for stock longs, 20-day horizon) and
     the scanner context (ck_score, SMA200, sector uptrend, VA120, stop distance in ATR, rule pass) - all as of the
     cutoff bar (calib_prompt.py, data from setups_calib.csv).
  2. After the normal graph, one extra "setup judge" call (deep model, Ollama JSON-schema output) returns
     {verdict: approve|veto|neutral, p_success: 0-1, reason}, with 4-6 few-shot CLOSED trades from the calibration half
     whose result was known strictly before the setup's cutoff (lessons_pool.csv). The plain 5-tier rating is kept.
Same safety model as run_all_setups.py: one child process per setup with a hard timeout; one flushed+fsynced JSON
line per finished setup (results/results_calib.jsonl); atomic attempts_calib.json; finished setup_ids skipped; night
window + AC + STOP-flag guard checked BEFORE each setup (nightwin.py, active when NIGHT_WINDOW is set); keepawake
while running; single-instance lock results/ta_calib.lock.

Usage:  python run_calibrated.py [--model qwen25-ta] [--limit N] [--dry-run] [--only S0013,S0128]
  --dry-run  checks the guard/lock, counts the work and prints the prompts of the first pending setup; no LLM call.
"""
import argparse, json, os, sys, time, subprocess, traceback, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nightwin, calib_prompt as cp
RES = os.path.join(HERE, "results"); os.makedirs(RES, exist_ok=True)
TAG = "calib"
OUT = os.path.join(RES, f"results_{TAG}.jsonl"); LOG = os.path.join(RES, f"progress_{TAG}.log")
LOCK = os.path.join(RES, f"ta_{TAG}.lock"); ATT = os.path.join(RES, f"attempts_{TAG}.json")
SETUPS = os.path.join(HERE, "setups_calib.csv"); LESSONS = os.path.join(HERE, "lessons_pool.csv")
PROMPT_VERSION = "calib-v1 (2026-10-08)"

def log(msg, quiet=False):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    if not quiet:
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

def ollama_root(base_url): return base_url.rsplit("/v1", 1)[0]

def judge(row, lessons, ta, model, base_url):
    """One structured call to Ollama's native /api/chat (JSON schema). Retries once with plain JSON mode."""
    import urllib.request
    system, user = cp.judge_messages(row, lessons, ta)
    out = {}
    for attempt, fmt in enumerate((cp.JUDGE_SCHEMA, "json")):
        body = dict(model=model, stream=False, format=fmt, options=dict(temperature=0.1, num_predict=500),
                    messages=[dict(role="system", content=system), dict(role="user", content=user)])
        req = urllib.request.Request(ollama_root(base_url) + "/api/chat", data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=600) as r: resp = json.loads(r.read().decode("utf-8"))
        txt = (resp.get("message") or {}).get("content", "")
        out = cp.parse_judge(txt)
        out.update(judge_raw=txt[:1500], judge_s=round(time.time() - t0, 1), judge_attempt=attempt + 1,
                   judge_prompt_tokens=resp.get("prompt_eval_count"), judge_completion_tokens=resp.get("eval_count"))
        if out["parse_ok"]: break
    return out

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
    class CalibGraph(TradingAgentsGraph):
        # every agent reads state["instrument_context"]; append our setup + scanner context (as of the cutoff)
        def resolve_instrument_context(self, ticker, asset_type="stock", trade_date=None):
            return super().resolve_instrument_context(ticker, asset_type, trade_date) + cp.instrument_addendum(row)
    os.makedirs(os.path.join(RES, "mem_calib"), exist_ok=True); os.makedirs(os.path.join(RES, "ta_logs_calib"), exist_ok=True)
    crypto = row["asset"] == "crypto"
    analysts = ("market",) if crypto else ("market", "fundamentals")   # same as the plain run (no PIT news/social feeds)
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(llm_provider="ollama", backend_url=base_url, deep_think_llm=deep_model or model, quick_think_llm=model,
               max_debate_rounds=1, max_risk_discuss_rounds=1, temperature=0.3, max_tokens=int(os.getenv("TA_MAX_TOKENS", "1500")),
               max_tool_rounds=6, results_dir=os.path.join(RES, "ta_logs_calib"),
               data_cache_dir=os.path.join(RES, "cache"),
               memory_log_path=os.path.join(RES, "mem_calib", f"{row['setup_id']}.md"))  # fresh memory: no cross-setup leakage
    lessons = cp.select_lessons(row, cp.load_csv(LESSONS))
    U = Usage(); t0 = time.time()
    ta = CalibGraph(selected_analysts=analysts, debug=False, config=cfg, callbacks=[U])
    state, decision = ta.propagate(row["ticker"], row["trade_date"], asset_type="crypto" if crypto else "stock")
    ids = state.get("investment_debate_state") or {}
    tad = dict(final_rating=str(state.get("final_rating", "")), final_trade_decision=str(state.get("final_trade_decision", "")),
               investment_plan=str(state.get("investment_plan", "")), trader_plan=str(state.get("trader_investment_plan", "")),
               bull=str(ids.get("bull_history", ""))[-1500:], bear=str(ids.get("bear_history", ""))[-1500:])
    ta_s = round(time.time() - t0, 1)
    j = judge(row, lessons, tad, deep_model or model, base_url)
    return dict(verdict=j["verdict"], p_success=j["p_success"], reason=j["reason"], parse_ok=j["parse_ok"],
                judge_raw=j["judge_raw"], judge_s=j["judge_s"], judge_attempt=j["judge_attempt"],
                judge_prompt_tokens=j["judge_prompt_tokens"], judge_completion_tokens=j["judge_completion_tokens"],
                decision=str(decision), final_rating=tad["final_rating"], final_trade_decision=tad["final_trade_decision"][:4000],
                trader_plan=tad["trader_plan"][:2000], bull=tad["bull"], bear=tad["bear"],
                lessons=[p["setup_id"] for p in lessons], n_lessons=len(lessons), analysts=list(analysts),
                ta_runtime_s=ta_s, runtime_s=round(time.time() - t0, 1), llm_calls=U.calls, prompt_tokens=U.pt,
                completion_tokens=U.ct, prompt_version=PROMPT_VERSION)

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
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout-min", type=float, default=45)
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--one", default=None)
    ap.add_argument("--deep-model", default=None)
    ap.add_argument("--only", default="", help="comma-separated setup_ids (testing)")
    ap.add_argument("--min-left-min", type=float, default=10)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.one: return child_main(args)
    q = args.dry_run   # a dry run never writes to the progress log
    why = nightwin.block_reason(args.min_left_min)
    if why:
        log(f"{'dry-run: ' if q else ''}not starting: {why} (resumes next night)", quiet=q); return 3
    if not q:
        import keepawake; keepawake.hold()   # no idle sleep while the batch runs; reset at exit
    lock = acquire_lock()
    if lock is None:
        print("another instance holds the lock; exiting"); return 0
    rows = [r for r in cp.load_csv(SETUPS)]
    rows.sort(key=lambda r: (int(float(r.get("priority") or 99999)), r["setup_id"]))   # same stratified order as the plain run
    if args.only: keep = set(args.only.split(",")); rows = [r for r in rows if r["setup_id"] in keep]
    attempts = nightwin.read_json(ATT, {})
    done = done_ids()
    todo = [r for r in rows if r["setup_id"] not in done and attempts.get(r["setup_id"], 0) < args.max_attempts]
    if args.limit: todo = todo[:args.limit]
    log(f"start: model={args.model} prompt={PROMPT_VERSION} total={len(rows)} done={len(done)} todo={len(todo)}", quiet=q)
    if q:
        if todo:
            r = todo[0]; L = cp.select_lessons(r, cp.load_csv(LESSONS))
            s, u = cp.judge_messages(r, L, dict(final_rating="(from the TA run)", final_trade_decision="(from the TA run)"))
            print(f"--- first pending: {r['setup_id']} {r['ticker']} {r['direction']} cutoff {r['trade_date']} half={r['half']} lessons={len(L)}")
            print("--- instrument context addendum:" + cp.instrument_addendum(r)); print("--- judge system:\n" + s); print("--- judge user:\n" + u)
        print("dry-run: no LLM call made"); return 0
    times = []; fail_streak = 0
    import urllib.request
    def ollama_up():
        try:
            urllib.request.urlopen(ollama_root(args.base_url) + "/api/version", timeout=10); return True
        except Exception: return False
    for i, r in enumerate(todo):
        why = nightwin.block_reason(args.min_left_min)   # checked BEFORE a setup starts: nothing partial is ever written
        if why:
            log(f"paused before {r['setup_id']}: {why} (resumes next night)"); return 3
        waited = 0
        while not ollama_up():
            if waited == 0: log("Ollama not reachable; waiting...")
            time.sleep(30); waited += 30
            if waited > 1800: log("Ollama down for 30 min; exiting (watchdog will relaunch)"); return
        sid = r["setup_id"]; t0 = time.time(); attempt_no = attempts.get(sid, 0) + 1
        cmd = [sys.executable, os.path.abspath(__file__), "--one", json.dumps(r),
               "--model", args.model, "--base-url", args.base_url] + (["--deep-model", args.deep_model] if args.deep_model else [])
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=args.timeout_min * 60, cwd=HERE)
            tag = [l for l in p.stdout.splitlines() if l.startswith("@@RESULT@@")]
            res = json.loads(tag[-1][10:]) if tag else dict(ok=False, error="child produced no result", stderr=p.stderr[-1500:])
        except subprocess.TimeoutExpired:
            res = dict(ok=False, error=f"timeout after {args.timeout_min} min")
        res.update({k: r.get(k) for k in ("setup_id", "ticker", "asset", "direction", "trade_date", "half", "priority",
                                           "platform", "automation", "rule_pass")},
                   wall_s=round(time.time() - t0, 1), finished_at=dt.datetime.now().isoformat(timespec="seconds"),
                   llm=args.model, deep_llm=args.deep_model or args.model, attempt=attempt_no)
        nightwin.append_jsonl(OUT, res)
        attempts[sid] = attempt_no; nightwin.write_json_atomic(ATT, attempts)
        fail_streak = 0 if res["ok"] else fail_streak + 1
        times.append(res["wall_s"]); avg = sum(times) / len(times)
        eta_h = avg * (len(todo) - i - 1) / 3600
        log(f"[{i+1}/{len(todo)}] {sid} {r['ticker']} {r['trade_date']} {r['direction']} -> "
            + (f"{res.get('verdict')} p={res.get('p_success')} (TA {res.get('decision')})" if res["ok"] else "FAIL " + res.get("error", "")[:120])
            + f" ({res['wall_s']:.0f}s, avg {avg:.0f}s, ETA {eta_h:.1f}h)")
        if fail_streak >= 3:   # circuit breaker: a systematic error must not burn the 3 attempts of every setup in one night
            log("3 consecutive failures; stopping this pass (see the error field in results_calib.jsonl)"); return 4
    log("finished pass")

if __name__ == "__main__":
    sys.exit(main() or 0)
