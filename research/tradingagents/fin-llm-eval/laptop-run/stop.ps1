Unregister-ScheduledTask -TaskName "TradingAgentsBacktest" -Confirm:$false -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" | Where-Object { $_.CommandLine -match "run_all_setups.py|run_queue.py|fin_eval.py" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Write-Output "stopped (results are kept; launch.ps1 resumes)"
