# Web Workspace 安裝與操作

0.9.0 Development，以 Python 本機服務＋瀏覽器操作，不依賴自製 EXE／Windows Installer。

本輪修復：[Session 恢復](SESSION_RECOVERY_REPAIR.md)、[Python 自動選取](PYTHON_LAUNCHER_REPAIR.md)、[桌機驗收](V090_DESKTOP_RETEST.md)。
服務重啟／Session 逾期時，再執行 Start 取得目前服務的登入連結；既有分頁可安全重新初始化，不需清除 Cookie。
六個管理 CMD 都會依序驗證 py／PATH／Registry／常見安裝的 Python 3.12 x64，再用絕對路徑執行。

1. 從 [python.org](https://www.python.org/downloads/windows/) 安裝 Python 3.12 x64，3.12.10 或較新 3.12，含 Launcher。
2. 解壓完整 Web ZIP，雙擊 `Start-Web-Workspace.cmd`。只有原始碼 ZIP 時，開發者需先在 desktop 執行 `npm ci`、`npm run build:web`。
3. 「運算環境」偵測／選擇官方 Hugging Face 簽章 llama.exe；「模型與應用」可匯入 GGUF 或使用既有 HF 搜尋／多執行緒下載。

已有 llama.exe 不需重新下載或修改 PATH。按「偵測已安裝版本」會檢查服務 PATH、目前使用者／系統 PATH 與 WindowsApps，
清單顯示簽章、版本、驗證失敗原因。看到「已驗證 · 尚未選取」後按「選取此 Runtime」，再重新載入確認保存。
若掃不到，可按「選擇既有 llama.exe 檔案」，或展開進階區輸入完整路徑；兩者仍需相同完整驗證。
無 GGUF 表示模型待準備，不會隱藏 Runtime，也不等於 GPU 推理失敗。診斷欄位與目標主機驗收見 [偵測修復](RUNTIME_DETECTION_REPAIR.md)。

啟動器檢查官方 Python／x64，建立獨立環境，依 SHA-256／wheel RECORD 安裝四個純 Python 套件。
發行 ZIP 包含原始 wheels，可離線完成基本環境；模型與選用 Runtime 下載仍需網路。
以原本的官方 Python `-I -S -B` 執行，隔離全域 site-packages；不執行 venv 的 Python EXE、pip/distlib entry-point EXE 或自製 Worker。
虛擬環境僅作儲存隔離，啟動時檢查檔案完整性。Python 標準庫仍含原生 DLL／PYD，不能保證通過所有裝置政策。

官方 Runtime 手動安裝依 [上游指引](https://github.com/ggml-org/llama-install.sh)。本程式不自動執行其遠端腳本。
要用應用內固定版本下載，執行 `Install-Web-Optional.cmd runtime`，重新啟動後再按下載並明確切換。
私人遠端 Host 需要 `Install-Web-Optional.cmd tls`；它與 ComfyUI／OpenVINO 都是選用環境，原生元件須另驗證。
雲端仍需使用者自己的帳號、憑證及當次傳送核准，不自動啟用付費服務。

預設資料在 `%LOCALAPPDATA%\LocalLLM`；支援 `--data` 指向自己的隔離資料夾。
沿用 SQLite、模型、聊天與作品，0.8.0 → 0.9.0 先備份，不移動或覆蓋 GGUF。
Desktop 與 Web 使用同一 `.workspace.lock`，不能同時開啟同一資料目錄。
本版未更改 schema 14，minimum_reader 保持 0.8.0，保留程式回滾相容性。

關閉瀏覽器後服務仍存在，啟動視窗與每頁的「服務管理」都清楚提示；停止按鈕／`Stop-Web-Workspace.cmd` 會取消任務並清理子程序。
90 秒無客戶端且沒有活躍工作會釋放閒置 llama／ComfyUI；30 分鐘無客戶端會停止服務及工作。
重複執行 Start 會開啟原服務；正常退出刪除控制記錄，異常記錄不能用來任意終止 PID。

更新：停止後執行 `Update-Web-Workspace.cmd "候選 ZIP" --sha256 交付雜湊`。
檢查整包 SHA、解壓路徑／大小／內容及內部 manifest，安裝到另一個版本目錄；下次 Start 才使用新版本。
`Rollback-Web-Workspace.cmd` 切回先前程式，使用者資料保留；未來資料格式若不相容，需保留新資料並恢復校驗備份。
沒有正式 Release／Tag，因此目前更新候選由 GitHub Actions 取得，不從不明來源自動下載程式碼。

`Diagnose-Web-Workspace.cmd` 保存 Python 簽章、建置、服務及唯讀 3077 診斷。分享前檢查路徑／事件資訊。
Start／Stop 都可能受腳本政策限制；可使用官方 Python 完整路徑執行 `-I -S -B app\web_launcher.py start`。
此替代啟動方式不是繞過安全政策；若政策仍阻擋，保持政策並記錄實際被擋檔案。
