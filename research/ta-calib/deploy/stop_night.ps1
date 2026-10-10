# Stops the nightly backtest (run at 08:00 by task "TA-Backtest-Night-Stop", or manually). Safe when nothing runs.
# Kills the queue/runner python processes (parents first, so no runner can record a 'failed' line for a child we
# kill; an interrupted setup simply has no line and is redone first next night), then unloads ONLY this project's
# Ollama models so the GPU is free. Other models (e.g. minicpm5) are never touched. Results/tasks are kept.
$ErrorActionPreference = 'Continue'
$root = $PSScriptRoot
$logf = Join-Path $root 'results\queue.log'
function Log($m) { Add-Content -Path $logf -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss ') + $m) -Encoding UTF8; Write-Output $m }
$pat = 'run_queue\.py|run_all_setups\.py|run_calibrated\.py|fin_eval\.py|run_aihf\.py'
$procs = @(Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" -ErrorAction SilentlyContinue |
           Where-Object { $_.CommandLine -and $_.CommandLine -match $pat })
$rank = { param($c) if ($c -match 'run_queue\.py') { 0 } elseif ($c -match '--one') { 2 } else { 1 } }
$killed = 0
foreach ($p in ($procs | Sort-Object { & $rank $_.CommandLine })) {
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue; if ($?) { $killed++ }
}
$ollama = (Get-Command ollama -ErrorAction SilentlyContinue).Source
if (-not $ollama) { $ollama = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe' }
$ours = @('qwen25-ta', 'fin-r1-ta', 'qwen25-7b-q4km', 'fin-r1-q4km')
$unloaded = @()
if (Test-Path $ollama) {
    $loaded = @(& $ollama ps 2>$null | Select-Object -Skip 1 | ForEach-Object { ($_ -split '\s+')[0] } | Where-Object { $_ })
    foreach ($m in $loaded) {
        if ($ours -contains ($m -replace ':latest$', '')) { & $ollama stop $m 2>&1 | Out-Null; $unloaded += $m }
    }
}
Log ("night stop: killed $killed process(es); unloaded: " + $(if ($unloaded) { $unloaded -join ', ' } else { 'none' }))