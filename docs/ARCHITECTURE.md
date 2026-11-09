# 桌面工作台架構

目前以 Windows x64 為目標；舊 Tkinter 和 GitHub Pages 仍走各自原本的入口。

| 層 | 實作 | 職責 |
|---|---|---|
| 呈現 | `desktop/src` · React / TypeScript / Tailwind | 導覽、對話、工作進度、模型與環境設定 |
| 桌面宿主 | `desktop/src-tauri` · Tauri 2 / Rust | 單一工作台命令、大小限制、資源路徑和工作程序生命週期 |
| Python 工作程序 | `desktop_worker.py` | JSON Lines、本機聊天、SQLite 和既有功能的轉接 |
| 任務排程 | `task_manager.py` | 任務生命週期、獨立佇列、去重、取消及下載重試 |
| 能力登錄 | `registries.py`、`media.py` | 提供 Model、Engine、Runtime 及 Workflow 描述，供頁面選擇與表單渲染 |
| 運算供應商 | `runtime_provider.py`、`colab_runtime.py` | 路由同意規則、HTTPS OpenAI-compatible、Colab Enterprise 的既有範本和 Notebook 作業 |
| 現有能力 | `downloads.py` / `load_plan.py` / `engine.py` / `model_team.py` / `media.py` / `comfy_runtime.py` | 下載、資源估算、llama.cpp、團隊及媒體 |

正式宿主把 JSON 寫入工作程序的 stdin，從 stdout 讀取回應，工作台 IPC 不開 HTTP 埠。Windows Job Object 讓宿主持有整棵工作程序樹；關閉行為仍需實際安裝驗收。llama.cpp 使用帶臨時金鑰的本機回環服務。既有 ComfyUI 為回環服務；使用外部啟動的 ComfyUI 時，程式不會停止該服務。只有瀏覽器開發預覽會使用 Vite 同來源代理；正式 bundle 不含代理。

- Model：GGUF 檔、外部模型 ID 或 ComfyUI 工作流程需要的權重。
- Engine：llama.cpp、ComfyUI 或 OpenAI-compatible 服務。
- Runtime：本機 CPU／GPU、使用者配置的 HTTPS 遠端或雲端。外部推理須手動選擇並確認本次傳送；一律不自動改用付費端點。
- Task：本機推理共用一個槽位，兩個背景下載和兩個遠端文字請求有獨立槽位。同一對話與下載目的檔案各自去重。團隊執行時佔用本機槽位，團隊內部沿用 RAM／VRAM 預算。已啟動的本機 ComfyUI 與文字引擎仍依現有互斥規則切換。
- 任務從排隊轉為執行，再進入完成、失敗、取消或中斷。取消執行中工作時保留槽位，等工作結束才交給下一筆。關閉後重開會把上次的進行中紀錄標為中斷。工作參數和串流回覆保留在本次程序，不寫入任務歷史。下載重試在本次程序建立新工作，付費或推理工作由使用者回原頁重新提交。
- Workflow：由 Python 宣告預設值、範圍、必要權重、引擎和輸出格式。工作程序驗證參數後組成 ComfyUI 圖譜，作品資料庫記錄實際參數及種子。四個內建選項共用同一個創作表單。

`%LOCALAPPDATA%\LocalLLM` 沿用模型、作品和 ComfyUI 資料。`desktop.sqlite3` 新增本機對話與任務索引；外部金鑰不進資料庫，關閉即清除。介面偏好存在本機 WebView。模型和媒體仍由檔案系統管理，沒有自動刪除或遷移。要備份請關閉工作台，再複製整個資料目錄。

本輪在 SQLite 新增 `task_metadata`、`creations` 和對話訊息索引，保留舊表和欄位。要回滾開發分支，可用 `git revert` 產生回滾提交，或建置基準 `fa81a2c` 後用獨立資料目錄驗收。回滾前保留整個使用者資料夾，舊版仍可讀取原本的對話和作品檔。
