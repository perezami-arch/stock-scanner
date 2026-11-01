# Crypto archive (01.11.2026)

**Decision (Ilan, 01.11.2026):** crypto is fully neutralized in this scanner, past and future: out of the scan universe,
the positions tracker, the paper/verdict ledgers, the simulated account and the reports. A **separate crypto scanner with
different parameters** will be built later. Nothing was deleted.

## What is here
Frozen snapshot of the crypto rows from the `state` branch as of 01.11.2026 (`scan-runs/*.csv`, `asset == crypto`):

| file | rows | tickers |
|---|---|---|
| positions_registry_crypto_2026-11-01.csv | 3 | UNI, LINK (13.10), AAVE (20.10) |
| platform_verdicts_ledger_crypto_2026-11-01.csv | 60 | AAVE, AVAX, BTC, DOT, LINK, UNI |
| platform_verdicts_ledger_trial_crypto_2026-11-01.csv | 5 | UNI |
| paper_trades_ledger_crypto_2026-11-01.csv | 36 | AAVE, AVAX, BCH, BTC, DOT, LINK, LTC, UNI |

## Runtime archive
On the first daily run after merge, `crypto_policy.archive_crypto_rows()` MOVES the crypto rows of the live ledgers to
`scan-runs/archive/crypto/<same file name>` (append + de-dup, archive written before the source is rewritten). That folder
is in the `ops/state.py` allowlist, so it is persisted on the `state` branch.

Code kept (not deleted): `modules/scanner_crypto.py`, `tracker/crypto_engine.py`. Re-enable only by explicit decision: `SCANNER_ENABLE_CRYPTO=1`.

The no-crypto recompute of the simulated account: `research/no-crypto-recompute/`.
