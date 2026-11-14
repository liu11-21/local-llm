param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string]$Output)
$ErrorActionPreference = 'Stop'
$inventoryRoot = (Resolve-Path -LiteralPath $Root).Path
$items = @(Get-ChildItem -LiteralPath $inventoryRoot -Recurse -File | Where-Object { $_.Extension -in @('.exe','.dll','.pyd') } | ForEach-Object {
    $relative = [IO.Path]::GetRelativePath($inventoryRoot, $_.FullName).Replace('\','/')
    $kind = switch ($relative) {
        'localllm-desktop.exe' { 'project shell with statically linked upstream crates' }
        'worker/LocalLLMWorker.exe' { 'project worker with upstream PyInstaller bootloader; signing scope REVIEW REQUIRED' }
        'uninstall.exe' { 'generated NSIS uninstaller; signing scope REVIEW REQUIRED' }
        default { 'upstream or generated binary; no project re-signing permitted without review' }
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $_.FullName
    @{
        path=$relative; sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        bytes=$_.Length; file_version=$_.VersionInfo.FileVersion; product_version=$_.VersionInfo.ProductVersion
        authenticode=$signature.Status.ToString(); signer_subject=$signature.SignerCertificate.Subject
        classification=$kind; source_mapping_status='REVIEW REQUIRED: build graph/third-party licenses, not proof of sole authorship'
        source_reference=if ($relative -eq 'localllm-desktop.exe') {'desktop/src-tauri/src/main.rs; Cargo.lock'} elseif ($relative -eq 'worker/LocalLLMWorker.exe') {'desktop_worker.py; build_desktop_worker.py; requirements-windows.lock'} elseif ($relative -eq 'uninstall.exe') {'tauri.conf.json; Tauri NSIS template/toolchain'} else {'notices/DEPENDENCY_LICENSES.json; exact upstream binary attribution pending review'}
    }
})
@{schema=1;source_commit=$env:GITHUB_SHA;version='0.8.0';files=$items;scope='Installed payload including uninstaller; no user data or absolute paths'} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Output -Encoding utf8
Write-Output "Recorded $($items.Count) installed PE files."
