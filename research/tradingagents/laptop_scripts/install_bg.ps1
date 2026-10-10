$ErrorActionPreference = "Continue"
Set-Location C:\ta-backtest
"start $(Get-Date)" | Out-File install.log
py -3.12 -m venv .venv 2>$null; if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip *>> install.log
.\.venv\Scripts\python.exe -m pip install "git+https://github.com/TauricResearch/TradingAgents.git@1394a3f72aa4393e1a98f51b382434c4b4c2d972" pandas *>> install.log
"PIP_DONE $LASTEXITCODE $(Get-Date)" | Out-File -Append install.log
ollama pull qwen2.5:7b-instruct-q4_K_M *>> pull.log
ollama pull hf.co/bartowski/SUFE-AIFLM-Lab_Fin-R1-GGUF:Q4_K_M *>> pull.log
ollama cp qwen2.5:7b-instruct-q4_K_M qwen25-7b-q4km *>> install.log
ollama cp hf.co/bartowski/SUFE-AIFLM-Lab_Fin-R1-GGUF:Q4_K_M fin-r1-q4km *>> install.log
ollama create qwen25-ta -f Modelfile *>> install.log
ollama create fin-r1-ta -f Modelfile.finr1 *>> install.log
"ALL_DONE $(Get-Date)" | Out-File -Append install.log
