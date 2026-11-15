# Local LLM 0.9.0 Web Workspace — 交付追蹤

基準 0.8.0 `90af62b`，工作分支 dev/web-workspace；不改 main、Stable v0.6.2、Desktop 分支，不建立 Release／Tag。
停止推進 SignPath／憑證；保留 Tauri 原始碼與已核准第一方 MIT，第三方／素材範圍不變。

已實作：共用 WorkspaceApplication 與 IPC／HTTP Transport、同源驗證／CSRF／Host／Origin、SSE／取消、
原排程與核心功能、官方 Runtime 簽章與內容 pin、GGUF 匯入、作品下載／Range、Benchmark 匯出、
服務管理與閒置／子程序保護、官方 Python 啟動器、純 Python 固定依賴、ZIP 更新／回滾、PWA。

首階段提交 `d65421b`；[真實原型](evidence/v090/prototype-real.json) 使用官方簽章 Python／llama.exe，
Qwen3-0.6B 真實繁體 HTTP／SSE、取消、SQLite、React 與關閉清理通過。
基本聊天沒有 cryptography import，沒有執行自製 EXE；Uvicorn／h11／click／colorama 精確 SHA 見鎖定檔。

完整測試、乾淨 Windows ZIP、下載位置、最終 SHA 與來源 Commit 待本輪 CI 完成後填入，未完成前不宣稱通過。
Chrome／Edge、Thinking ON／OFF、Agent／Team／Benchmark、升級及更新／回滾均須依個別證據判定。
RTX／CUDA／NPU／多 GPU／雙實體 Remote／SAC 完整鏈 NEEDS HARDWARE，付費雲端 NEEDS AUTH。
PWA 手動安裝與裝置政策仍需維護者實機確認；不能以一般 CI 取代 SAC。

[架構](WEB_ARCHITECTURE.md) · [首次安裝](WEB_INSTALLATION.md) · [安全](WEB_SECURITY.md) · [相容性](WEB_COMPATIBILITY.md)
