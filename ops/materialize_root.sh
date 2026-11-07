#!/usr/bin/env bash
# Build the box's flat /workspace layout at $SCANNER_ROOT from this repo, so the code runs unchanged.
# Usage: ops/materialize_root.sh <repo_dir> <scanner_root>
set -euo pipefail
REPO=$(cd "$1" && pwd); ROOT="$2"; mkdir -p "$ROOT"
cp "$REPO"/scanner/*.py "$REPO"/scanner/levels_schema.json "$ROOT"/
cp "$REPO"/modules/*.py "$ROOT"/
cp "$REPO"/ops/status_mismatch.py "$ROOT"/status_mismatch.py
mkdir -p "$ROOT/trading-frameworks-eval/iaf"; cp "$REPO"/research/tradingagents/trading-frameworks-eval/iaf/* "$ROOT/trading-frameworks-eval/iaf/"; cp "$REPO/modules/stop_rules.py" "$ROOT/trading-frameworks-eval/iaf/"
mkdir -p "$ROOT/tracker"; cp -r "$REPO"/tracker/. "$ROOT/tracker/"
for d in liq-sweep fib-spiral research_nightly scanner-tool-eval; do mkdir -p "$ROOT/$d"; cp -r "$REPO/research/$d/." "$ROOT/$d/"; done
mkdir -p "$ROOT/scan-runs" "$ROOT/prompts" "$ROOT/x-cache" "$ROOT/news-cache" "$ROOT/scanner-momentum-cache" "$ROOT/short-data"
echo "materialized $(find "$ROOT" -maxdepth 1 -name '*.py' | wc -l) top-level modules at $ROOT"
