# Manual stop: kills the running queue now and unloads the project's models (results kept; it resumes at the next
# 23:00 window). To stop the nightly schedule entirely as well:  .\stop.ps1 -Disable   (re-enable: .\stop.ps1 -Enable)
param([switch]$Disable, [switch]$Enable)
& (Join-Path $PSScriptRoot 'stop_night.ps1')
if ($Disable) { Disable-ScheduledTask -TaskName 'TA-Backtest-Night-Start' | Out-Null; Write-Output 'nightly start task disabled' }
if ($Enable)  { Enable-ScheduledTask  -TaskName 'TA-Backtest-Night-Start' | Out-Null; Write-Output 'nightly start task enabled' }