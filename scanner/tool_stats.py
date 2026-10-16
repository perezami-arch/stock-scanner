"""Per-tool statistics for EXPERIMENTAL (weight-0) scanner columns - forward measurement from 2026-10-12.
Built 08.10.2026 for Ilan / room "בניית מודל סורק לשוק ההון". Generic: works on any column of the tracker, so it covers
research_columns.py (exp_<tool>_*), scanner_geometry (exp_spiral/gann, vp*, candle_*, liq_*), watch_short_below_va120,
sr_levels (sr_*), Elliott v2 (exp_ev2_*, scanner_elliott_v2), OpenBB (openbb_*/obb_*), fundamentals (scanner_fundamentals.TRACKER_KEYS), TradingView alerts (tv_*),
and the LLM verdicts of Grok / Perplexity / Claude / GPT / Jev (scan-runs/platform_verdicts_ledger.csv, FORWARD ONLY).

Inputs
  tracker : build7 xlsx (sheet 'מעקב סריקות'; Hebrew headers, suffixes like ' (ניסיוני, משקל 0)' are stripped) or a CSV with
            the same headers or English keys (ticker, alert_date, direction, cum_d1..cum_d20).
  extras  : CSVs joined on (ticker, alert date[, direction]) - e.g. scan_raw.csv of the runs (t, date/asof) to bring exp_* columns
            that the tracker does not carry. Existing tracker values win.
  ledger  : platform_verdicts_ledger.csv (decision_point 'entry'; trial rows and rows before forward_only_from are dropped).
Outcomes (per tracker row, direction-adjusted as the tracker: SHORT gains when price falls)
  ret_d5/10/20 = tracker 'יום k' (cum return vs the alert price); bench = SPY (stocks) / BTC-USD (crypto), day 1 = first bench
  session >= alert date, base = last bench close before day 1 (same as build7 excess_spy_d20);
  excess_dk = ret_dk - sgn * bench_dk = sgn x (stock - bench) (room convention 08.10: a short is compared with being short the
  benchmark). Day 20: the tracker column excess_dir_d20 (build7) is used when present and filled; otherwise computed here.
  Bench closes come from tracker/prices_all.pkl first (price return, identical to build7), yfinance only extends past its end.
  A "result" = a row whose primary horizon (default day 20) is complete. Rows marked 'לא נספר' (duplicates) are dropped.
Tests (per column, per segment: stock LONG / stock SHORT / crypto LONG, and ALL pooled for direction-aware columns)
  flag rule by kind: flag (bool/0-1) | signed (sign agrees with the trade) | signed_dir (> 0) | pct (>= 50 direction-adjusted)
  | count (> 0) | cat (each level vs the rest) | num (>= median of the measured rows; per side only).
  N flagged / unflagged, hit rate (ret>0, excess>0), mean & median return and excess at the primary horizon, mean excess at
  5/10/20, diff = flagged - unflagged mean excess with 95% CI from two-way clustered SE (ticker x entry date, CGM),
  p = max(ticker-, date-, two-way clustered p), drop-top-1/3-ticker diffs, distinct entry dates,
  Spearman of the flag with momentum_score and (SHORT rows) with the short rule.
  BH-FDR q over ALL testable rows of ALL tools together (testable: >= 20 results per side). Survivor = q < 0.10.
  Status vs the out-of-sample rule: < 15 flagged results 'איסוף', 15-29 'בדיקת ביניים', >= 30 'החלטה'; a decision also needs
  >= MIN_DATES distinct entry dates. Model-verdict columns are always measured from 2026-10-12 even if --since is earlier.
Outputs: CSV (all rows) + Hebrew Markdown section (per-tool summary + top tests) for the report.
CLI:  python3 tool_stats.py TRACKER.xlsx [--extra scan_raw.csv ...] [--ledger LEDGER] [--since 2026-10-12] [--out DIR]
API:  import tool_stats as TS; table, md = TS.run(tracker, extras=[...], ledger=TS.LEDGER, since='2026-10-12', out_dir=None)
"""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, re, sys, math, json, glob, argparse, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, _SCANNER_ROOT)

VERSION = "2026-10-08.3"   # .2: excess_dir_d20 preferred; bench = tracker prices_all.pkl first (same as build7)
                           # .3: Elliott v2 (scanner_elliott_v2) - exp_ev2_* -> tool "elliott_v2"; price/text/tautological ev2 columns = info;
                           #     trade-direction ev2 view built from raw ev2_long_*/ev2_short_* (e.g. scan_hooks.csv extras) when exp_ev2_* is missing
FORWARD_START = "2026-10-12"
LEDGER = (_SCANNER_ROOT + "/scan-runs/platform_verdicts_ledger.csv")
HORIZONS = (5, 10, 20)
MIN_SIDE = 20            # FDR family: >= 20 results on each side
INTERIM_N, DECISION_N = 15, 30
MIN_DATES = 5
Q = 0.10
CACHE = (_SCANNER_ROOT + "/research-models/bench")
MODEL_RE = re.compile(r"^(llm_|grok|perplexity|pplx|claude|gpt|jev|platform_|verdict)", re.I)
INCLUDE_RE = re.compile(r"^(exp_|watch_|sr_|openbb_|obb_|short_(?:si_pct|si_dtc|si_chg|svr_|comp_|squeeze|ib_fee|ib_avail)|tv_|tradingview|llm_|grok|perplexity|pplx|claude|gpt|jev|candle_|liq_|vp\d|vpanc|vp20m|lowvol|momentum_score$)", re.I)
# 10.10: liq-sweep / fib-spiral price levels & times are info only (not tests): exp_fs_A..D, entry/stop/targets, ls_* price levels
PRICE_LSFS_RE = re.compile(r"^exp_(fs_(A|B|C|D|D_time|D_conf_time|entry|stop|lines|target_t1|target_t2|target_786|t1_src|t2_src)|ls_(level|pierce_time|entry_e1|e2_limit|stop|target|atr14|dir))$")
SKIP_RE = re.compile(r"(_date|_at|_lbl|_label_end|_train_end|_bar|_model|_status|_flag|_ts|_utc|_price|_level|_poc|_vah|_val|_near|_lo|_hi|"
                     r"_tgt|_inval|_last|_above|_below|_pwh|_pwl|_pdh|_pdl|_headlines_top3|sector_etf|_patterns|_patterns_prev2|_kind_lbl|"
                     r"_reason|_text|_risk|_cost.*|_version|_from|_age_days|_period_end|_last_filed)$", re.I)
HEB = {"מודל AI": "source", "תאריך התראה": "alert_date", "טיקר": "ticker", "כיוון": "direction", "סה\"כ תשואה": "ret_last",
       "חזרות / סתירות": "dup_note", "סוג טרייד / סורק": "scanner_type", "תשואה מעל SPY ביום 20": "excess_spy_d20", "MCAP": "mcap",
       "תשואה עודפת מכוונת מול SPY ביום 20": "excess_dir_d20"}
# Elliott v2 (scanner_elliott_v2, 08.10): FDR backtest elliott-v2-eval/fdr_results.md. Tested: ev2_state / ev2_kind / ev2_abc_type /
# ev2_context (cat), ev2_beyond_target, ev2_fib_stale_v1, ev2_fib_reanchored (flag), ev2_tentative_move_atr (num). NOT tested (info):
# raw price levels, free-text labels / names, and the tautological ones - the tentative pivot exists on 100% of setups (its kind is
# identical to the waves column wz_cur_dir) and 'provisional' only says the count ends on it; ev2_long/short_state duplicate ev2_state.
EV2_INFO = ("ev2_target", "ev2_target_name", "ev2_label", "ev2_long_label", "ev2_short_label", "ev2_long_state", "ev2_short_state",
            "ev2_fib_origin", "ev2_fib_end", "ev2_fib_r618", "ev2_fib_x1618", "ev2_tentative_kind", "ev2_tentative_price",
            "ev2_tentative_date", "ev2_last_bar", "ev2_provisional", "ev2_pivots", "ev2_long_pivots", "ev2_short_pivots",
            "ev2_last_confirmed", "ev2_direction_view", "ev2_flag")
EV2_META = {**{k: "info" for k in EV2_INFO}, **{"exp_" + k: "info" for k in EV2_INFO}, "ev2_beyond_target": "flag",
            "exp_ev2_beyond_target": "flag", "ev2_fib_stale_v1": "flag", "exp_ev2_fib_stale_v1": "flag",
            "ev2_fib_reanchored": "flag", "exp_ev2_fib_reanchored": "flag", "ev2_tentative_move_atr": "num", "exp_ev2_tentative_move_atr": "num"}
EV2_VIEW_KEYS = ("label", "state", "kind", "provisional", "beyond_target", "abc_type", "context", "target", "target_name", "fib_stale_v1",
                 "fib_reanchored", "fib_origin", "fib_end", "fib_r618", "fib_x1618")
def ev2_trade_view(x):
    """exp_ev2_<k> in the TRADE direction from raw ev2_long_<k> / ev2_short_<k> (scan_hooks.csv carries both views; its plain ev2_* is
    the LONG view, so it is never used directly). Tracker values (build7 exp_ev2_*, already trade view) win. View-free keys
    (ev2_tentative_*, ev2_last_bar) are copied as-is."""
    if not any(str(c).startswith(("ev2_long_", "ev2_short_")) for c in x.columns): return x
    x = x.copy(); lng = x["direction"].astype(str).str.upper().ne("SHORT")
    for k in EV2_VIEW_KEYS:
        a, b, t = f"ev2_long_{k}", f"ev2_short_{k}", f"exp_ev2_{k}"
        if a not in x.columns and b not in x.columns: continue
        v = pd.Series(np.where(lng, x[a] if a in x.columns else None, x[b] if b in x.columns else None), index=x.index, dtype=object)
        x[t] = x[t].where(x[t].notna(), v) if t in x.columns else v
    for k in ("tentative_kind", "tentative_price", "tentative_date", "tentative_move_atr", "tentative_back_atr", "last_bar"):
        if f"ev2_{k}" in x.columns:
            t = f"exp_ev2_{k}"; x[t] = x[t].where(x[t].notna(), x[f"ev2_{k}"]) if t in x.columns else x[f"ev2_{k}"]
    return x
TRACKER_EXCESS = {20: "excess_dir_d20"}   # build7 column (direction x (stock - SPY), stocks only) - preferred over our own computation
SEG_ORDER = ["ALL", "stock LONG", "stock SHORT", "crypto LONG", "crypto SHORT"]

# ------------------------------------------------------------------ small stats toolkit (no scipy needed)
def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1, a - 1; c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > 1e-300 else 1e-300); h = d
    for m in range(1, 300):
        m2 = 2 * m; aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > 1e-300 else 1e-300); c = 1 + aa / c if abs(c) > 1e-300 else 1e300; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > 1e-300 else 1e-300); c = 1 + aa / c if abs(c) > 1e-300 else 1e300; de = d * c; h *= de
        if abs(de - 1) < 1e-12: break
    return h
def _ibeta(a, b, x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    return math.exp(lb) * _betacf(a, b, x) / a if x < (a + 1) / (a + b + 2) else 1 - math.exp(lb) * _betacf(b, a, 1 - x) / b
def t_p2(t, df):
    if not np.isfinite(t) or df <= 0: return np.nan
    return _ibeta(df / 2, 0.5, df / (df + t * t))
def t_crit(df, p=0.05):
    lo, hi = 0.0, 100.0
    for _ in range(80):
        m = (lo + hi) / 2
        if t_p2(m, df) > p: lo = m
        else: hi = m
    return (lo + hi) / 2

def _clvar(X, e, g):
    """cluster-robust sandwich for OLS with design X (n x k) and residuals e, clusters g"""
    XtXi = np.linalg.pinv(X.T @ X); k = X.shape[1]; meat = np.zeros((k, k))
    u = pd.DataFrame(X * e[:, None]).groupby(np.asarray(g)).sum().values
    G = len(u); meat = u.T @ u; n = len(e)
    c = G / max(G - 1, 1) * (n - 1) / max(n - k, 1)
    return c * XtXi @ meat @ XtXi, G
def diff_test(y, f, tk, dt):
    """flagged - unflagged mean with ticker / date / two-way clustered SE. Returns dict."""
    y = np.asarray(y, float); f = np.asarray(f, float); X = np.c_[np.ones(len(y)), f]
    b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b
    Vt, Gt = _clvar(X, e, tk); Vd, Gd = _clvar(X, e, dt); Vi, _ = _clvar(X, e, pd.Series(tk).astype(str).values + "|" + pd.Series(dt).astype(str).values)
    V2 = Vt + Vd - Vi
    se = {"tk": math.sqrt(max(Vt[1, 1], 0)), "dt": math.sqrt(max(Vd[1, 1], 0))}
    se["2w"] = math.sqrt(V2[1, 1]) if V2[1, 1] > 0 else max(se["tk"], se["dt"])
    dfree = max(min(Gt, Gd) - 1, 1)
    p = {k: (t_p2(b[1] / s, dfree) if s > 0 else np.nan) for k, s in se.items()}
    tc = t_crit(dfree); sc = max(se.values())            # conservative CI: the widest of ticker / date / two-way SE
    return dict(diff=b[1], se=sc, ci_lo=b[1] - tc * sc, ci_hi=b[1] + tc * sc, p_ticker=p["tk"], p_date=p["dt"],
                p_2way=p["2w"], p=np.nanmax([p["tk"], p["dt"], p["2w"]]), clusters_ticker=Gt, clusters_date=Gd)
def spearman(a, b):
    a = pd.Series(a, dtype=float); b = pd.Series(b, dtype=float); m = a.notna() & b.notna()
    if m.sum() < 5 or a[m].nunique() < 2 or b[m].nunique() < 2: return np.nan
    return float(np.corrcoef(a[m].rank(), b[m].rank())[0, 1])
def bh(p):
    p = np.asarray(p, float); q = np.full(len(p), np.nan); m = np.isfinite(p); n = int(m.sum())
    if not n: return q
    idx = np.where(m)[0]; o = idx[np.argsort(p[idx])]; r = p[o] * n / np.arange(1, n + 1)
    q[o] = np.minimum.accumulate(r[::-1])[::-1].clip(max=1); return q

# ------------------------------------------------------------------ loading
def _norm_head(h):
    h = str(h).strip(); h0 = re.sub(r"\s*\([^()]*\)\s*$", "", h).strip()
    if h0 in HEB: return HEB[h0]
    m = re.match(r"^יום (\d+)$", h0)
    if m: return f"cum_d{int(m.group(1))}"
    return h0
def _fund_map():
    try:
        import scanner_fundamentals as F
        return {h: k for h, k in zip(F.TRACKER_HEAD, F.TRACKER_KEYS)}
    except Exception: return {}
def load_tracker(path, sheet=None):
    if str(path).lower().endswith((".xlsx", ".xlsm")):
        x = pd.read_excel(path, sheet_name=sheet if sheet is not None else 0)
    else:
        x = pd.read_csv(path)
    fm = _fund_map(); cols = []
    for c in x.columns:
        n = _norm_head(c); n = fm.get(n, fm.get(str(c).strip(), n)); cols.append(n)
    x.columns = cols; x = x.loc[:, ~pd.Index(cols).duplicated()]
    ren = {"t": "ticker", "date": "alert_date", "dir": "direction", "model": "source"}
    x = x.rename(columns={k: v for k, v in ren.items() if k in x.columns and v not in x.columns})
    x["alert_date"] = pd.to_datetime(x["alert_date"], errors="coerce").dt.normalize()
    x["direction"] = x["direction"].astype(str).str.upper().str.strip()
    x["ticker"] = x["ticker"].astype(str).str.strip().str.upper()
    if "asset" not in x.columns:
        cr = x["ticker"].str.endswith("-USD") | x.get("scanner_type", pd.Series("", index=x.index)).astype(str).eq("קריפטו")
        x["asset"] = np.where(cr, "crypto", "stock")
    x["dup_skip"] = x.get("dup_note", pd.Series("", index=x.index)).fillna("").astype(str).str.startswith("לא נספר")
    return x
def _key_date(d):
    return pd.to_datetime(d, errors="coerce", utc=False)
def merge_extra(x, path):
    e = pd.read_csv(path)
    e = e.rename(columns={"t": "ticker", "dir": "direction", "rc_direction": "direction"})
    if "alert_date" not in e.columns:
        for c in ("asof_local", "scan_date", "date"):
            if c in e.columns:
                e["alert_date"] = pd.to_datetime(e[c].astype(str).str[:10], errors="coerce"); break
    if "alert_date" not in e.columns:      # scan-runs/<YYYY-MM-DD_HHMM...>/file.csv -> the run folder date (IL) = tracker alert date
        m = re.match(r"^(\d{4}-\d\d-\d\d)", os.path.basename(os.path.dirname(os.path.abspath(path))))
        if not m: raise ValueError(f"{path}: no alert_date column and no dated run folder")
        e["alert_date"] = pd.Timestamp(m.group(1))
    e["alert_date"] = pd.to_datetime(e["alert_date"], errors="coerce").dt.normalize(); e["ticker"] = e["ticker"].astype(str).str.upper()
    on = ["ticker", "alert_date"] + (["direction"] if "direction" in e.columns else [])
    if "direction" in e.columns: e["direction"] = e["direction"].astype(str).str.upper()
    e = e.drop_duplicates(on, keep="last")
    new = [c for c in e.columns if c not in on]
    m = x.merge(e[on + new], on=on, how="left", suffixes=("", "__x"))
    for c in new:                              # tracker values win, extras fill the gaps
        if c + "__x" in m.columns:
            m[c] = m[c].where(m[c].notna(), m[c + "__x"]); m = m.drop(columns=c + "__x")
    return m
def _jev_num(v):
    m = re.search(r"([+-]?\d+(?:\.\d+)?)\)?\s*$", str(v)); return float(m.group(1)) if m else np.nan
def ledger_columns(path=LEDGER, forward_start=FORWARD_START, include_trial=False):
    """platform_verdicts_ledger.csv -> one row per (ticker, direction, scan date) with llm_* columns."""
    if not path or not os.path.exists(path): return None
    L = pd.read_csv(path)
    if "decision_point" in L: L = L[L.decision_point.astype(str).eq("entry")]
    is_tr = L.trial.astype(str).str.lower().isin(["true", "1"]) if "trial" in L else pd.Series(False, index=L.index)
    if not include_trial: L = L[~is_tr]
    else:   # 16.10: trial rows kept but tagged; models in the 08.10 trial saw NO chart images -> separable
        L = L.copy(); L["source"] = np.where(is_tr[L.index], "trial-" + L.asof_local.astype(str).str[:10], "forward")
        L["chart_images"] = L.get("image_input", pd.Series(index=L.index, dtype=object)).astype(str).eq("image")
        forward_start = "2000-01-01"; L["forward_only_from"] = forward_start
    L["alert_date"] = pd.to_datetime(L.asof_local.astype(str).str[:10], errors="coerce")
    fo = pd.to_datetime(L.get("forward_only_from", forward_start), errors="coerce").fillna(pd.Timestamp(forward_start))
    L = L[L.alert_date >= np.maximum(fo, pd.Timestamp(forward_start))]
    if L.empty: return pd.DataFrame(columns=["ticker", "direction", "alert_date"])
    L["ticker"] = L.ticker.astype(str).str.upper(); L["direction"] = L.direction.astype(str).str.upper()
    out = {}
    for (t, d, a), g in L.groupby(["ticker", "direction", "alert_date"]):
        r = {}
        if include_trial: r["llm_source"] = g.source.iloc[0]; r["llm_chart_images"] = bool(g.chart_images.any())
        for _, z in g.iterrows():
            p = str(z.platform).lower(); v = str(z.verdict).strip().lower() if pd.notna(z.verdict) else None
            if v is None or v in ("nan", ""): continue
            if p == "jev":
                s = _jev_num(z.verdict); r["llm_jev_sentiment"] = s
                r["llm_jev_verdict"] = "positive" if s > 0.25 else ("negative" if s < -0.25 else "neutral")
            else:
                r[f"llm_{p}_verdict"] = v
                if pd.notna(z.get("conviction_or_sentiment")): r[f"llm_{p}_conviction"] = float(z.conviction_or_sentiment)
            if p == "gpt":
                r["llm_gpt_veto"] = v == "veto"; r["llm_gpt_flag_or_veto"] = v in ("veto", "flag")
            if p == "grok": r["llm_grok_approve"] = v == "approve"; r["llm_grok_veto"] = v == "veto"
            if p == "pplx": r["llm_pplx_approve"] = v == "approve"; r["llm_pplx_flag"] = v == "flag"
            if p == "claude": r["llm_claude_supports"] = v == "supports"
        out[(t, d, a)] = r
    X = pd.DataFrame.from_dict(out, orient="index"); X.index.names = ["ticker", "direction", "alert_date"]
    return X.reset_index()
LEDGER_META = {"llm_source": "info", "llm_chart_images": "info", "llm_jev_sentiment": "signed", "llm_pplx_flag": "flag", "llm_jev_verdict": "info", "llm_grok_verdict": "info",
               "llm_pplx_verdict": "info", "llm_claude_verdict": "info", "llm_gpt_verdict": "info",   # covered by the explicit flags below
               "llm_gpt_veto": "flag", "llm_gpt_flag_or_veto": "flag", "llm_grok_approve": "flag",
               "llm_grok_veto": "flag", "llm_pplx_approve": "flag", "llm_claude_supports": "flag"}

# ------------------------------------------------------------------ outcomes
def bench_series(sym):
    """daily closes for SPY / BTC-USD: tracker prices_all.pkl first, else yfinance (cached per day)."""
    try:
        p = pd.read_pickle((_SCANNER_ROOT + "/tracker/prices_all.pkl"))
        if sym in p.columns.get_level_values(0):
            s = p[sym]["Close"].dropna(); s.index = pd.to_datetime(s.index); cached = s
        else: cached = None
    except Exception: cached = None
    os.makedirs(CACHE, exist_ok=True); f = f"{CACHE}/{sym}_{pd.Timestamp.now(tz='Asia/Jerusalem'):%Y%m%d}.csv"
    if os.path.exists(f):
        s = pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]
    else:
        try:
            import yfinance as yf
            z = yf.download(sym, start="2026-01-01", interval="1d", auto_adjust=True, progress=False)
            if isinstance(z.columns, pd.MultiIndex): z.columns = z.columns.get_level_values(0)
            s = z["Close"].dropna(); s.index = pd.to_datetime(s.index).tz_localize(None); s.to_csv(f)
        except Exception:
            s = cached
    if cached is not None and s is not None:       # tracker closes win (same series as build7); yfinance only extends past them
        s = pd.concat([cached, s[s.index > cached.index.max()]])
    elif s is None: s = cached
    return s
def add_outcomes(x, horizons=HORIZONS):
    x = x.copy(); x["sgn"] = np.where(x.direction.eq("SHORT"), -1, 1)
    B = {"stock": bench_series("SPY"), "crypto": bench_series("BTC-USD")}
    for k in horizons:
        x[f"ret_d{k}"] = pd.to_numeric(x.get(f"cum_d{k}"), errors="coerce")
        bk = []
        for a, d in zip(x.asset, x.alert_date):
            s = B.get(a)
            if s is None or pd.isna(d): bk.append(np.nan); continue
            post = s.index[s.index >= d]; pre = s.index[s.index < d]
            bk.append(float(s[post[k - 1]] / s[pre[-1]] - 1) if len(post) >= k and len(pre) else np.nan)
        x[f"bench_d{k}"] = bk
        x[f"excess_d{k}"] = x[f"ret_d{k}"] - x.sgn * x[f"bench_d{k}"]
        x[f"excess_src_d{k}"] = np.where(x[f"excess_d{k}"].notna(), "computed", None)
        tc = TRACKER_EXCESS.get(k)
        if tc and tc in x.columns:                 # prefer the tracker's directional column where it is filled
            v = pd.to_numeric(x[tc], errors="coerce")
            use = v.notna() & x[f"ret_d{k}"].notna()
            x.loc[use, f"excess_d{k}"] = v[use]; x.loc[use, f"excess_src_d{k}"] = tc
    return x

# ------------------------------------------------------------------ columns -> flags
def tool_of(col):
    c = col.lower()
    if c.startswith("llm_"): return c.split("_")[1]
    if c.startswith(("exp_ev2_", "ev2_")): return "elliott_v2"
    if c.startswith("exp_"):
        t = c.split("_")[1]
        return {"spiral": "geometry", "gann": "geometry", "anchor": "geometry"}.get(t, t)
    if c.startswith(("vp", "candle_", "liq_")): return "geometry"
    if c.startswith("watch_short_below_va120"): return "va120"
    if c.startswith("sr_"): return "sr_levels"
    if c.startswith(("openbb_", "obb_")): return "openbb"
    if c.startswith("short_"): return "short_data"   # scanner_short.py (FINRA SI by publication date, Reg SHO z, squeeze, IBKR borrow)
    if c.startswith(("tv_", "tradingview")): return "tradingview"
    if c in _fund_keys(): return "fundamentals"
    if c.startswith("momentum_score"): return "momentum (reference)"
    if MODEL_RE.match(c): return re.split(r"[_ ]", c)[0]
    return "other"
_FK = None
def _fund_keys():
    global _FK
    if _FK is None:
        try:
            import scanner_fundamentals as F; _FK = set(k.lower() for k in F.TRACKER_KEYS)
        except Exception: _FK = set()
    return _FK
def _meta():
    m = dict(LEDGER_META); m.update(EV2_META); m["watch_short_below_va120"] = "flag"; m["momentum_score"] = "pct"
    try:
        import research_columns as RC; m.update(RC.COLUMN_META)
    except Exception: pass
    return m
def kind_of(col, s, meta):
    if col in meta: return meta[col]
    if PRICE_LSFS_RE.match(col): return "info"
    if SKIP_RE.search(col) and not col.startswith("watch_"): return "info"
    v = s.dropna()
    if not len(v): return "empty"
    if v.map(lambda z: isinstance(z, (bool, np.bool_))).all(): return "flag"
    num = pd.to_numeric(v, errors="coerce")
    if num.notna().mean() >= 0.95:
        u = set(num.dropna().unique())
        if u <= {0, 1}: return "flag"
        if u <= {-1, 0, 1}: return "signed"
        return "num"
    sv = v.astype(str).str.lower()
    if sv.isin(["true", "false"]).all(): return "flag"
    if sv.str.match(r"^\d{4}-\d\d-\d\d").mean() > 0.5: return "info"
    if sv.nunique() <= 12: return "cat"
    return "info"
def _bool(s):
    return s.map(lambda z: np.nan if pd.isna(z) else (str(z).strip().lower() in ("true", "1", "1.0", "yes")))
def flags(col, kind, s, sgn, ref_median=None):
    """list of (test_label, flagged Series of True/False/NaN)"""
    if kind == "flag": return [("== True", _bool(s))]
    num = pd.to_numeric(s, errors="coerce")
    if kind == "signed": return [("sign agrees with direction", (np.sign(num) * sgn > 0).where(num.notna()))]
    if kind == "signed_dir": return [("> 0", (num > 0).where(num.notna()))]
    if kind == "pct": return [(">= 50 (direction-adjusted)", (num >= 50).where(num.notna()))]
    if kind == "count": return [("> 0", (num > 0).where(num.notna()))]
    if kind == "num":
        med = ref_median if ref_median is not None else num.median()
        return [(f">= median ({med:.4g})", (num >= med).where(num.notna()))]
    if kind == "cat":
        sv = s.where(s.notna()).astype(str).str.strip().str.lower().where(s.notna())
        lv = set(sv.dropna().unique())
        if lv and lv <= {"long", "short", "neutral", "none"}:      # a direction call -> agreement flag
            return [("call agrees with direction", (sv.str.upper() == pd.Series(np.where(sgn > 0, "LONG", "SHORT"), index=s.index)).where(sv.notna()))]
        return [(f"== {l}", (sv == l).where(sv.notna())) for l in sorted(lv)]
    return []

# ------------------------------------------------------------------ main computation
def _status(n_res, n_dates, testable):
    if n_res < INTERIM_N: return f"איסוף ({n_res}/{INTERIM_N})"
    if n_res < DECISION_N: return f"בדיקת ביניים ({n_res}/{DECISION_N})"
    if n_dates < MIN_DATES: return f"30+ תוצאות, ממתין לגיוון ימי כניסה ({n_dates}/{MIN_DATES})"
    return "החלטה" if testable else "החלטה (צד ההשוואה קטן מ-20)"
def compute(x, since=FORWARD_START, horizon=20, cols=None, include_re=None, min_side=MIN_SIDE, forward_start=FORWARD_START):
    meta = _meta(); since = pd.Timestamp(since)
    x = x[~x.dup_skip & x.alert_date.notna() & x.direction.isin(["LONG", "SHORT"])].copy()
    inc = re.compile(include_re, re.I) if include_re else INCLUDE_RE
    fk = _fund_keys()
    cand = cols or [c for c in x.columns if inc.match(str(c)) or (not include_re and str(c).lower() in fk)]
    if "short_rule_pass" in x.columns: srp = _bool(x.short_rule_pass)
    elif "stop_type" in x.columns: srp = x.stop_type.astype(str).str.contains("short rule failed").map(lambda b: not b).where(x.stop_type.notna() & x.direction.eq("SHORT"))
    else: srp = pd.Series(np.nan, index=x.index)
    x["_srp"] = srp; x["_mom"] = pd.to_numeric(x.get("momentum_score"), errors="coerce")
    y_ex, y_raw = f"excess_d{horizon}", f"ret_d{horizon}"
    rows = []
    for col in cand:
        s_all = x[col]; kind = kind_of(col, s_all, meta)
        if kind in ("info", "empty"): continue
        fwd = bool(MODEL_RE.match(col)); st = max(since, pd.Timestamp(forward_start)) if fwd else since
        sub = x[x.alert_date >= st]
        if sub[col].notna().sum() == 0: continue
        segs = [("ALL", sub)] if kind != "num" else []
        for (a, d), g in sub.groupby(["asset", "direction"]): segs.append((f"{a} {d}", g))
        for seg, g in segs:
            med = pd.to_numeric(g[col], errors="coerce").median() if kind == "num" else None
            for lab, fl in flags(col, kind, g[col], g.sgn.values, med):
                m = fl.notna()
                if not m.any(): continue
                gg = g[m]; f = fl[m].astype(bool)
                res = gg[y_ex].notna() & gg[y_raw].notna()
                fr, ur = gg[res & f], gg[res & ~f]
                r = dict(tool=tool_of(col), column=col, kind=kind, test=lab, segment=seg, forward_only=fwd, since=str(st.date()),
                         n_logged=int(m.sum()), n_flagged=int(f.sum()), n_unflagged=int((~f).sum()),
                         n_results_flagged=len(fr), n_results_unflagged=len(ur),
                         entry_dates_flagged=int(fr.alert_date.nunique()), entry_dates_all=int(gg[res].alert_date.nunique()),
                         first_entry=str(gg.alert_date.min().date()), last_entry=str(gg.alert_date.max().date()))
                for k in HORIZONS:
                    a_ = gg[f & gg[f"excess_d{k}"].notna()]; b_ = gg[~f & gg[f"excess_d{k}"].notna()]
                    r[f"flag_mean_ret_d{k}"] = a_[f"ret_d{k}"].mean() if len(a_) else np.nan
                    r[f"flag_mean_excess_d{k}"] = a_[f"excess_d{k}"].mean() if len(a_) else np.nan
                    r[f"unflag_mean_excess_d{k}"] = b_[f"excess_d{k}"].mean() if len(b_) else np.nan
                    r[f"n_flag_d{k}"] = len(a_)
                if len(fr):
                    r.update(hit_rate=(fr[y_raw] > 0).mean(), hit_rate_excess=(fr[y_ex] > 0).mean(), mean_ret=fr[y_raw].mean(),
                             median_ret=fr[y_raw].median(), mean_excess=fr[y_ex].mean(), median_excess=fr[y_ex].median())
                if len(ur): r.update(unflag_hit_rate=(ur[y_raw] > 0).mean(), unflag_mean_excess=ur[y_ex].mean(), unflag_median_excess=ur[y_ex].median())
                both = gg[res]
                if len(fr) >= 3 and len(ur) >= 3:
                    try:
                        r.update(diff_test(both[y_ex].values, f[res].values.astype(float), both.ticker.values, both.alert_date.values))
                        r["median_diff"] = fr[y_ex].median() - ur[y_ex].median()
                        top = fr.groupby("ticker")[y_ex].sum().sort_values(ascending=r["diff"] < 0).index
                        for kk in (1, 3):
                            z = both[~both.ticker.isin(top[:kk])]; fz = f[res][~both.ticker.isin(top[:kk])]
                            r[f"diff_drop_top{kk}"] = z[y_ex][fz].mean() - z[y_ex][~fz].mean() if fz.any() and (~fz).any() else np.nan
                    except Exception as e: r["test_error"] = f"{e.__class__.__name__}: {e}"
                r["corr_momentum"] = spearman(f.astype(float), gg["_mom"])
                sh = gg.direction.eq("SHORT") & gg["_srp"].notna()
                r["corr_short_rule"] = spearman(f[sh].astype(float), gg["_srp"][sh].astype(float)) if sh.sum() >= 5 else np.nan
                r["testable"] = bool(len(fr) >= min_side and len(ur) >= min_side and np.isfinite(r.get("p", np.nan)))
                rows.append(r)
    T = pd.DataFrame(rows)
    if T.empty: return T
    for c in ("diff", "se", "ci_lo", "ci_hi", "p_ticker", "p_date", "p_2way", "p", "median_diff", "diff_drop_top1", "diff_drop_top3",
              "hit_rate", "hit_rate_excess", "mean_ret", "median_ret", "mean_excess", "median_excess", "unflag_hit_rate", "unflag_mean_excess"):
        if c not in T.columns: T[c] = np.nan
    T["q_bh"] = np.nan; m = T.testable
    T.loc[m, "q_bh"] = bh(T.loc[m, "p"].values)
    def robust(r):
        if not (r.get("q_bh", 1) < Q): return None
        sg = np.sign(r["diff"])
        return bool(all(np.sign(r.get(k, np.nan)) == sg for k in ("median_diff", "diff_drop_top1", "diff_drop_top3")))
    T["robust"] = T.apply(robust, axis=1)
    T["survives_fdr"] = T.q_bh < Q
    T["status"] = [_status(int(a), int(b), bool(c)) for a, b, c in zip(T.n_results_flagged, T.entry_dates_flagged, T.testable)]
    T["verdict"] = np.where(T.survives_fdr & (T["diff"] > 0) & T.robust.fillna(False).astype(bool) & T.status.eq("החלטה"), "מועמד למשקל (החלטת אילן)",
                   np.where(T.status.eq("החלטה") & ~T.survives_fdr, "אין ראיה - נשאר במשקל 0", ""))
    T["seg_o"] = T.segment.map({s: i for i, s in enumerate(SEG_ORDER)})
    T = T.sort_values(["tool", "column", "seg_o", "test"]).drop(columns="seg_o").reset_index(drop=True)
    return T

# ------------------------------------------------------------------ Hebrew markdown
def _pp(v, d=1): return "—" if v is None or not np.isfinite(v) else f"{v*100:+.{d}f}"
def _pc(v): return "—" if v is None or not np.isfinite(v) else f"{v*100:.0f}%"
def markdown(T, since=FORWARD_START, horizon=20, n_rows=0, top=15):
    L = [f"### כלים ניסיוניים (משקל 0) — סטטיסטיקה קדימה מ-{pd.Timestamp(since):%d.%m.%Y}", "",
         f"מדד עיקרי: תשואה עודפת ביום {horizon} מול SPY (מניות) / BTC (קריפטו), מותאמת כיוון. כלל: {INTERIM_N} תוצאות = בדיקת ביניים, "
         f"{DECISION_N} = החלטה (ולפחות {MIN_DATES} ימי כניסה שונים). FDR ‏(BH, q<{Q:.2f}) על כל הכלים יחד, רק בדיקות עם {MIN_SIDE}+ תוצאות בכל צד. "
         f"קביעות מודלים (Grok, Perplexity, Claude, GPT, Jev) נמדדות רק מ-12.10. שורות במעקב: {n_rows}.", ""]
    if T is None or T.empty:
        L.append("_עדיין אין שורות עם עמודות ניסיוניות בתקופת המדידה._"); return "\n".join(L)
    best = T.sort_values(["n_results_flagged"], ascending=False)
    L += ["| כלי | עמודות נבדקות | שורות מתועדות | תוצאות מסומנות (מקס׳) | ימי כניסה | הבדיקה החזקה | הפרש עודף (נק׳ %) [95% CI] | q | סטטוס |",
          "|---|---|---|---|---|---|---|---|---|"]
    for tool, g in T.groupby("tool"):
        b = g.sort_values(["p", "n_results_flagged"], ascending=[True, False], na_position="last").iloc[0]
        ci = f"{_pp(b.get('diff'))} [{_pp(b.get('ci_lo'))}, {_pp(b.get('ci_hi'))}]" if np.isfinite(b.get("diff", np.nan)) else "—"
        q = f"{b['q_bh']:.2f}" if np.isfinite(b.get("q_bh", np.nan)) else "—"
        st = b["status"]
        L.append(f"| {tool} | {g.column.nunique()} | {int(g.n_logged.max())} | {int(g.n_results_flagged.max())} | {int(g.entry_dates_flagged.max())} | "
                 f"{b['column']} {b['test']} ({b['segment']}) | {ci} | {q} | {st} |")
    L += ["", f"**בדיקות מובילות (לפי p, עד {top}):**", "",
          "| עמודה | בדיקה | מקטע | מסומן/לא | הצלחה | ממוצע עודף מסומן | חציון | הפרש [CI] | p | q | מתאם למומנטום | סטטוס |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in T[np.isfinite(T.get("p", pd.Series(np.nan, index=T.index)))].sort_values("p").head(top).iterrows():
        L.append(f"| {r.column} | {r.test} | {r.segment} | {int(r.n_results_flagged)}/{int(r.n_results_unflagged)} | {_pc(r.get('hit_rate'))} | "
                 f"{_pp(r.get('mean_excess'))} | {_pp(r.get('median_excess'))} | {_pp(r.get('diff'))} [{_pp(r.get('ci_lo'))}, {_pp(r.get('ci_hi'))}] | "
                 f"{r['p']:.3f} | {('%.2f' % r['q_bh']) if np.isfinite(r.get('q_bh', np.nan)) else '—'} | "
                 f"{('%.2f' % r['corr_momentum']) if np.isfinite(r.get('corr_momentum', np.nan)) else '—'} | {r.status} |")
    surv = T[T.survives_fdr.fillna(False)]
    L += ["", f"שורדי FDR: {len(surv)} מתוך {int(T.testable.sum())} בדיקות שעמדו בסף. " +
          ("אף כלי לא עבר את הסף — כולם נשארים במשקל 0." if not len(surv) else
           "עברו: " + "; ".join(f"{r.column} {r.test} ({r.segment}, q={r.q_bh:.2f}, {'יציב' if r.robust else 'לא יציב'})" for _, r in surv.iterrows()) +
           " — עדיין משקל 0 עד החלטה של אילן.")]
    return "\n".join(L)

# ------------------------------------------------------------------ API / CLI
def run(tracker, extras=(), ledger=LEDGER, since=FORWARD_START, horizon=20, out_dir=None, cols=None, include_re=None, sheet=None, min_side=MIN_SIDE,
        forward_start=FORWARD_START):
    """forward_start: first date for model-verdict columns (keep the default; lower it only for pipeline tests)."""
    x = load_tracker(tracker, sheet)
    for e in extras or ():
        for p in sorted(glob.glob(e)): x = merge_extra(x, p)
    x = ev2_trade_view(x)
    Lg = ledger_columns(ledger, forward_start) if ledger else None
    if Lg is not None and len(Lg):
        Lg = Lg[[c for c in Lg.columns if c in ("ticker", "direction", "alert_date") or c not in x.columns]]
        x = x.merge(Lg, on=["ticker", "direction", "alert_date"], how="left")
    x = add_outcomes(x)
    T = compute(x, since, horizon, cols, include_re, min_side, forward_start)
    md = markdown(T, since, horizon, n_rows=int((x.alert_date >= pd.Timestamp(since)).sum()))
    if forward_start != FORWARD_START: md = "**בדיקת צנרת בלבד - תאריך התחלה לקביעות מודלים שונה מ-12.10**\n\n" + md
    if out_dir:
        os.makedirs(out_dir, exist_ok=True); stamp = pd.Timestamp.now(tz="Asia/Jerusalem").strftime("%Y-%m-%d_%H%M")
        T.to_csv(f"{out_dir}/tool_stats_{stamp}.csv", index=False)
        open(f"{out_dir}/tool_stats_{stamp}_he.md", "w").write(md)
        json.dump(dict(version=VERSION, tracker=str(tracker), extras=list(extras or ()), ledger=ledger, since=str(since), horizon=horizon,
                       rows_measured=int((x.alert_date >= pd.Timestamp(since)).sum()), tests=int(len(T)),
                       testable=int(T.testable.sum()) if len(T) else 0,
                       excess_d20_source={str(k): int(v) for k, v in x.get(f"excess_src_d{horizon}", pd.Series(dtype=object)).value_counts().items()}), open(f"{out_dir}/tool_stats_{stamp}_meta.json", "w"), indent=1)
    return T, md

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tracker"); ap.add_argument("--extra", nargs="*", default=[]); ap.add_argument("--ledger", default=LEDGER)
    ap.add_argument("--no-ledger", action="store_true"); ap.add_argument("--since", default=FORWARD_START); ap.add_argument("--horizon", type=int, default=20)
    ap.add_argument("--out", default=(_SCANNER_ROOT + "/research-models/tool_stats")); ap.add_argument("--cols", nargs="*"); ap.add_argument("--include-re")
    ap.add_argument("--min-side", type=int, default=MIN_SIDE)
    a = ap.parse_args()
    T, md = run(a.tracker, a.extra, None if a.no_ledger else a.ledger, a.since, a.horizon, a.out, a.cols, a.include_re, min_side=a.min_side)
    print(md)
