param([Parameter(Mandatory)][string]$Installer)

$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or !$env:RUNNER_TEMP) {
    throw 'Run the installer smoke test on a clean GitHub Actions Windows runner.'
}

$installDir = Join-Path $env:LOCALAPPDATA 'Local LLM Workspace'
$shortcuts = foreach ($folder in @('DesktopDirectory', 'Programs')) {
    Join-Path ([Environment]::GetFolderPath($folder)) 'Local LLM Workspace.lnk'
}
$dataDir = Join-Path $env:LOCALAPPDATA 'LocalLLM'
$db = Join-Path $dataDir 'desktop.sqlite3'
$marker = Join-Path $dataDir "ci-preserve-$env:GITHUB_RUN_ID-$env:GITHUB_RUN_ATTEMPT.txt"
if ((Test-Path -LiteralPath $installDir) -or (Test-Path -LiteralPath $db)) {
    throw 'The Windows runner already contains a Local LLM installation or profile.'
}

$installExe = (Resolve-Path -LiteralPath $Installer).Path
$uninstaller = Join-Path $installDir 'uninstall.exe'
$app = $null
$worker = $null
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
Set-Content -LiteralPath $marker -Value 'preserve-user-data'

try {
    $setup = Start-Process -FilePath $installExe -ArgumentList '/S' -WindowStyle Hidden -PassThru -Wait
    if ($setup.ExitCode -ne 0) { throw "Installer exited with code $($setup.ExitCode)." }

    $appExe = Join-Path $installDir 'localllm-desktop.exe'
    $workerExe = Join-Path $installDir 'worker/LocalLLMWorker.exe'
    foreach ($file in @($appExe, $workerExe, $uninstaller)) {
        if (!(Test-Path -LiteralPath $file -PathType Leaf)) { throw "Installed file missing: $file" }
    }
    $shell = New-Object -ComObject WScript.Shell
    foreach ($shortcut in $shortcuts) {
        if (!(Test-Path -LiteralPath $shortcut -PathType Leaf) -or
            $shell.CreateShortcut($shortcut).TargetPath -ne $appExe) {
            throw "Installed shortcut missing or invalid: $shortcut"
        }
    }
    $app = Start-Process -FilePath $appExe -WindowStyle Hidden -PassThru
    $deadline = (Get-Date).AddSeconds(40)
    while ((Get-Date) -lt $deadline) {
        $app.Refresh()
        if ($app.HasExited) { throw "Desktop app exited with code $($app.ExitCode)." }
        $worker = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($app.Id) AND Name = 'LocalLLMWorker.exe'"
        if ($worker -and (Test-Path -LiteralPath $db)) { break }
        Start-Sleep -Milliseconds 500
    }
    if (!$worker -or !(Test-Path -LiteralPath $db)) {
        throw 'The installed WebView did not initialize the Python worker.'
    }

    if (!$app.CloseMainWindow() -or !$app.WaitForExit(8000)) { $app.Kill() }
    $app.WaitForExit(8000) | Out-Null
    $deadline = (Get-Date).AddSeconds(8)
    while ((Get-Date) -lt $deadline -and (Get-Process -Id $worker.ProcessId -ErrorAction SilentlyContinue)) {
        Start-Sleep -Milliseconds 250
    }
    if (Get-Process -Id $worker.ProcessId -ErrorAction SilentlyContinue) {
        throw 'The worker survived desktop app shutdown.'
    }

    $remove = Start-Process -FilePath $uninstaller -ArgumentList '/S' -WindowStyle Hidden -PassThru -Wait
    if ($remove.ExitCode -ne 0) { throw "Uninstaller exited with code $($remove.ExitCode)." }
    if (Test-Path -LiteralPath $appExe) { throw 'The application executable remained after uninstall.' }
    foreach ($shortcut in $shortcuts) {
        if (Test-Path -LiteralPath $shortcut) { throw "Shortcut remained after uninstall: $shortcut" }
    }
    if ((Get-Content -LiteralPath $marker -Raw).Trim() -ne 'preserve-user-data' -or !(Test-Path -LiteralPath $db)) {
        throw 'Uninstall did not preserve the shared application data.'
    }
} finally {
    if ($app -and !$app.HasExited) { $app.Kill() }
    Remove-Item -LiteralPath $marker -ErrorAction SilentlyContinue
}
