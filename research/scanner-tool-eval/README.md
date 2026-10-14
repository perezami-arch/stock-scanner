# scanner-tool-eval

A harness for checking whether a forecasting or ranking tool filters the scanner's setups usefully, using
**point-in-time** data only. Written for the Kronos / Chronos-2 / TimesFM evaluation (Oct 2026), and reusable for any new tool.

## Layout
| file | role |
|---|---|
| `pit.py` | Point-in-time data layer. `load_setups()` reads the canonical `/workspace/tracker/setups-point-in-time-2026-10-08.csv` (read-only) and sets `asof_ts`. `history(ticker, asset, asof_ts, lookback)` returns daily candles that were complete at `asof_ts`. `realized_fixed()` returns outcomes after the cutoff. |
| `fetch_prices.py` | Downloads prices for every ticker in the setups file: daily bars for US, hourly bars for crypto (needed to cut at the exact minute). Saves to `$PIT_PX_DIR` (default `/workspace/kronos-eval/tracker_eval/px`). |
| `prepare.py` | Builds `setups_prepared.csv` with direction-adjusted realized returns: the tracker's day-5, day-20 and total where present, otherwise computed from prices and flagged `realized_source=computed`. |
| `tools/base.py` | `Tool` interface plus baselines: random walk, momentum 12-1, low-vol 60d. |
| `tools/ts_models.py` | Kronos (mini/small/base), Chronos-2 and TimesFM-2.5 wrappers. They reuse `/workspace/kronos-eval` (venv, HF cache, KV-cached Kronos). |
| `run_tools.py` | Scores every setup with the tools you name. Writes `forecasts/<key>.csv` and `.meta.json` (runtime, RAM). |
| `report.py` | Writes the markdown report: Spearman, per-date RankIC, keep vs reject with date-clustered bootstrap CIs, breakdowns by source, asset class, time-source quality and direction, the prebreakout focus, incremental value over the factors, and the excluded (<$1.5B) set. |

## Cut rules (point in time)
* US: the history ends at the `cutoff_bar_date` close (16:00 ET). If the alert came during or before that day's session, this is the previous session's close. Date-only alerts also use the previous session's close.
* Crypto: 24h candles rebuilt from hourly bars, ending at `cutoff_minute_utc`. Date-only alerts cut at 00:00 UTC of the alert day.
* Perplexity task-list times (`time_source=ui_log`) are logged 5-70 min after the real run, so the cutoff is also capped at logged time minus 70 min.
* `dup_not_counted=True` rows are skipped. Rows with no alert date (no cutoff) are skipped.

## Run
```bash
source /workspace/kronos-eval/.venv/bin/activate
cd /workspace/scanner-tool-eval
python fetch_prices.py            # once / when new setups arrive
python prepare.py
python run_tools.py rw mom121 lowvol chronos2 timesfm kronos-small
python report.py tracker_eval.md
```

## Adding a new tool
1. Subclass `tools.base.Tool`. Set `name`, and set `rank_only=True` if your number is a ranking rather than an expected return (its sign then carries no meaning).
2. Implement `score(self, ticker, asset, asof_ts, horizon_days) -> float`. This is the expected return over `horizon_days` bars (trading days for US, 24h days for crypto), and higher means more bullish. Return NaN if you can't score.
   **Only** read data through `pit.history(ticker, asset, asof_ts, ...)`, or any other source cut at `asof_ts`. That is the whole no-lookahead guarantee.
   For speed, override `score_batch(reqs)` (see `_PathTool` in `tools/ts_models.py`).
3. Register it: add `"mykey": MyTool` to `REGISTRY` in `tools/base.py`, or a branch in `run_tools.make()`.
4. Run `python run_tools.py mykey && python report.py`. It appears in every table, and `report.py` flips the sign for SHORT setups automatically.

Example:
```python
class ShortTermReversal(Tool):
    name = "Reversal 5d"; rank_only = True
    def score(self, ticker, asset, asof_ts, horizon_days):
        c = pit.history(ticker, asset, asof_ts, lookback=10)["close"]
        return -(c.iloc[-1] / c.iloc[-6] - 1) if len(c) >= 6 else float("nan")
```

## Caveats built into the report
Setups on the same date share market moves, so iid p-values are optimistic. Use the date-clustered bootstrap CIs and the per-date RankIC t-stats. Many tools × targets × groups are tested, so expect some p<0.05 by chance.
