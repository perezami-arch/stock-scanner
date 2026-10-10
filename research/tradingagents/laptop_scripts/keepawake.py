"""Keep Windows from idle-sleeping while a runner process lives.
hold(): SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED) on the calling thread; resets to ES_CONTINUOUS
at interpreter exit (Windows also drops the request automatically when the process ends, even on a hard kill).
Lid-close / manual Sleep still sleep the machine (power-button/lid actions override this request).
No-op on non-Windows. Returns True if Windows accepted the request."""
import os, atexit
ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
_held = False
def release():
    global _held
    if os.name == "nt" and _held:
        try:
            import ctypes; ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        except Exception: pass
    _held = False
def hold():
    global _held
    if os.name != "nt": return False
    try:
        import ctypes
        k = ctypes.windll.kernel32; k.SetThreadExecutionState.restype = ctypes.c_uint
        ok = k.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED) != 0
        if ok and not _held: atexit.register(release)
        _held = _held or ok
        return ok
    except Exception:
        return False
