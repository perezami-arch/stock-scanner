"""Writes iaf/geometry_table.md (every comparison) and the §3.14 block (geo_section.md) from geometry_table.csv."""
import numpy as np, pandas as pd
OUT='/workspace/trading-frameworks-eval/iaf/'
A=pd.read_csv(OUT+'geometry_table.csv'); M=int(A.n_comparisons.iloc[0])
LC=pd.read_csv(OUT+'geo_leakcheck.csv'); LM=pd.read_csv(OUT+'geo_leakcheck_mismatches.csv') if open(OUT+'geo_leakcheck_mismatches.csv').read().strip() else pd.DataFrame()
def f1(x): return '' if pd.isna(x) else f'{x:+.1f}'
def fp(x): return '' if pd.isna(x) else (f'{x:.4f}' if x>=0.0001 else '<0.0001')
def tab(df,cols,heads):
    out=['| '+' | '.join(heads)+' |','|'+'---|'*len(heads)]
    for _,r in df.iterrows():
        v=[]
        for c in cols:
            x=r[c]
            if c in ('N_with','N_without'): v.append(str(int(x)))
            elif c in ('p','q_BH','p_incr','p_ticker_only'): v.append(fp(x))
            elif c in ('coverage','changed','hit_with','hit_without','level_med_atr'): v.append('' if pd.isna(x) else (f'{x:.0f}' if c!='level_med_atr' else f'{x:.1f}'))
            elif isinstance(x,(float,np.floating)): v.append(f1(x))
            else: v.append(str(x))
        out.append('| '+' | '.join(v)+' |')
    return '\n'.join(out)
fam=A.groupby(['kind','family']).agg(n=('p','size'),nom=('p',lambda x:int((x<0.05).sum())),q10=('q_BH',lambda x:int((x<0.10).sum())),rob=('flag',lambda x:int((x=='ROBUST').sum()))).reset_index()
fam['exp']=fam.n*0.05
famtab='| kind | family | comparisons | p<0.05 (nominal) | expected by chance | q<0.10 (BH) | ROBUST |\n|---|---|---|---|---|---|---|\n'+'\n'.join(
    f'| {r.kind} | {r.family} | {r.n} | {r.nom} | {r.exp:.1f} | {r.q10} | {r.rob} |' for r in fam.itertuples())+f'\n| **total** | | **{M}** | **{int((A.p<0.05).sum())}** | **{0.05*M:.1f}** | **{int((A.q_BH<0.10).sum())}** | **{int((A.flag=="ROBUST").sum())}** |'
F=A[A.kind=='filter']; L=A[A.kind=='level']
fs=F[F.q_BH<0.10].sort_values('p')
fcols=['segment','feature','test','N_with','N_without','mean_with','mean_without','med_with','med_without','diff_x','diff_raw','wd','half1','half2','drop1','drop3','p','q_BH','p_incr','flag']
fheads=['segment','feature','test','N with','N without','x_mkt with','x_mkt without','med x with','med x without','diff x_mkt','diff raw ret','diff within-date','diff 1st half','diff 2nd half','diff w/o top1','diff w/o top3','p','q (BH)','p beyond rule inputs','flag']
ftop=F[(F.q_BH>=0.10)].sort_values('p').head(12)
lc=['segment','feature','N_with','coverage','level_med_atr','changed','mean_with','mean_without','med_with','med_without','hit_with','hit_without','x_with','x_without','diff_raw','drop3','p','q_BH','flag']
lh=['segment','variant','N covered','coverage %','level dist (ATR, median)','% trades changed','mean variant','mean policy','median variant','median policy','hit variant','hit policy','x_mkt variant','x_mkt policy','paired diff','diff w/o top3','p','q (BH)','flag']
Lc=L[L.code.str.endswith('_c')].copy(); Lc['o']=Lc.segment.map({s:i for i,s in enumerate(['All stock LONG','Rule-filtered stock LONG','Perplexity stock LONG','Grok stock LONG','All stock SHORT','Crypto LONG'])})
Lc=Lc.sort_values(['o','code'])
# full table md
full=A.sort_values(['kind','segment','family','p'])
cols_all=['kind','family','segment','feature','test','N_with','N_without','mean_with','mean_without','med_with','med_without','hit_with','hit_without','diff_x','diff_med_x','diff_raw','wd','half1','half2','drop1','drop3','p_ticker_only','p','q_BH','p_incr','flag']
md=(f'### N. Geometry / volume-profile / candle / liquidity columns (scanner_geometry.py) — EVERY comparison. **Total comparisons in the BH family: {M}** '
    '(filter tests: x_mkt = excess vs SPY (stocks) / BTC (crypto) under the active stop policy, close-based; with = feature present / quintile / rank top half; '
    'level tests: paired per-trade difference vs the active policy on covered trades, mean_with/without = variant/policy raw return). '
    'p = max(ticker-clustered, entry-date-clustered, two-way clustered); q = Benjamini-Hochberg over all rows; wd = difference after demeaning x_mkt within entry-date cohorts; '
    'half1/half2 = difference in the earlier/later half of entry dates; p_incr = p of the feature after controlling for the existing rule inputs (20-method score, % vs SMA200, sector uptrend).\n'
    +tab(full,cols_all,cols_all))
open(OUT+'geometry_table.md','w').write(md)
leak_ok=len(LM)==0 and int(LC.late_dates.sum())==0 and int((LC.geo_last_bar!=LC.rule_bar).sum())==0
sec=f'''### 3.14 Geometry, volume profile, candles and liquidity zones (`/workspace/scanner_geometry.py`) — PIT backtest on the scanner setups (group follow-up; `iaf/geo_features.py`, `geo_leakcheck.py`, `sim_geo.py`, `geo_analyze.py`, `geo_report.py`; full table N = `iaf/geometry_table.md|csv`)
**Bottom line: expect noise and that is mostly what came out.** {M} comparisons were run in one Benjamini-Hochberg family; {int((A.p<0.05).sum())} had nominal p<0.05 (≈{0.05*M:.0f} expected by chance). After FDR (q<0.10) and every robustness check, **only 2 of {len(F)} filter comparisons survive, both on stock SHORTS and both re-expressing "the stock is already breaking down" — which the existing short rule (score ≥3 & below SMA200) already captures.** No spiral, Gann, candle-pattern or sweep column survives anywhere (best: candles p=0.04, spiral q=0.41, sweeps — 'any sweep in the last 3 bars' on shorts −4.8 pp, q=0.20 — cluster sweeps and prior-candle breaks separately q≥0.5). In the level tests nothing improves on the active policy; liquidity/FVG take-profits and HVN stops on crypto are **robustly worse**. Nothing here gets score weight; the two short-side survivors are candidates to re-check on the setups from 12.10.2026 onward.

**Setup.** Columns = `geometry_columns(df, cutoff, asset, direction)` exactly as written by the teammate (module not modified), computed for 1,040 setups (all rows; tables use the main sheet, no dups). Cutoff = the same information cutoff every earlier table uses (`setups_prepared.info_cutoff_utc`: stocks = rule-bar close, i.e. previous close for pre/intraday alerts and the alert-day bar only for after-close alerts; crypto = alert minute, Perplexity −70 min). Direction view = the setup's direction; liquidity features are re-expressed relative to the trade (*fwd* = target side, e.g. buy-side pools above a long; *back* = stop side). Outcome = the **active policy** trade (stock longs: ratchet chandelier 4×ATR + ½ at Fib 1.618; stock shorts: ratchet chandelier 4×ATR; crypto longs: fixed 3×ATR; close-based; open trades marked at the 2026-10-07 close). `sim_geo.py` reproduces `sim_ratchet_trades.csv` (rt_ratchet_h618 / rt_ratchet / rt_fixed3, c and i) with 0 mismatches (max |diff| 2e-16). Segments: all stock longs (N=242), rule-filtered stock longs (115), Perplexity stock longs (59), Grok stock longs (142), all stock shorts (189), crypto longs (264, Grok 255 + Perplexity 9). Crypto shorts are frozen by the rules and were not tested.

**1. Independent leak check (30 random setups, seed 20261008).** For each setup the columns were computed 4 ways: full history + cutoff; history physically truncated at the rule bar; all bars after the rule bar replaced by random garbage plus 30 extra garbage bars; truncated with cutoff=None. **{int(LC.n_cols.sum()*3):,} column comparisons, {len(LM)} mismatches.** {int(LC.n_confirmed_cols.sum())} `*_confirmed_at` values plus all past-object dates (anchor, spiral, anchored-VP start, sweep, candle bar) and the confirmation dates of every pool used by the level tests: **{int(LC.late_dates.sum())} later than the cutoff bar**; last visible bar = rule bar in {int((LC.geo_last_bar==LC.rule_bar).sum())}/30. For all 816 main-sheet setups, feeding the module the raw alert time (exact / schedule / UI-log alerts) instead of the tracker cutoff gives the same last visible bar in 100 % of cases (date-only alerts use the conservative tracker cutoff). Verdict: **{'no look-ahead found' if leak_ok else 'LEAK FOUND - see geo_leakcheck_mismatches.csv'}**. (Caveat, not a code leak: daily prices are Yahoo dividend-adjusted, as in every earlier table.)

**2. Method.** Filter test = mean x_mkt with the feature − without, per segment; continuous features: lowest quintile vs rest, highest quintile vs rest, and a rank slope (≈ Q5−Q1). Min N 20 on each side ({{skipped}} candidate comparisons were skipped for N<20 or <5 distinct values and are **not** counted). Sweeps split by `liq_sweep_kind` (pool/cluster sweep vs prior-candle break) and by direction relative to the trade. **p-values are conservative:** the maximum of ticker-clustered, entry-date-clustered and two-way clustered p, because stock setups come from only 22–25 entry dates (the top 5 dates hold 55–60 % of stock trades) — naïve p-values would be far too small. Robust = q<0.10 **and** median difference, raw-return difference, within-entry-date difference, and the difference after dropping the top-1 and top-3 tickers all keep the sign. q<0.10 that fails a check = LUCK.

**Comparisons by family (total {M}):**
{famtab}
All 10 robust level-test rows are robustly **worse** than the active policy (crypto targets and HVN stops); none is an improvement.

**Filter comparisons surviving FDR (q<0.10) — total comparisons in the family: {M}.** x_mkt in % (excess vs SPY), shorts: ret + SPY return.
{tab(fs,fcols,fheads)}

* **vp120 "beyond value area in trade direction"** for shorts = the close is **below the 120-day volume-profile value area**. 37 of these 38 shorts already pass the short rule (score ≥3 & below SMA200), so it is mostly a stricter version of the rule. Inside the 60 rule-filtered shorts: below VA120 (N=37, 30 tickers, 11 dates) +6.2 % mean / +6.8 % median / +7.3 vs SPY / 81 % hit vs the other 23 rule-passers +1.2 % / +1.6 % / +2.3 vs SPY / 61 % hit (descriptive, not in the FDR family). It also stays significant after controlling for the rule inputs (p≈0.02). This is the only lead worth carrying forward, as a **candidate refinement of the short rule**, to be validated on the new setups.
* **liq_fwd_pools_n** for shorts = number of untaken swing-low pools below the price. Fewer pools (price at or under its recent lows) → better shorts. Same story: a breakdown/momentum proxy; 43 of the 49 shorts with ≤1 such pool already pass the short rule. After controlling for the rule inputs it is no longer significant (p≈0.06).

**Closest misses (nominal p<0.05, fail FDR) — total comparisons: {M}.** Listed only so nobody re-discovers them as "signals":
{tab(ftop,['segment','feature','test','N_with','N_without','diff_x','wd','drop3','p','q_BH'],['segment','feature','test','N with','N without','diff x_mkt','diff within-date','diff w/o top3','p','q (BH)'])}
A consistent but non-significant pattern on stock longs: being **inside** the 60/120-day value area beat being extended above it (rule-filtered longs +7 to +8 pp, all longs +3 to +6 pp; q 0.19–0.37). Plausible (do not chase extended names), but not proven here.

**3. Level tests** (paired vs the active policy on covered trades; close-based shown, intraday in table N — total comparisons in the family: {M}). *Stop* = nearest confirmed object beyond the entry −0.5×ATR14 (pool = untaken equal/swing-low cluster, OB = unmitigated order-block zone, HVN = 60/120-bar profile node); `fix` = that level only, `hyb` = the tighter of the level and the policy stop. *Target* = next untaken liquidity pool or open FVG edge in the trade direction, full exit or ½, replacing the 1.618 half on stock longs. No object beyond the entry → the trade stays on the active policy and is not counted.
{tab(Lc,lc,lh)}

* **Stocks: no level rule beats the 4×ATR chandelier.** Pool stops (median 2.7–3.4 ATR from entry vs 4 ATR) change 10–37 % of trades and move the mean by −0.8 to +0.5 pp. HVN stops (≈1.2–1.4 ATR) change 25–44 %, cost 0.2–1.4 pp on longs and cut the hit rate (e.g. all longs 56 → 44 %); on shorts +0.6 pp, noise. OB stops sit ≈6.5–8 ATR away and rarely bind (±0.7 pp). Liquidity / FVG targets raise the hit rate (all longs 53–55 → 58–63 %, rule-filtered 61–67 → 61–80 %) but lower the mean by up to 2.7 pp on longs — the same trade-off as the Fib targets in §3.12; on shorts they change ≤0.5 pp. No stock level difference survives FDR (best q ≈0.3).
* **Crypto: liquidity / FVG targets are robustly harmful.** The nearest pool / FVG sits only ≈1.4–1.7 ATR above entry, so 90–98 % of trades exit early: −13 to −20 pp per covered trade for ½ exits, −25 to −40 pp for full exits (q ≤0.02, robust to dropping the top-3 coins). HVN stops (≈1.5 ATR) are also worse (−10.5 pp close, −13.5 pp intraday; robust at q 0.05 intraday). Pool stops: −3.4 pp, not significant. OB stops: +4.9 pp on 117 trades, p 0.19, noise.

**What this means for the scanner**
* Keep every geometry / volume-profile / candle / liquidity column at **weight 0** (logging only). Spiral, Gann, all 26 candle patterns and the sweep columns (either kind) show nothing.
* **Do not** use liquidity pools, FVGs, order blocks or HVNs as stops or take-profits instead of the active policy; for crypto they are clearly worse.
* The only thing to watch on new setups from 12.10.2026: **stock shorts whose close is below the 120-day value area** (vp120_va_pos = "below VA"), as a possible tightening of the existing short rule. Needs ≈30 closed new trades before any weight.
* Caveats: in-sample, ≈3½ months, 22–25 stock entry dates, most stock trades still open (marked 2026-10-07); clustering-robust p-values are themselves approximate with this few dates.
'''
skipped=pd.read_pickle(OUT+'geo_results.pkl')['skipped']
sec=sec.replace('{skipped}',str(skipped))
open(OUT+'geo_section.md','w').write(sec)
print(sec[:3000]); print('...'); print(len(sec))
