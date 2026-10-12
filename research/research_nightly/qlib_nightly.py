"""Nightly Qlib walk-forward model for the research column exp_qlib_* (run with gh-repos-eval/venv-qlib).
Same model as the earlier eval (gh-repos-eval/qlib/qlib_wf_B.py): official Alpha158 features + LightGBM (fixed 200 rounds),
label = 20-day forward return Ref($close,-20)/$close-1, CSRankNorm on the label.
POINT-IN-TIME for bar D (= last bar of research-models/data/<D>, already cut by models_data.py):
  * the bins are dumped from bars <= D only;
  * train ends at cal[i(D)-20] -> the last label uses the close of D itself (fully realised when bar D is visible);
  * the score is the prediction on the Alpha158 features of D (backward-looking only; leak check 0/161,476 cells earlier).
Output: research-models/qlib/pred_<D>.csv (ticker, bar_date, score, pct 0-100 cross-sectional, train_end, label_end, model_id)
        research-models/qlib/model_<D>.pkl, meta_<D>.json. Written atomically (tmp + rename)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, json, time, glob, shutil, pickle, subprocess, argparse
import numpy as np, pandas as pd
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")          # qlib's recorder writes ./mlruns (file store)
H = 20
ROOT = (_SCANNER_ROOT + "/research-models"); REPO = (_SCANNER_ROOT + "/gh-repos-eval/qlib/repo")
ap = argparse.ArgumentParser(); ap.add_argument("data_dir"); ap.add_argument("--threads", type=int, default=2); ap.add_argument("--rounds", type=int, default=200)
a = ap.parse_args()
os.makedirs(f"{ROOT}/qlib", exist_ok=True); os.chdir(f"{ROOT}/qlib")
D = os.path.basename(a.data_dir.rstrip("/")); src = f"{a.data_dir}/src_csv"; T0 = time.time()
bins = f"{ROOT}/qlib/bin_{D}"; shutil.rmtree(bins, ignore_errors=True)
subprocess.run([sys.executable, f"{REPO}/scripts/dump_bin.py", "dump_all", "--data_path", src, "--qlib_dir", bins, "--freq", "day",
                "--date_field_name", "date", "--symbol_field_name", "symbol", "--include_fields", "open,high,low,close,volume,vwap,factor",
                "--max_workers", str(a.threads)], check=True, capture_output=True)
import qlib
from qlib.constant import REG_US
qlib.init(provider_uri=bins, region=REG_US, kernels=a.threads)
from qlib.contrib.data.handler import Alpha158
from qlib.data.dataset import DatasetH
from qlib.contrib.model.gbdt import LGBModel
cal = pd.DatetimeIndex(pd.read_csv(f"{bins}/calendars/day.txt", header=None)[0])
if str(cal[-1].date()) != D: raise SystemExit(f"calendar ends {cal[-1].date()} != data dir {D}")
iD = len(cal) - 1; tr_end = cal[iD - H]; va_start = cal[iD - H - 40 + 1]
h = Alpha158(instruments="all", start_time="2023-01-03", end_time=D, fit_start_time="2023-01-03", fit_end_time="2023-12-31",
             infer_processors=[], learn_processors=[{"class": "DropnaLabel"}, {"class": "CSRankNorm", "kwargs": {"fields_group": "label"}}],
             label=([f"Ref($close, -{H})/$close - 1"], ["LABEL0"]))
seg = {"train": ("2023-04-03", tr_end), "valid": (va_start, tr_end), "test": (cal[iD], cal[iD])}
ds = DatasetH(h, segments=seg)
params = dict(loss="mse", colsample_bytree=0.8879, learning_rate=0.05, subsample=0.8789, lambda_l1=205.6999, lambda_l2=580.9768, max_depth=8,
              num_leaves=210, num_threads=a.threads, early_stopping_rounds=100000, num_boost_round=a.rounds, verbosity=-1)
m = LGBModel(**params); t = time.time(); m.fit(ds); fit_s = time.time() - t
p = m.predict(ds, segment="test").xs(cal[iD], level=0)
mid = f"qlib_alpha158_lgb{a.rounds}_{D}"
P = pd.DataFrame({"ticker": p.index.astype(str).str.upper(), "bar_date": D, "score": p.values})
P["pct"] = P.score.rank(pct=True) * 100; P["train_end"] = str(tr_end.date()); P["label_end"] = str(cal[iD].date()); P["model_id"] = mid
os.makedirs(f"{ROOT}/qlib", exist_ok=True)
pickle.dump(m, open(f"{ROOT}/qlib/model_{D}.pkl", "wb"))
P.to_csv(f"{ROOT}/qlib/pred_{D}.csv.tmp", index=False); os.replace(f"{ROOT}/qlib/pred_{D}.csv.tmp", f"{ROOT}/qlib/pred_{D}.csv")
meta = dict(bar_date=D, train=("2023-04-03", str(tr_end.date())), valid=(str(va_start.date()), str(tr_end.date())), label_end=str(cal[iD].date()),
            n_scored=int(P.score.notna().sum()), fit_s=round(fit_s, 1), total_s=round(time.time() - T0, 1), model_id=mid)
json.dump(meta, open(f"{ROOT}/qlib/meta_{D}.json", "w"), indent=1); print(json.dumps(meta))
for old in sorted(glob.glob(f"{ROOT}/qlib/bin_*"))[:-2]: shutil.rmtree(old, ignore_errors=True)   # keep the last 2 bin dumps
