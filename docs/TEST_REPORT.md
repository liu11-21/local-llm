# 桌面工作台測試紀錄

基準：GitHub `main` `8447047496691d34d5c6b24cb846c81d6bcce07f`，正式下載 v0.6.2；新增工作留在 `dev/desktop-workspace`。基準為 6 個 Python 單元測試全數通過。已知問題：舊版未簽署、舊 onefile 需解壓、網頁的原生功能依賴本機橋接，並非 GitHub Pages 可獨立執行。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | 18 個 Python 測試，涵蓋既有更新與團隊回歸、路由同意、HTTPS 驗證、金鑰省略、Colab 提交核准、SSE 串流與取消、SQLite、區段續傳、授權檔完整性及打包 Worker UTF-8 IPC。 |
| PASS | Windows 11 上用 llama.cpp 與 SmolLM2 GGUF：CPU 啟動、聊天回應、對話保存、引擎停止。 |
| PASS | npm/TypeScript/Vite 正式資源建置；Chromium 開發預覽使用真實 Worker，驗證首頁、模型估算、聊天、淺色模式和 650 px 導覽。 |
| PASS | PyInstaller 6.22.3 / Python 3.12.10 onedir 已建置。隔離的全新資料目錄中，由 Worker EXE 下載並驗證官方引擎、以四執行緒下載 105,454,432 位元組的 SmolLM2 GGUF，完成 CPU 聊天、歷史保存、引擎停止、兩成員依序執行及主模型整合。 |
| PASS | v0.6.1 公開 EXE 的 SHA-256、PE、封裝與官方 llama.cpp 位元組比對；固定官方引擎下載與解壓。 |
| PASS | Hugging Face 搜尋、固定版本檔案清單、四執行緒下載 1,185,376 位元組的官方 tinyllamas 測試資產。模擬區段斷線後續傳的位元組比對亦通過。先前連線重設的案例在本輪重跑成功。 |
| PASS | 原生 Tauri NSIS 已在 GitHub Actions 的 Windows Server 2022 x64 runner 建置並驗收。靜默安裝、桌面與開始功能表捷徑、WebView2 啟動 Worker、關閉 Worker、卸載及保留 SQLite 與資料全部通過。[CI 執行紀錄](https://github.com/liu11-21/local-llm/actions/runs/42482360729) |
| PASS | 已下載 CI 產物，ZIP 符合 GitHub Actions 公布的 SHA-256，安裝 EXE 符合 `BUILD.json` 的 SHA-256 `21f64c053624187b1774a717ec2a09634a45c58815a57146f34db21b74eed969`。建置提交為 `ba504ee`。[Windows 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42482360729/artifacts/13618575102) |
| PASS | 含代理人、Colab 與更新功能的 `ca30587` 通過 Windows CI 安裝驗收。已再次下載並核對 ZIP 與安裝 EXE，EXE 的 SHA-256 為 `72a6eb22a2f351fc8824458a8690d4c0e46c9bf7e5ccaccde04fb253402c9446`。[新版開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42488732138/artifacts/13621130867) |
| BLOCKED | 此 Windows 11 電腦的應用程式控制原則擋下未簽章開發安裝程式，原生互動驗收未執行。 |
| NEEDS WINDOWS TEST | 以 Defender、Norton、Avast、AVG 的最新定義掃描乾淨安裝與運行；記錄產品版本、事件與 SHA-256。這次未確認 `Custody` 原因。 |
| PASS | Windows 11 Intel Iris Xe 實際執行 llama.cpp Vulkan 分層，SmolLM2 30 層分配給 GPU，完成代理人工作並保存報告。 |
| PASS | 本機開發預覽驗證代理人計畫、核准、報告和原始資料查閱，以及更新頁與 Colab 表單。 |
| PASS | 工作台實際讀取官方 GitHub 版本清單，已能排除舊桌面通道；新版選擇、下載校驗及中止行為以測試資產驗證。 |
| PASS | 官方 ComfyUI CPU 版可啟動，三種工作流程所需的輸出節點存在。回環 HTTP 測試端點驗證三種圖譜提交、輸出下載與格式檢查，以及工作 ID 專屬的取消。 |
| PASS | Windows 11 的官方 CPU 版 ComfyUI 以 SHA-256 已核對的 Stable Diffusion 1.5 權重，跑完預設 512×512、24 步圖片生成。工作台下載並保存 387,306 位元組的 PNG，尺寸和檔案格式符合預期。 |
| FAIL | 此機的 Intel ComfyUI 套件在 PyTorch XPU 裝置探測發生存取違例，可使用已驗證的 CPU 套件。 |
| NEEDS GPU TEST | 其他 GPU 分層與估算偏差、影片與音樂的真實權重推理、作品預覽與 GPU 資源釋放。 |
| NEEDS CLOUD AUTHORIZATION | Colab Enterprise 已接入既有範本、工作提交與狀態查詢，合約測試通過。OpenAI-compatible SSE 及送出前同意有自動測試。回環 TLS 測試未通過憑證校驗，真正的 Notebook、外部 HTTPS 服務與額度須在授權環境驗收。 |
| NOT RUN | Tauri 更新簽章、正式 Authenticode、簽章後驗證。正式發行未進行。 |

Windows 驗收順序：對照 Actions 的 `BUILD.json` 和 `SHA256SUMS.txt` → 非管理員安裝 → 從捷徑啟動 → 安裝引擎 → 下載小 GGUF → 聊天、中止、重新開啟查歷史 → 切換服務與關閉，檢查子程序 → 解除安裝後重裝，確認模型／作品／對話仍在。GPU 與付費端點需獨立驗收，這些通過前不標記可公開發行。
