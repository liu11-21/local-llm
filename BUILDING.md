# Build from public source

Windows 10/11 x64、WebView2、MSVC C++ Build Tools／Windows SDK；使用 Windows CI 指定的 Python 3.12.10 x64、Node 24.22.1、Rust 1.99.1。安裝包不附模型；實際 RAM／VRAM 需求依模型而變。鎖定版本有助重建，但不保證位元組完全一致。

從公開 dev/desktop-workspace 的完整 Commit 建置，勿用來源 ZIP 代替安裝程式。PowerShell：

```powershell
git clone --branch dev/desktop-workspace https://github.com/liu11-21/local-llm.git
Set-Location local-llm
git rev-parse HEAD
python -m pip install --only-binary=:all: -r desktop/requirements-windows.lock
python -m pip install --only-binary=:all: -r desktop/requirements-audit.lock
python check_workspace_version.py
python -m unittest -v
python build_desktop_worker.py
npm --prefix desktop ci --no-audit --no-fund
npm --prefix desktop run test:layout
cargo metadata --locked --format-version 1 --manifest-path desktop/src-tauri/Cargo.toml | Set-Content build/cargo-license-metadata.json -Encoding utf8
python license_audit.py collect --output build/release-notices --network --crate-archives --cargo-metadata build/cargo-license-metadata.json
python release_evidence.py prepare-notices --directory build/release-notices
npm --prefix desktop run tauri -- build --target x86_64-pc-windows-msvc -- --locked
```

每個命令均須確認結束碼；失敗不得繼續發行。授權工具僅讀取依賴 metadata、已安裝來源及校驗過的 crate 封裝，保留未知狀態，不下載模型。cargo metadata 必須使用同一鎖檔與工具鏈。輸出在 desktop/src-tauri/target/x86_64-pc-windows-msvc/release/bundle/nsis。

只有 UI 預覽可執行 npm --prefix desktop run dev；不用封裝 Worker 或 Rust。完整封裝必須先準備 build/release-notices，確保原始聲明隨安裝包分發。

Worker 建置會在尚無 notices 目錄時放入 tracked 審查快照，供來源開發啟動使用；這不是當次 Cargo build 的完整對應證明。發行 CI 必須依上述 metadata／collect 流程重新產生精確版本 Notice，不能用快照取代。

CI 額外從 4354605004c7d8db1f88bca8e3cc1ef38b135b55 建置 Workspace 0.6.2，驗證原地升級、資料保留、捷徑及解除安裝。不要在有私人資料的電腦執行 CI 安裝測試。CI 不關閉 Windows 安全功能；本機 TLS 攔截造成的測試限制不得套用到乾淨 Runner。
