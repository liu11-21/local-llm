# 桌面工作台測試紀錄

基準：GitHub `main` `8447047496691d34d5c6b24cb846c81d6bcce07f`，正式下載 v0.6.2；新增工作留在 `dev/desktop-workspace`。基準為 6 個 Python 單元測試全數通過。已知問題：舊版未簽署、舊 onefile 需解壓、網頁的原生功能依賴本機橋接，並非 GitHub Pages 可獨立執行。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | Python 測試：既有更新與團隊回歸；新增路由同意、HTTPS 驗證、金鑰省略、停用 Colab、串流／取消與 SQLite、實際打包 Worker UTF-8 IPC。 |
| PASS | Windows 11 上用 llama.cpp 與 SmolLM2 GGUF：CPU 啟動、聊天回應、對話保存、引擎停止。 |
| PASS | npm/TypeScript/Vite 正式資源建置；Chromium 開發預覽使用真實 Worker，驗證首頁、模型估算、聊天、淺色模式和 650 px 導覽。 |
| PASS | PyInstaller 6.22.3 / Python 3.12.10 onedir 已建置並成功完成實際 EXE IPC 測試。 |
| PASS | v0.6.1 公開 EXE 的 SHA-256、PE、封裝與官方 llama.cpp 位元組比對；固定官方引擎下載與解壓。 |
| NEEDS WINDOWS TEST | 在 Windows 10／11 x64 乾淨環境建置／安裝 Tauri NSIS；驗證 WebView2、捷徑、資料路徑、GPU 子程序關閉及卸載。現機未安裝 MSVC C++ Build Tools。 |
| NEEDS WINDOWS TEST | 以 Defender、Norton、Avast、AVG 的最新定義掃描乾淨安裝與運行；記錄產品版本、事件與 SHA-256。這次未確認 `Custody` 原因。 |
| NEEDS GPU TEST | 實際 GPU 分層與估算偏差，ComfyUI 便攜版、三種作品預覽、取消及 GPU 資源釋放。 |
| NEEDS CLOUD AUTHORIZATION | 自有 HTTPS 遠端／雲端端點的相容性、串流、錯誤與額度；Colab Enterprise 尚未接入。 |
| NOT RUN | Tauri 更新簽章、正式 Authenticode、簽章後驗證。正式發行未進行。 |

Windows 驗收順序：對照 Actions 的 `BUILD.json` 和 `SHA256SUMS.txt` → 非管理員安裝 → 從捷徑啟動 → 安裝引擎 → 下載小 GGUF → 聊天、中止、重新開啟查歷史 → 切換服務與關閉，檢查子程序 → 解除安裝後重裝，確認模型／作品／對話仍在。GPU 與付費端點需獨立驗收，這些通過前不標記可公開發行。
