# 桌面工作台測試紀錄

基準：GitHub `main` `8447047496691d34d5c6b24cb846c81d6bcce07f`，正式下載 v0.6.2；新增工作留在 `dev/desktop-workspace`。基準為 6 個 Python 單元測試全數通過。已知問題：舊版未簽署、舊 onefile 需解壓、網頁的原生功能依賴本機橋接，並非 GitHub Pages 可獨立執行。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | 15 個 Python 測試，涵蓋既有更新與團隊回歸、路由同意、HTTPS 驗證、金鑰省略、停用 Colab、SSE 串流與取消、SQLite、區段續傳、授權檔完整性及打包 Worker UTF-8 IPC。 |
| PASS | Windows 11 上用 llama.cpp 與 SmolLM2 GGUF：CPU 啟動、聊天回應、對話保存、引擎停止。 |
| PASS | npm/TypeScript/Vite 正式資源建置；Chromium 開發預覽使用真實 Worker，驗證首頁、模型估算、聊天、淺色模式和 650 px 導覽。 |
| PASS | PyInstaller 6.22.3 / Python 3.12.10 onedir 已建置。隔離的全新資料目錄中，由 Worker EXE 下載並驗證官方引擎、以四執行緒下載 105,454,432 位元組的 SmolLM2 GGUF，完成 CPU 聊天、歷史保存、引擎停止、兩成員依序執行及主模型整合。 |
| PASS | v0.6.1 公開 EXE 的 SHA-256、PE、封裝與官方 llama.cpp 位元組比對；固定官方引擎下載與解壓。 |
| PASS | Hugging Face 搜尋、固定版本檔案清單、四執行緒下載 1,185,376 位元組的官方 tinyllamas 測試資產。模擬區段斷線後續傳的位元組比對亦通過。先前連線重設的案例在本輪重跑成功。 |
| PASS | 原生 Tauri NSIS 已在 GitHub Actions 的 Windows Server 2022 x64 runner 建置並驗收。靜默安裝、桌面與開始功能表捷徑、WebView2 啟動 Worker、關閉 Worker、卸載及保留 SQLite 與資料全部通過。[CI 執行紀錄](https://github.com/liu11-21/local-llm/actions/runs/42482360729) |
| PASS | 已下載 CI 產物，ZIP 符合 GitHub Actions 公布的 SHA-256，安裝 EXE 符合 `BUILD.json` 的 SHA-256 `21f64c053624187b1774a717ec2a09634a45c58815a57146f34db21b74eed969`。建置提交為 `ba504ee`。[Windows 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42482360729/artifacts/13618575102) |
| NEEDS WINDOWS TEST | 在 Windows 10／11 使用互動安裝介面與桌面捷徑，手動驗收原生介面的完整聊天與媒體流程。 |
| NEEDS WINDOWS TEST | 以 Defender、Norton、Avast、AVG 的最新定義掃描乾淨安裝與運行；記錄產品版本、事件與 SHA-256。這次未確認 `Custody` 原因。 |
| NEEDS GPU TEST | 實際 GPU 分層與估算偏差，ComfyUI 便攜版、三種作品預覽、取消及 GPU 資源釋放。 |
| NEEDS CLOUD AUTHORIZATION | 自有 HTTPS 遠端／雲端端點的相容性、串流、錯誤與額度；Colab Enterprise 尚未接入。 |
| NOT RUN | Tauri 更新簽章、正式 Authenticode、簽章後驗證。正式發行未進行。 |

Windows 驗收順序：對照 Actions 的 `BUILD.json` 和 `SHA256SUMS.txt` → 非管理員安裝 → 從捷徑啟動 → 安裝引擎 → 下載小 GGUF → 聊天、中止、重新開啟查歷史 → 切換服務與關閉，檢查子程序 → 解除安裝後重裝，確認模型／作品／對話仍在。GPU 與付費端點需獨立驗收，這些通過前不標記可公開發行。
