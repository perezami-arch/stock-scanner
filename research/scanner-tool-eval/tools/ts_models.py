"""Foundation time-series model tools (Kronos, Chronos-2, TimesFM-2.5). Reuses /workspace/kronos-eval code.
Each forecasts a 20-bar path once per unique (ticker, asof) and answers any horizon <= 20 from it."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, time, numpy as np, pandas as pd, torch
import pit
from .base import Tool
KE = (_SCANNER_ROOT + "/kronos-eval")
os.environ.setdefault("HF_HOME", f"{KE}/hf_cache")
LOOKBACK, MAXH, MIN_HIST = 400, 20, 60

class _PathTool(Tool):
    def __init__(self):
        self.cache = {}; self.timing = []
    def _paths(self, items):   # items: list of (ticker, asset, asof, hist_df) -> list of np arrays (MAXH,) predicted closes
        raise NotImplementedError
    def score_batch(self, reqs, batch=16):
        need = []
        for t, a, ts, h in reqs:
            k = (t, a, pd.Timestamp(ts))
            if k in self.cache or k in [n[:3] for n in need]: continue
            try: hist = pit.history(t, a, ts, getattr(self, "lookback", LOOKBACK))
            except FileNotFoundError: self.cache[k] = None; continue
            if len(hist) < MIN_HIST: self.cache[k] = None; continue
            need.append((t, a, pd.Timestamp(ts), hist))
        need.sort(key=lambda n: len(n[3]))
        for i in range(0, len(need), batch):
            chunk = need[i:i + batch]; t0 = time.time()
            for (t, a, ts, hist), p in zip(chunk, self._paths(chunk)):
                self.cache[(t, a, ts)] = p / hist["close"].iloc[-1] - 1
            self.timing.append((time.time() - t0) / len(chunk))
            print(f"[{self.name}] {min(i + batch, len(need))}/{len(need)}", flush=True)
        out = []
        for t, a, ts, h in reqs:
            p = self.cache.get((t, a, pd.Timestamp(ts)))
            out.append(np.nan if p is None else float(p[min(max(int(h), 1), MAXH) - 1]))
        return out
    def score(self, ticker, asset, asof_ts, horizon_days):
        return self.score_batch([(ticker, asset, asof_ts, horizon_days)])[0]

class KronosTool(_PathTool):
    def __init__(self, size="small", sample_count=5, threads=int(os.environ.get("THREADS", 4)), lookback=LOOKBACK):
        super().__init__(); self.lookback = lookback
        sys.path.insert(0, f"{KE}/Kronos"); sys.path.insert(0, KE)
        from model import Kronos, KronosTokenizer, KronosPredictor
        import kronos_fast; kronos_fast.enable()       # KV-cached inference, output-identical to upstream
        torch.set_num_threads(threads); torch.manual_seed(0)
        tok = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-2k" if size == "mini" else "NeoQuasar/Kronos-Tokenizer-base")
        self.pred = KronosPredictor(Kronos.from_pretrained(f"NeoQuasar/Kronos-{size}"), tok, device="cpu", max_context=2048 if size == "mini" else 512)
        self.S = sample_count; self.name = f"Kronos-{size}" + ("" if lookback == LOOKBACK else f" (ctx{lookback})")
    def _paths(self, chunk):   # Kronos predict_batch needs equal history lengths -> sub-batch by length
        out = [None] * len(chunk); by = {}
        for i, c in enumerate(chunk): by.setdefault(len(c[3]), []).append(i)
        for idx in by.values():
            for i, p in zip(idx, self._paths_eq([chunk[i] for i in idx])): out[i] = p
        return out
    def _paths_eq(self, chunk):
        cols = ["open","high","low","close","volume","amount"]
        dfs = [h[cols].reset_index(drop=True) for _, _, _, h in chunk]
        xs = [pd.Series(h.index) for _, _, _, h in chunk]
        ys = [pd.Series(pit.future_dates(a, h.index[-1], MAXH)) for _, a, _, h in chunk]
        out = self.pred.predict_batch(dfs, xs, ys, pred_len=MAXH, T=1.0, top_p=0.9, sample_count=self.S, verbose=False)
        return [o["close"].values for o in out]

class Chronos2Tool(_PathTool):
    name = "Chronos-2"
    def __init__(self, threads=4):
        super().__init__(); torch.set_num_threads(threads)
        from chronos import Chronos2Pipeline
        self.pipe = Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map="cpu")
    def _paths(self, chunk):
        _, mean = self.pipe.predict_quantiles([h["close"].values.astype(np.float32) for *_, h in chunk], prediction_length=MAXH, quantile_levels=[0.5])
        return [m[0].numpy() for m in mean]

class TimesFMTool(_PathTool):
    name = "TimesFM-2.5"
    def __init__(self, threads=4):
        super().__init__(); torch.set_num_threads(threads)
        import timesfm
        self.m = timesfm.TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch", torch_compile=False)
        self.m.compile(timesfm.ForecastConfig(max_context=416, max_horizon=128, normalize_inputs=True, use_continuous_quantile_head=True,
                                              force_flip_invariance=True, infer_is_positive=True, fix_quantile_crossing=True, per_core_batch_size=16))
    def _paths(self, chunk):
        point, _ = self.m.forecast(horizon=MAXH, inputs=[h["close"].values.astype(np.float32) for *_, h in chunk])
        return [point[i] for i in range(len(chunk))]
