# Starts the queue fully detached via Task Scheduler (survives the remote shell closing / ~14-min command cut),
# and re-launches it every 15 minutes as a watchdog (lock file prevents double runs; finished work is skipped,
# so a relaunch after sleep/reboot just resumes).
Set-Location $PSScriptRoot
$py   = Join-Path $PSScriptRoot ".venv\Scripts\pythonw.exe"
$argLine = "`"$(Join-Path $PSScriptRoot 'run_queue.py')`""
$action  = New-ScheduledTaskAction -Execute $py -Argument $argLine -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Days 7)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Days 3) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "TradingAgentsBacktest" -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName "TradingAgentsBacktest"
Write-Output "launched; progress: results\queue.log, results\fin_eval.log, results\progress.log"
