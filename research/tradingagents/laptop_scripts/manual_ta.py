"""Manual daytime batch (requested by Ilan 2026-10-08): TradingAgents on the next N pending setups, same priority
order as the nightly ta_qwen step (so the nightly run skips them), then unloads qwen25-ta.
Holds results/queue.lock for the whole run (same lock as run_queue.py), so a nightly start can't collide;
run_all_setups.py additionally holds results/ta.lock.  Usage: pythonw manual_ta.py [N]"""
import os, sys, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, "results")
sys.path.insert(0, HERE)
os.environ.pop("NIGHT_WINDOW", None)          # manual run: no night-window guard
import run_queue                               # reuses its lock()/log()/ensure_ollama(); its main is guarded
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
L = run_queue.lock()
if L is None:
    run_queue.log("manual_ta: queue.lock held by another run; not starting"); sys.exit(0)
import keepawake; keepawake.hold()   # no idle sleep during the manual batch; reset at exit
run_queue.ensure_ollama()
PY = os.path.join(HERE, ".venv", "Scripts", "python.exe")
run_queue.log(f"manual_ta: start ta_qwen --limit {N}")
with open(os.path.join(RES, "ta_qwen.out"), "a", encoding="utf-8") as out:
    out.write(time.strftime(f"\n=== %Y-%m-%d %H:%M:%S manual start --limit {N}\n")); out.flush()
    p = subprocess.run([PY, "run_all_setups.py", "--model", "qwen25-ta", "--timeout-min", "45", "--limit", str(N)],
                       cwd=HERE, stdout=out, stderr=subprocess.STDOUT, creationflags=run_queue.NOWIN)
run_queue.log(f"manual_ta: end rc={p.returncode}")
try:
    exe = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
    r = subprocess.run([exe if os.path.exists(exe) else "ollama", "stop", "qwen25-ta"], capture_output=True, text=True,
                       creationflags=run_queue.NOWIN)
    run_queue.log(f"manual_ta: ollama stop qwen25-ta rc={r.returncode} {r.stdout.strip()} {r.stderr.strip()}")
except Exception as e:
    run_queue.log(f"manual_ta: ollama stop failed: {e}")
run_queue.log("manual_ta: done")
