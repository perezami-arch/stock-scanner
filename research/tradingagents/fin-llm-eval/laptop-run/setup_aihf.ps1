# OPTIONAL step 4: ai-hedge-fund persona filter (stocks only). Separate venv so its pinned langchain versions
# can't clash with TradingAgents. Nothing system-wide. Run from this folder in PowerShell, AFTER setup.ps1.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
py -3.12 -m venv .venv-aihf 2>$null; if (-not (Test-Path .venv-aihf)) { python -m venv .venv-aihf }
.\.venv-aihf\Scripts\python.exe -m pip install --upgrade pip
# ai-hedge-fund v2 pinned to the commit reviewed on the box (78b779c, 2026-10-02) + price/EDGAR helpers
.\.venv-aihf\Scripts\python.exe -m pip install "git+https://github.com/virattt/ai-hedge-fund.git@78b779c1389e2d1452dc29606d2c4126d859b964" yfinance requests pandas
# Smoke test: 2 stock setups with the 7B model already pulled by setup.ps1
.\.venv-aihf\Scripts\python.exe aihf\run_aihf.py druckenmiller --model qwen25-7b-q4km --limit 2
Write-Output "OK. Full run (~442 stock setups, est. 30-60 min on the RTX 4070):"
Write-Output "  .\.venv-aihf\Scripts\python.exe aihf\run_aihf.py druckenmiller --model qwen25-7b-q4km"
Write-Output "  .\.venv-aihf\Scripts\python.exe aihf\run_aihf.py buffett --model qwen25-7b-q4km"
