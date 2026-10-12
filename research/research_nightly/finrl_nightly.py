"""Nightly FinRL PPO model for the research column exp_finrl_* (run with gh-repos-eval/venv-finrl).
Same setup as the earlier eval (gh-repos-eval/finrl/finrl_wf.py, the small 2048-step run): official StockTradingEnv,
stockstats indicators macd / rsi_30 / cci_30 / dx_30, 0.07% costs, PPO MlpPolicy with VecNormalize.
POINT-IN-TIME for bar D (= last bar of research-models/data/<D>, already cut by models_data.py): PPO is trained on bars <= D,
then the trained policy runs forward deterministically over the last WARM sessions up to D; the score of a ticker is the
agent's action for it on D (state = data up to the close of D). FinRL needs every ticker on every day: tickers listed later
are back-filled with their first price (flat -> no return information; documented impurity of the earlier eval).
Output: research-models/finrl/pred_<D>.csv (ticker, bar_date, score = action in [-1,1], pct, train_end, label_end, model_id),
        model_<D>.zip (+ vecnorm_<D>.pkl), meta_<D>.json. Written atomically."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, json, time, glob, argparse, numpy as np, pandas as pd, torch
ap = argparse.ArgumentParser(); ap.add_argument("data_dir"); ap.add_argument("--steps", type=int, default=2048); ap.add_argument("--warm", type=int, default=10)
ap.add_argument("--threads", type=int, default=2); a = ap.parse_args()
torch.set_num_threads(a.threads)
import importlib.util as _u
_sp = _u.spec_from_file_location("envst", (_SCANNER_ROOT + "/gh-repos-eval/finrl/repo/finrl/meta/env_stock_trading/env_stocktrading.py"))
_m = _u.module_from_spec(_sp); _sp.loader.exec_module(_m); StockTradingEnv = _m.StockTradingEnv
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stockstats import StockDataFrame
ROOT = (_SCANNER_ROOT + "/research-models"); D = os.path.basename(a.data_dir.rstrip("/")); T0 = time.time()
IND = ["macd", "rsi_30", "cci_30", "dx_30"]; fr = []
for f in sorted(glob.glob(f"{a.data_dir}/src_csv/*.csv")):
    x = pd.read_csv(f); x["date"] = pd.to_datetime(x["date"]); x = x[["date", "open", "high", "low", "close", "volume"]].sort_values("date")
    if x.date.max() != pd.Timestamp(D): continue
    sd = StockDataFrame.retype(x.copy())
    for i in IND: x[i] = sd[i].values
    x["tic"] = os.path.basename(f)[:-4].upper(); fr.append(x)
P = pd.concat(fr); TK = sorted(P.tic.unique())
dates = sorted(d for d in P.date.unique() if d >= pd.Timestamp("2024-01-02") and d <= pd.Timestamp(D))
idx = pd.MultiIndex.from_product([dates, TK], names=["date", "tic"])
P = P.set_index(["date", "tic"]).reindex(idx).groupby(level="tic").transform(lambda s: s.ffill().bfill()).reset_index()
P[IND] = P[IND].fillna(0); P = P.sort_values(["date", "tic"]); P["day"] = P.groupby("date").ngroup(); P = P.set_index("day"); P.index.name = None
N = len(TK); SS = 1 + 2 * N + N * len(IND)
def env(df):
    df = df.copy(); df.index = df.index - df.index.min()
    return StockTradingEnv(df=df, stock_dim=N, hmax=100, initial_amount=1_000_000, num_stock_shares=[0] * N, buy_cost_pct=[0.0007] * N,
                           sell_cost_pct=[0.0007] * N, reward_scaling=1e-4, state_space=SS, action_space=N, tech_indicator_list=IND, print_verbosity=10 ** 9)
venv = VecNormalize(DummyVecEnv([lambda: env(P)]), norm_obs=True, norm_reward=True)
m = PPO("MlpPolicy", venv, n_steps=2048, batch_size=128, learning_rate=3e-4, ent_coef=0.01, seed=int(pd.Timestamp(D).strftime("%Y%m%d")) % 2**31, verbose=0, device="cpu")
t = time.time(); m.learn(total_timesteps=a.steps); train_s = time.time() - t
venv.training = False; venv.norm_reward = False
te = P[P.date >= dates[-a.warm]]; e = env(te); obs, _ = e.reset(); td = sorted(te.date.unique())
for k, d in enumerate(td):
    act, _ = m.predict(venv.normalize_obs(np.array(obs, dtype=np.float32)[None]), deterministic=True)
    if k == len(td) - 1: break
    obs, _, done, _, _ = e.step(act[0])
assert pd.Timestamp(td[-1]) == pd.Timestamp(D)
mid = f"finrl_ppo{a.steps}_{D}"
R = pd.DataFrame({"ticker": TK, "bar_date": D, "score": act[0].astype(float)})
R["pct"] = R.score.rank(pct=True) * 100; R["train_end"] = D; R["label_end"] = D; R["model_id"] = mid
os.makedirs(f"{ROOT}/finrl", exist_ok=True)
m.save(f"{ROOT}/finrl/model_{D}.zip"); venv.save(f"{ROOT}/finrl/vecnorm_{D}.pkl")
R.to_csv(f"{ROOT}/finrl/pred_{D}.csv.tmp", index=False); os.replace(f"{ROOT}/finrl/pred_{D}.csv.tmp", f"{ROOT}/finrl/pred_{D}.csv")
meta = dict(bar_date=D, tickers=N, state_dim=SS, train_days=len(dates), steps=a.steps, warm_sessions=a.warm, train_s=round(train_s, 1),
            total_s=round(time.time() - T0, 1), model_id=mid, distinct_scores=int(R.score.round(4).nunique()))
json.dump(meta, open(f"{ROOT}/finrl/meta_{D}.json", "w"), indent=1); print(json.dumps(meta))
for old in sorted(glob.glob(f"{ROOT}/finrl/model_*.zip"))[:-5]: os.remove(old)
