# One-time setup (PowerShell, in this folder). Requires Python 3.11+ and Ollama (already installed). Nothing else is installed system-wide.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
py -3.12 -m venv .venv 2>$null; if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip
# TradingAgents pinned to the commit tested on the box (v0.6.0, 2026-10-03)
.\.venv\Scripts\python.exe -m pip install "git+https://github.com/TauricResearch/TradingAgents.git@1394a3f72aa4393e1a98f51b382434c4b4c2d972" pandas

# Smaller KV cache so a 7B Q4_K_M model + 16k context stays inside 8 GB VRAM (takes effect after Ollama restarts)
[Environment]::SetEnvironmentVariable("OLLAMA_FLASH_ATTENTION", "1", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_KV_CACHE_TYPE", "q8_0", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_MAX_LOADED_MODELS", "1", "User")
Write-Output "Restart Ollama now (tray icon -> Quit, then start it again) so the settings above apply. Press Enter when done."; Read-Host | Out-Null

# Both models at the SAME quantization (Q4_K_M, ~4.7 GB each); only one is loaded at a time.
ollama pull qwen2.5:7b-instruct-q4_K_M
ollama pull hf.co/bartowski/SUFE-AIFLM-Lab_Fin-R1-GGUF:Q4_K_M
ollama cp qwen2.5:7b-instruct-q4_K_M qwen25-7b-q4km
ollama cp hf.co/bartowski/SUFE-AIFLM-Lab_Fin-R1-GGUF:Q4_K_M fin-r1-q4km
ollama create qwen25-ta -f Modelfile          # same weights, 16k context for TradingAgents
ollama create fin-r1-ta -f Modelfile.finr1

# SEC EDGAR wants a contact in the User-Agent (no key/account). Optional but polite:
# [Environment]::SetEnvironmentVariable("SEC_EDGAR_USER_AGENT", "Ilan Perets your@email", "User")

# Smoke tests (foreground, a few minutes): 1 eval item per model, 1 setup
$env:FIN_EVAL_NUM_PREDICT = "3000"
.\.venv\Scripts\python.exe run_all_setups.py --model qwen25-ta --limit 1 --timeout-min 30
ollama ps     # PROCESSOR column should read 100% GPU; if it shows CPU/GPU split, lower num_ctx in Modelfile to 8192
