# Reconciliation of the 10.10.2026 commits (Amiram Peretz, 21:52–22:29 IDT)

Base for this branch = the tested code on the box (`/workspace`, 12.10.2026). Nine commits (`ccfd98d`..`280fd08`) were reviewed file by file.

## Not adopted – conflicts with approved rules (needs Ilan's decision)
| Change | Where | Approved rule it conflicts with |
|---|---|---|
| **Grok as an additional analyst** (`grok_analyst_*` columns, `GROK_ROLE_VERSION='dual-role-v1'`, conviction/thesis/key-risk from Grok, ledger role `analyst`) | `scanner/scanner_platforms.py`, `run_daily_report.py`, `unified_report.py`, `docs/GROK_ANALYST.he.md`, `tests/test_grok_analyst.py` | Grok = X sentiment + crypto **only**; Claude = analyst |
| **GPT challenges both analysts** (`rebuttal_of_grok_he`, `gpt_rebuttal_of_grok`) | `scanner_platforms.py` | GPT = devil's advocate against the single (Claude) case |
| **Platform order changed** (Grok sentiment+analyst → Perplexity → Jev → Claude → GPT) | `scanner_platforms.py`, `run_unified_scan.py` docs | Jev is the news pre-filter |
| **Weekly list up to 50 names** (`--candidates 50`) | `run_unified_scan.py`, `run_scheduled.py` | up to 20 names by score |
| **Research overlay 30% in the ranking** (`--research-weight 0.30`, `scanner_research_score`, Jewish-lunar / Gann-Tekunah components) | `run_unified_scan.py`, `modules/scanner_research_score.py` | weight-0 policy until graduation (≥30 OOS, 8–10 entry days, FDR q<0.10, incremental, walk-forward) |
| **Daily run every day** (incl. weekends) | `run_daily_report.py`, systemd timer | weekdays 08:24 |
| Architecture doc describing the above as approved | `ARCHITECTURE.he.md` | — |

## Moved to `proposals/chatgpt-2026-10-10/` (kept, NOT wired into the scan)
Standalone code that does not change roles by itself but depends on the overlay or on Linux/Windows deployment:
`scanner_research_score.py`, `scanner_research_ledger.py`, `scanner_trade_followup.py` (5/10/20-session follow-up after exit – useful candidate),
`scanner_lunar_calendar.py`, `scanner_artifact_archive.py`, `ensure_research_calendar.py`, `publish_research_archive.py`,
`run_scheduled.py` and `ops/systemd/*` (superseded by GitHub Actions), `ops/deploy_linux.py`, `ops/sync_windows_research.py`, their tests and docs.

## Kept as-is (documentation only, no effect on the scan)
`research/jewish-lunar/` (sources, mapping, validation, October calendar fixture), `docs/sources/` (the 8.10 architecture PDF).

## Removed
`.github/workflows/research-tests.yml` (tested the overlay modules that are not wired in), `docs/GROK_ANALYST.he.md`, `tests/test_grok_analyst.py`.

## Edits to existing files
All edits to `scanner/*`, `modules/scanner_*` and `levels_schema.json` were replaced by the current `/workspace` versions.
The only change applied on top of `/workspace`: hard-coded `/workspace` paths now read `SCANNER_ROOT` (default `/workspace`), so the box behaves exactly as before.
