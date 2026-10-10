Set-Location $PSScriptRoot
Write-Output "== queue";      Get-Content results\queue.log -Tail 5 -ErrorAction SilentlyContinue
Write-Output "== fin eval";   Get-Content results\fin_eval.log -Tail 4 -ErrorAction SilentlyContinue
Write-Output "== TA (qwen)";  Get-Content results\progress.log -Tail 5 -ErrorAction SilentlyContinue
Write-Output "== TA (fin-r1 deep)"; Get-Content results\progress_finr1deep.log -Tail 3 -ErrorAction SilentlyContinue
Write-Output ("TA results lines: " + (Get-Content results\results.jsonl -ErrorAction SilentlyContinue | Measure-Object -Line).Lines)
Get-ScheduledTask -TaskName "TradingAgentsBacktest" -ErrorAction SilentlyContinue | Select-Object TaskName, State
ollama ps
