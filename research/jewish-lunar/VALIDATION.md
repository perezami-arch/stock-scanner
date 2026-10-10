# Local validation — 2026-10-10

Version: `gann-tekuna-overlay-0.2.0`; lifecycle `forward-research-1.0`. User-selected research budget: 30%.
Source base: `b399f53e08bb078aa95108170903b6b07b862a3a`; changes are recorded in this repository's Git history.

## Executed

```text
python -X utf8 -B -W ignore::ResourceWarning -m unittest discover -s tests -p 'test_*.py' -q
Ran 54 tests in 9.834s
OK
```

- Full and partial budget arithmetic; missing components return allocation to baseline.
- Score bounds, invalid configuration, disabled weighting, raw-momentum fallback.
- LONG/SHORT mirrored fixtures and direction-specific geometry.
- A higher-baseline fixture loses rank to a better-confirmed fixture after weighting.
- Earnings blocking remains effective after the rank change.
- Scores remain identical across candidate, levels, CSV, tracker and report snapshots.
- The paper entrypoint is executed against synthetic levels and replacement external services.
- Legacy environment top-N limits cannot truncate the unified candidate universe before scoring.
- Exact Jerusalem sunset boundary, opening-sunset sample, equivalent time zones and missing coverage.
- Future pivot confirmations, stale Fibonacci anchors and provisional Elliott evidence.
- Elliott is excluded from volume-family votes; missing family names are not treated as zero evidence.
- Actual geometry functions, on synthetic OHLCV: 4 cutoffs × 2 directions give identical results
  for the historical prefix and the same prefix followed by extreme future bars.
- Unavailable geometry and overlay errors are explicit and retain available evidence/baseline.
- H3 asset age affects clock relation; no Hebrew-day or waxing/waning directional prior.
- Median RVOL excludes the current bar and resists a prior-volume outlier.
- Immutable snapshots, duplicate ingestion, mature-outcome immutability, mode separation.
- Future/incomplete bars excluded; entry/session gaps remain pending, never zero.
- Replayed/trial runs and snapshots captured after the proposed entry open are excluded.
- Daily updates do not multiply the number of research trials.
- Daily news is fetched on days without a new bar and when the price source fails.
- Post-exit checks count 5/10/20 sessions AFTER the exit, mirror LONG/SHORT and are idempotent.
- Missing news coverage, future news, duplicate articles and adjusted exit discrepancies.
- Monthly astronomy generator replayed October 2026 from saved public sources: all 31 days,
  sunset boundaries, lunar phases and illumination match the prior pilot exactly. See
  `calendar-generator-validation.json`. No network or market data required for that replay.

The legacy levels/report writers emit ResourceWarnings about existing unclosed-file patterns;
the final test command suppresses that warning category only. It does not suppress test failures.
The platform candidate-filter test substitutes a network client that raises if called; the
local Python runtime lacks `requests`. No network request is part of these tests.

## Not established

No complete live-bot run, historical profitability backtest, unseen return validation, new
TradingView/market data fetch, account trade or deployment to the internal Linux bot was performed.
Missing live scanner dependencies and historical run artifacts remain as described in INTEGRATION.he.md.
The tests establish implementation behavior within their stated fixtures; they do not validate
the 30% allocation, source-inspired market hypotheses, trade-count calibration, or investment returns.

The included calendar covers October 2026; the scheduled wrapper extends current/next-month
coverage through public APIs and pinned JPL data after deployment. Missing coverage is
reported and reduces effective research allocation. The prior SPY study did not validate an edge
and must not be presented as evidence that this overlay improves results.
