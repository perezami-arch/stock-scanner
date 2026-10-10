"""Entry point for the NIGHTLY scheduled task "TA-Backtest-Night-Start" (23:00, re-fired every 15 min until 07:45
as a watchdog; a lock prevents double runs). Launched as:  pythonw run_queue.py --night 23:00-08:00
Steps (each resumable; finished steps are marked results/<step>.done and skipped):
  1. fin_eval            Qwen2.5-7B vs Fin-R1 calc test (already complete -> skipped)
  2. aihf_druckenmiller  ai-hedge-fund persona, all stock setups, Qwen2.5-7B (~6-10 s/setup)
  3. aihf_buffett        same, Buffett persona
  4. ta_calib            CALIBRATED TradingAgents (run_calibrated.py, added 2026-10-08, approved by Ilan): setup + scanner
                         context in every agent's prompt, final JSON verdict approve/veto/neutral + p_success, few-shot
                         closed trades from the calibration half. All 832 runnable setups, Qwen2.5-7B (~3.8 min/setup).
                         It REPLACES the plain ta_qwen step (removed below; its results.jsonl is kept as is).
  5. ta_finr1deep        TradingAgents, Fin-R1 as deep model, first 120 setups (plain, unchanged)
Night mode: no new setup/step starts with < 10 min (TA) / < 2 min (aihf) left before 08:00, or on battery, or if
results/STOP exists. The 08:00 task "TA-Backtest-Night-Stop" (stop_night.ps1) kills whatever is still running and
unloads the models; a killed setup writes nothing and is redone first the next night.
Without --night (manual run) nothing is time-limited."""
import os, sys, subprocess, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, "results"); os.makedirs(RES, exist_ok=True)
sys.path.insert(0, HERE); import nightwin
PY = sys.executable
AIHF_PY = os.path.join(HERE, ".venv-aihf", "Scripts", "pythonw.exe" if os.name == "nt" else "python")
NOWIN = 0x08000000 if os.name == "nt" else 0          # CREATE_NO_WINDOW: nothing pops up at night
def log(m):
    with open(os.path.join(RES, "queue.log"), "a", encoding="utf-8") as f: f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + m + "\n")
def lock():
    fh = open(os.path.join(RES, "queue.lock"), "a+")
    try:
        if os.name == "nt":
            import msvcrt; fh.seek(0); msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl; fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fh
    except OSError: return None
def ollama_up():
    try: urllib.request.urlopen("http://localhost:11434/api/version", timeout=10); return True
    except Exception: return False
def ensure_ollama():
    if ollama_up(): return
    app = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama app.exe")
    if os.name == "nt" and os.path.exists(app):
        log("Ollama not running; starting the Ollama app"); subprocess.Popen([app], cwd=os.path.dirname(app), creationflags=NOWIN)
        for _ in range(24):
            time.sleep(5)
            if ollama_up(): return
if __name__ == "__main__":
    if "--night" in sys.argv: os.environ["NIGHT_WINDOW"] = sys.argv[sys.argv.index("--night") + 1]
    why = nightwin.block_reason(10)
    if why:
        if "--night" in sys.argv and "window" not in why: log(f"not starting: {why}")
        sys.exit(0)
    L = lock()
    if L is None: sys.exit(0)
    import keepawake; keepawake.hold()   # ES_CONTINUOUS|ES_SYSTEM_REQUIRED while this process lives; reset at exit (lid/manual sleep still pauses it)
    ensure_ollama()
    steps = [
        ("fin_eval", [PY, "fin_eval.py", "qwen25-7b-q4km", "fin-r1-q4km"]),
        ("aihf_druckenmiller", [AIHF_PY, os.path.join("aihf", "run_aihf.py"), "druckenmiller", "--model", "qwen25-7b-q4km"]),
        ("aihf_buffett", [AIHF_PY, os.path.join("aihf", "run_aihf.py"), "buffett", "--model", "qwen25-7b-q4km"]),
        # ("ta_qwen", [PY, "run_all_setups.py", "--model", "qwen25-ta", "--timeout-min", "45"]),   # replaced 2026-10-08 by ta_calib
        ("ta_calib", [PY, "run_calibrated.py", "--model", "qwen25-ta", "--timeout-min", "45"]),
        ("ta_finr1deep", [PY, "run_all_setups.py", "--model", "qwen25-ta", "--deep-model", "fin-r1-ta",
                          "--tag", "finr1deep", "--max-priority", "120", "--timeout-min", "60"]),
    ]
    for name, cmd in steps:
        if os.path.exists(os.path.join(RES, f"{name}.done")): continue
        why = nightwin.block_reason(10 if name.startswith("ta_") else 2)
        if why: log(f"pause before {name}: {why}"); break
        log(f"start {name}")
        with open(os.path.join(RES, f"{name}.out"), "a", encoding="utf-8") as out:
            out.write(time.strftime("\n=== %Y-%m-%d %H:%M:%S start\n")); out.flush()
            p = subprocess.run(cmd, cwd=HERE, stdout=out, stderr=subprocess.STDOUT, creationflags=NOWIN)
        log(f"end {name} rc={p.returncode}")
        if p.returncode == 3: log("paused (night window / battery / STOP); resumes next night"); break
        if p.returncode == 0 and (name == "fin_eval" or name.startswith("aihf_")): open(os.path.join(RES, f"{name}.done"), "w").close()
        # TA steps mark themselves done only when nothing is left (a pass with failures is retried next launch)
        if name.startswith("ta_") and p.returncode == 0:
            tag = name.split("_", 1)[1]
            prog = os.path.join(RES, "progress.log" if tag == "qwen" else f"progress_{tag}.log")
            try:
                if "todo=0" in open(prog, encoding="utf-8").read().splitlines()[-2]: open(os.path.join(RES, f"{name}.done"), "w").close()
            except Exception: pass
    log("queue pass finished")