# research_columns.py / tool_stats.py - integration notes (08.10.2026)

## A. research_columns.py (weight 0, logged only)
Call once per scan, after the daily bars exist (same frames as scanner_geometry):

```python
import research_columns as RC          # 08.10: research tools (TA-Lib, pandas-ta, smc, Elliott x3, Qlib, FinRL) - weight 0
try:
    RC.reset_budget(300)                 # total budget for the block (s); tools past it -> NaN + status 'skipped (scan time budget)'
    _items = []
    for t, _ok, _srp in zip(out['t'], out['mcap_ok'], out['short_rule_pass'].fillna(False)):
        if t.startswith('^') or not bool(_ok): continue
        b = ST.daily_bars(t, 'stock', SCAN_ASOF, _px_dir)
        if b is None or len(b) < 60: continue
        _items.append(((t, 'LONG'), b, SCAN_ASOF, 'stock', 'LONG', t))
        if bool(_srp): _items.append(((t, 'SHORT'), b, SCAN_ASOF, 'stock', 'SHORT', t))
    _rc = RC.compute_many(_items, workers=2)
    _rcdf = pd.DataFrame(_rc); _rcdf[['t', 'rc_direction']] = pd.DataFrame(_rcdf.pop('key').tolist(), index=_rcdf.index)
    _rcdf.to_csv(f'{OUTDIR}/research_columns.csv', index=False)          # every column, both views
    out = out.merge(_rcdf[_rcdf.rc_direction == 'LONG'].drop(columns='rc_direction'), on='t', how='left')
    print(json.dumps(RC.status_summary(_rc), ensure_ascii=False))
except Exception as _e:
    print(f'RESEARCH COLUMNS logged-only block failed: {_e.__class__.__name__}: {_e}')
```
* One ticker: `RC.compute_all(df, cutoff, 'stock', 'LONG', symbol='AAPL')` (tools=['talib','pta'] to limit).
* Columns: `RC.ALL_COLUMNS` (112), tracker subset `RC.TRACKER_KEYS` (30), flag rules for tool_stats `RC.COLUMN_META`.
* Every tool: `exp_<tool>_status` = 'ok' or the error; on error all of its columns are NaN. The scan never crashes.
* TA tools run in a persistent worker of /workspace/ta-repos-eval/venv (system python has no talib/pandas-ta/smc). The worker gets
  no env secrets and no network.

## B. tool_stats.py
```bash
python3 /workspace/tool_stats.py TRACKER.xlsx --extra "/workspace/scan-runs/2026-10-1*/research_columns.csv" --out /workspace/research-models/tool_stats
```
```python
import tool_stats as TS
table, md_he = TS.run('/workspace/scan-tracker-2026-10-12-mom.xlsx', extras=['/workspace/scan-runs/*/research_columns.csv'])
```
Defaults: since 2026-10-12, horizon day 20, ledger /workspace/scan-runs/platform_verdicts_ledger.csv (entry rows, non-trial, >= forward_only_from).

## C. Nightly Qlib / FinRL models (box only, weight 0)
* One pass: `bash /workspace/research_nightly/run_nightly.sh`. For a historical pass: `ASOF="2026-09-24 14:00" bash ...` (ASOF is in UTC).
  Steps: data (yfinance, PIT cut at ASOF) -> qlib_nightly.py -> finrl_nightly.py. Each step writes `/workspace/research-models/<tool>/pred_<D>.csv`, where D = the last visible bar.
* Loop: `bash /workspace/research_nightly/start_nightly.sh` (start | status | stop). It runs at 00:30 IL, with a retry at 04:30. **It does not survive a box reboot.** After a reboot, run the same command again.
* Log: `/workspace/research-models/logs/nightly_<date>.log`
* Scan side: `research_columns` reads `pred_<D>` for the D that is visible at the cutoff. If the file is missing or stale, or if `train_end > D` or `label_end > D`, the columns are NaN and the reason is written to the status column.
* Qlib: Alpha158 + LightGBM with 200 rounds. Label = return over 20 sessions. train_end = D-20 sessions (the labels end at D).
  FinRL: PPO with 2048 steps, trained on bars <= D.

## D. vectorbt parity vs stop_rules.py
* `python3 /workspace/research_nightly/vbt_parity_new.py --tracker <tracker.xlsx>` (default `--since 2026-10-12`, rows with stop_type).
  `--trades <csv>` takes ticker, asset, direction, alert_date.
* Output: `/workspace/research-models/vbt_parity/<stamp>/parity_trades.csv` + `parity_summary.json` (tolerance 0.01pp).
* Historical check (`--all-rows`): 405/405 match, max diff 4e-14pp.

## E. Freqtrade - documentation only: `FREQTRADE_SHADOW.md`
