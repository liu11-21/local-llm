# 桌面工作台架構

目前以 Windows x64 為目標；舊 Tkinter 和 GitHub Pages 仍走各自原本的入口。

| 層 | 實作 | 職責 |
|---|---|---|
| 呈現 | `desktop/src` · React / TypeScript / Tailwind | 導覽、對話、工作進度、模型與環境設定 |
| 桌面宿主 | `desktop/src-tauri` · Tauri 2 / Rust | 單一工作台命令、大小限制、資源路徑和工作程序生命週期 |
| Python 工作程序 | `desktop_worker.py` | JSON Lines、排程、本機聊天、SQLite 和既有功能的轉接 |
| 運算供應商 | `runtime_provider.py` | 路由同意規則、HTTPS OpenAI-compatible、停用的 Colab 契約 |
| 現有能力 | `downloads.py` / `load_plan.py` / `engine.py` / `model_team.py` / `media.py` / `comfy_runtime.py` | 下載、資源估算、llama.cpp、團隊及媒體 |

正式宿主把 JSON 寫入工作程序的 stdin，從 stdout 讀取回應，工作台 IPC 不開 HTTP 埠。Windows Job Object 讓宿主持有整棵工作程序樹；關閉行為仍需實際安裝驗收。llama.cpp 使用帶臨時金鑰的本機回環服務。既有 ComfyUI 為回環服務；使用外部啟動的 ComfyUI 時，程式不會停止該服務。只有瀏覽器開發預覽會使用 Vite 同來源代理；正式 bundle 不含代理。

- Model：GGUF 檔、外部模型 ID 或 ComfyUI 工作流程需要的權重。
- Engine：llama.cpp、ComfyUI 或 OpenAI-compatible 服務。
- Runtime：本機 CPU／GPU、使用者配置的 HTTPS 遠端或雲端。外部推理須手動選擇並確認本次傳送；一律不自動改用付費端點。
- Task：下載、聊天、團隊、媒體或引擎生命週期操作。工作台一次執行一筆重任務；團隊內仍由既有資源估算決定是否並行。排程無法保證偵測到所有其他程式的顯存使用。

`%LOCALAPPDATA%\LocalLLM` 沿用模型、作品和 ComfyUI 資料。`desktop.sqlite3` 新增本機對話與任務索引；外部金鑰不進資料庫，關閉即清除。介面偏好存在本機 WebView。模型和媒體仍由檔案系統管理，沒有自動刪除或遷移。要備份請關閉工作台，再複製整個資料目錄。
