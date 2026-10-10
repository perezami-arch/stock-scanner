Set-Location $PSScriptRoot
Write-Output "== queue";      Get-Content results\queue.log -Tail 5 -ErrorAction SilentlyContinue
Write-Output "== fin eval";   Get-Content results\fin_eval.log -Tail 4 -ErrorAction SilentlyContinue
Write-Output "== TA (qwen)";  Get-Content results\progress.log -Tail 5 -ErrorAction SilentlyContinue
Write-Output "== TA calibrated"; Get-Content results\progress_calib.log -Tail 5 -ErrorAction SilentlyContinue
Write-Output "== TA (fin-r1 deep)"; Get-Content results\progress_finr1deep.log -Tail 3 -ErrorAction SilentlyContinue
Write-Output ("TA results lines: " + (Get-Content results\results.jsonl -ErrorAction SilentlyContinue | Measure-Object -Line).Lines)
Get-ScheduledTask -TaskName "TA-Backtest-Night-*" -ErrorAction SilentlyContinue | ForEach-Object { $i = $_ | Get-ScheduledTaskInfo; "{0}  {1}  next={2}  last={3} rc={4}" -f $_.TaskName, $_.State, $i.NextRunTime, $i.LastRunTime, $i.LastTaskResult }
Write-Output "== aihf"; Get-ChildItem results\aihf_*_qwen25-7b-q4km.jsonl -ErrorAction SilentlyContinue | ForEach-Object { "$($_.Name): " + (Get-Content $_.FullName | Measure-Object -Line).Lines }
ollama ps
