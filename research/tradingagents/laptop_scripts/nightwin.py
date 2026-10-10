"""Night-window / power guard shared by the nightly runners.

Active only when the env var NIGHT_WINDOW is set (e.g. "23:00-08:00"); run_queue.py sets it when the
scheduled task launches it with --night. Manual/daytime runs (no env var) are never blocked.
Runners call block_reason(need_min) BEFORE starting each new item: if it returns a non-empty string they stop
cleanly (nothing partial is written) and the next night resumes from the same place.
Also stops when the laptop is on battery, and when results/STOP exists (manual graceful stop)."""
import os, json, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
STOP_FLAG = os.path.join(HERE, "results", "STOP")


def _hm(s):
    h, m = s.strip().split(":"); return dt.time(int(h), int(m))


def minutes_left(now=None):
    """Minutes until the window ends; 0 if outside it; huge if no window is configured."""
    w = os.getenv("NIGHT_WINDOW", "").strip()
    if not w: return 10 ** 6
    s, e = (_hm(x) for x in w.split("-"))
    now = now or dt.datetime.now(); t = now.time()
    end = dt.datetime.combine(now.date(), e)
    if s > e:                                   # crosses midnight (23:00-08:00)
        if t >= s: end += dt.timedelta(days=1)
        elif t >= e: return 0
    elif not (s <= t < e): return 0
    return (end - now).total_seconds() / 60


def on_ac():
    if os.name != "nt": return True
    import ctypes
    class SPS(ctypes.Structure):
        _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte), ("BatteryLifePercent", ctypes.c_ubyte),
                    ("SystemStatusFlag", ctypes.c_ubyte), ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]
    s = SPS()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)): return True
    return s.ACLineStatus != 0                  # 0 = battery, 1 = AC, 255 = unknown (treated as AC)


def block_reason(need_min=0):
    if not os.getenv("NIGHT_WINDOW", "").strip(): return ""
    if os.path.exists(STOP_FLAG): return "STOP flag present"
    left = minutes_left()
    if left <= need_min: return f"night window closing ({left:.0f} min left, need {need_min})"
    if not on_ac(): return "on battery"
    return ""


def append_jsonl(path, rec):
    """Append one record as one line, flushed + fsynced. If a previous run was killed mid-write and left an
    unterminated line, start on a new line so the old fragment can't merge into this record."""
    data = (json.dumps(rec, ensure_ascii=False, default=str) + "\n").encode("utf-8")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "rb") as r:
            r.seek(-1, 2)
            if r.read(1) != b"\n": data = b"\n" + data
    with open(path, "ab") as f:
        f.write(data); f.flush(); os.fsync(f.fileno())


def write_json_atomic(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except Exception: return default