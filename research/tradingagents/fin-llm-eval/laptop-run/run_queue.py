"""Entry point for the scheduled task (watchdog relaunches every 15 min; a lock prevents double runs).
Step 1: fin_eval for Qwen2.5-7B and Fin-R1 (both Q4_K_M, ~10-30 min on the RTX 4070).
Step 2: TradingAgents over all setups with Qwen2.5-7B Q4_K_M (sample-priority order).
Step 3: TradingAgents with Fin-R1 as the deep-thinking model (research + portfolio manager) on the first 120 setups
        of the same order, so Qwen-only vs Fin-R1-deep can be compared on identical setups.
Every step is resumable; re-running just continues."""
import os, sys, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, "results"); os.makedirs(RES, exist_ok=True)
PY = sys.executable
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
if __name__ == "__main__":
    L = lock()
    if L is None: sys.exit(0)
    if os.name == "nt":
        try:
            import ctypes; ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        except Exception: pass
    steps = [
        ("fin_eval", [PY, "fin_eval.py", "qwen25-7b-q4km", "fin-r1-q4km"]),
        ("ta_qwen", [PY, "run_all_setups.py", "--model", "qwen25-ta", "--timeout-min", "45"]),
        ("ta_finr1deep", [PY, "run_all_setups.py", "--model", "qwen25-ta", "--deep-model", "fin-r1-ta",
                          "--tag", "finr1deep", "--max-priority", "120", "--timeout-min", "60"]),
    ]
    for name, cmd in steps:
        if os.path.exists(os.path.join(RES, f"{name}.done")): continue
        log(f"start {name}"); p = subprocess.run(cmd, cwd=HERE); log(f"end {name} rc={p.returncode}")
        if p.returncode == 0 and name == "fin_eval": open(os.path.join(RES, f"{name}.done"), "w").close()
        # TA steps mark themselves done only when nothing is left (a pass with failures is retried next launch)
        if name.startswith("ta_") and p.returncode == 0:
            tag = name.split("_", 1)[1]
            prog = os.path.join(RES, "progress.log" if tag == "qwen" else f"progress_{tag}.log")
            try:
                if "todo=0" in open(prog, encoding="utf-8").read().splitlines()[-2]: open(os.path.join(RES, f"{name}.done"), "w").close()
            except Exception: pass
    log("queue pass finished")
