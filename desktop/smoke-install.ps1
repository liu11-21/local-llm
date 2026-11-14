param([Parameter(Mandatory)][string]$Installer, [Parameter(Mandatory)][string]$BaselineInstaller)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or !$env:RUNNER_TEMP) { throw 'Use a clean GitHub Actions Windows runner.' }
$installDir = Join-Path $env:LOCALAPPDATA 'Local LLM Workspace'
$dataDir = Join-Path $env:LOCALAPPDATA 'LocalLLM'
$legacyDb = Join-Path $dataDir 'desktop.sqlite3'
$db = Join-Path $dataDir 'workspace.sqlite3'
$appExe = Join-Path $installDir 'localllm-desktop.exe'
$workerExe = Join-Path $installDir 'worker/LocalLLMWorker.exe'
$uninstaller = Join-Path $installDir 'uninstall.exe'
$shortcuts = foreach ($folder in @('DesktopDirectory','Programs')) { Join-Path ([Environment]::GetFolderPath($folder)) 'Local LLM Workspace.lnk' }
$marker = Join-Path $dataDir "ci-preserve-$env:GITHUB_RUN_ID.txt"
if ((Test-Path -LiteralPath $installDir) -or (Test-Path -LiteralPath $db) -or (Test-Path -LiteralPath $legacyDb)) { throw 'Runner already has a Workspace profile.' }
$script:app = $null
$script:worker = $null
function Install-Workspace([string]$Path) {
    $setup = Start-Process -FilePath (Resolve-Path -LiteralPath $Path).Path -ArgumentList '/S' -WindowStyle Hidden -PassThru -Wait
    if ($setup.ExitCode -ne 0) { throw "Installer exited $($setup.ExitCode)" }
}
function Start-AndClose([string]$ExpectedDatabase, [string]$ExpectedVersion='0.8.0') {
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $script:app = Start-Process -FilePath $appExe -WindowStyle Hidden -PassThru
    $script:worker = $null
    $ready = $false
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {
        $script:app.Refresh()
        if ($script:app.HasExited) { throw 'Installed app exited before initialization.' }
        $script:worker = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($script:app.Id) AND Name = 'LocalLLMWorker.exe'"
        if ($script:worker -and (Test-Path -LiteralPath $ExpectedDatabase)) {
            python upgrade_probe.py ready --data $dataDir --database $ExpectedDatabase --expected-version $ExpectedVersion
            if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        }
        Start-Sleep -Milliseconds 250
    }
    if (!$script:worker -or !$ready) { throw 'WebView did not finish initializing its worker/database.' }
    $timer.Stop()
    if (!$script:app.CloseMainWindow() -or !$script:app.WaitForExit(8000)) { $script:app.Kill() }
    $script:app.WaitForExit(8000) | Out-Null
    $deadline = (Get-Date).AddSeconds(8)
    while ((Get-Date) -lt $deadline -and (Get-Process -Id $script:worker.ProcessId -ErrorAction SilentlyContinue)) { Start-Sleep -Milliseconds 250 }
    if (Get-Process -Id $script:worker.ProcessId -ErrorAction SilentlyContinue) { throw 'Worker survived app shutdown.' }
    return $timer.Elapsed.TotalMilliseconds
}
try {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    Set-Content -LiteralPath $marker -Value 'preserve-user-data'
    Install-Workspace $BaselineInstaller
    $baselineStartup = Start-AndClose $db '0.7.0'
    python upgrade_probe.py initialize --data $dataDir --worker $workerExe --output build/windows-review/baseline-worker.json
    if ($LASTEXITCODE) { throw 'Baseline installed worker identity/initialization failed.' }
    python upgrade_probe.py seed --data $dataDir --record build/upgrade-seed.json
    if ($LASTEXITCODE) { throw 'Baseline data seeding failed.' }
    $legacyHash = if (Test-Path -LiteralPath $legacyDb) { (Get-FileHash -LiteralPath $legacyDb).Hash } else { $null }
    # Same Workspace identifier and installation directory: do not manually uninstall 0.7.0.
    Install-Workspace $Installer
    foreach ($file in @($appExe,$workerExe,$uninstaller)) { if (!(Test-Path -LiteralPath $file)) { throw "Missing installed file: $file" } }
    $shell = New-Object -ComObject WScript.Shell
    foreach ($shortcut in $shortcuts) { if (!(Test-Path -LiteralPath $shortcut) -or $shell.CreateShortcut($shortcut).TargetPath -ne $appExe) { throw "Invalid shortcut: $shortcut" } }
    $startup = @(1..3 | ForEach-Object { Start-AndClose $db })
    if ($legacyHash -and (Get-FileHash -LiteralPath $legacyDb).Hash -ne $legacyHash) { throw 'Upgrade modified original legacy database.' }
    python upgrade_probe.py verify --data $dataDir --record build/upgrade-seed.json --output build/windows-review/upgrade-verification.json
    if ($LASTEXITCODE) { throw 'Upgrade data verification failed.' }
    python check_workspace_version.py --build build/windows-review/BUILD.json --worker $workerExe
    if ($LASTEXITCODE) { throw 'Installed worker identity mismatch.' }
    python workspace_perf.py --worker $workerExe --repeats 3 --output build/windows-review/performance-packaged-worker.json
    if ($LASTEXITCODE) { throw 'Packaged worker baseline failed.' }
    ./desktop/pe-inventory.ps1 -Root $installDir -Output build/windows-review/installed-pe-inventory.json
    foreach ($notice in @('STATUS.json','workspace.spdx.json','DEPENDENCY_LICENSES.json','PRIVACY.md','LICENSE')) {
        if (!(Test-Path -LiteralPath (Join-Path $installDir "notices/$notice"))) { throw "Installed notice missing: $notice" }
    }
    @{status='PASS';baseline_source='e2ba3476c6a58574db3c488e9aa4296f4cd4dc4c';baseline_version='0.7.0';version='0.8.0';
      baseline_startup_ms=$baselineStartup;process_cold_startup_ms=$startup;scope='WebView launch to live worker and database; OS cache not flushed';
      desktop_shortcut=$true;start_menu_shortcut=$true;worker_cleanup=$true;in_place_upgrade=$true} | ConvertTo-Json | Set-Content build/windows-review/installer-smoke.json
    $remove = Start-Process -FilePath $uninstaller -ArgumentList '/S' -WindowStyle Hidden -PassThru -Wait
    if ($remove.ExitCode -ne 0 -or (Test-Path -LiteralPath $appExe)) { throw 'Uninstall failed.' }
    foreach ($shortcut in $shortcuts) { if (Test-Path -LiteralPath $shortcut) { throw 'Uninstall left shortcut.' } }
    if ((Get-Content -LiteralPath $marker -Raw).Trim() -ne 'preserve-user-data' -or !(Test-Path -LiteralPath $db) -or ($legacyHash -and !(Test-Path -LiteralPath $legacyDb))) { throw 'Uninstall removed user data.' }
    python upgrade_probe.py verify --data $dataDir --record build/upgrade-seed.json --output build/windows-review/upgrade-after-uninstall.json
    if ($LASTEXITCODE) { throw 'Uninstall changed data.' }
    Write-Output 'PASS Workspace 0.7.0 -> 0.8.0 install/upgrade/shortcuts/worker/uninstall/data preservation'
} finally {
    if ($script:app -and !$script:app.HasExited) { $script:app.Kill() }
    Remove-Item -LiteralPath $marker -ErrorAction SilentlyContinue
}
