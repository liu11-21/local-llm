# 桌面工作台測試紀錄

## Batch 4A–4C

基準 `a2d0bdb`，版本 `0.6.2`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | Windows 本機 83 項 Python 測試中 79 項通過，4 項 TLS 網路回環案例由 Windows CI 執行。新案例涵蓋引擎和模型缺少、離線、外部政策、未知費用、ComfyUI 預檢、私人位址、受保護私鑰、憑證重用及更新撤銷。 |
| PASS | Chromium 在 1280×900、1024×768、800×600、650×720 驗證深淺模式、長名稱、錯誤、鍵盤焦點、reduced motion、側欄收合、即時資源、Host 自動 TLS、同意對話框及既有 Agent／Team／作品庫。確認 Esc 未送出，核准只提交一次並保存一則回答。 [實際畫面](UI_DESIGN.md#batch-4a4c-工作台與任務準備) |
| PASS | 自動產生的憑證與 DPAPI 保護密碼通過本機 TLS 記憶體握手。瀏覽器同時驗證 Host 建立邀請及顯示指紋。 |
| NEEDS REMOTE HOST | 兩台實體電腦之間的自動 TLS、私人網路與斷線行為仍待驗收。 |
| NEEDS GPU | 實體遠端 GPU 推理與即時 GPU／VRAM 用量的驗收。 |
| NOT RUN | 4D 遠端媒體與持久任務、4E 完整新手引導及進一步跨 Runtime 整合。 |

## 第三階段 Batch 3D–3E

程式基準 `678d04b`，版本 `0.6.2`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | Windows 本機 Python 共 77 項測試，73 項通過，4 項 TLS 回環案例移至乾淨的 CI 環境。本機 DPAPI、記憶體 TLS 正確與錯誤 IP 身分、SSE 重連不重複輸出、推薦政策及權重驗證失效均通過。 |
| PASS | Windows CI 的受控 Host／Client 測試涵蓋 TLS、無授權拒絕、協定版本、配對、撤銷、配對持久化、同一任務重送、任務所有權和取消。推理使用受控的模型回應。 [第一輪 Host／Client CI](https://github.com/liu11-21/local-llm/actions/runs/42771568190) |
| PASS | Chromium 深淺模式，1280×900、1024×768、800×600、650×720。測試啟用與停止 Host、長主機名稱、建立邀請、無效邀請、能力比較，以及既有 Agent、Team 與創作。 [實際 UI](UI_DESIGN.md#batch-3d3e-私人遠端運算) |
| PASS | `1704f45` 通過 Windows Server 2022 x64 CI，包括受控 HTTPS 配對後從桌面聊天提交、儲存回答來源、封裝與安裝／卸載。 [Windows CI](https://github.com/liu11-21/local-llm/actions/runs/42817141781) |
| PASS | 已下載 ZIP，核對 GitHub 的 ZIP SHA-256、`BUILD.json` 提交和安裝 EXE。EXE SHA-256 為 `17454342b4f122c662132efe04be130395f1b437fe6f073b2fc0bed411b0db6a`。 [Windows 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42817141781/artifacts/13764692723) |
| NEEDS REMOTE HOST | 兩台實體 Windows 電腦之間的 LAN／VPN、防火牆、TLS、長時間斷線和重連驗收。 |
| NEEDS GPU | 遠端實體 GPU 上的 llama.cpp 載入、生成效能及 CPU 回退需要另行驗收。 |
| NEEDS CLOUD AUTH | 推薦只讀取能力，Colab Enterprise 及雲端推理的付費路徑沿用既有契約，這次沒有提交測試推理。 |

本機 Norton Web/Mail Shield 替換了回環服務的測試 TLS 憑證，預期的身分驗證因此拒絕連線。CI 使用未經替換的測試憑證執行實際 HTTPS 協定測試。

## 第三階段 Batch 3A–3C

基準為 `d39afbf`，開發安裝包版本為 `0.6.2`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | 64 項 Python 測試。涵蓋 Team 交付與審查狀態、必要依賴、工具參數及核准、權限、逾時後的執行槽、ComfyUI 權重清單、SHA-256、磁碟不足、取消、續傳、同名保護、節點預檢、舊作品、作品篩選、安全原檔路徑及媒體中繼資料。 |
| PASS | TypeScript／Vite 建置及 Chromium UI 測試。涵蓋四種尺寸及深淺模式、Team 部分交付、創作安裝摘要、作品庫搜尋、排序、類型與模型篩選、參數與種子回填。Team 回應由可控 SSE 測試端點提供。 [實際介面截圖](UI_DESIGN.md#batch-3-創作與作品庫) |
| PASS | 真實 Windows CPU。重新計算既有 SD 1.5 權重的 SHA-256，檢查 ComfyUI 節點，從桌面 Worker RPC 提交並透過 TaskManager 完成 256×256 PNG。SQLite 作品庫可查到尺寸、種子及真實 ComfyUI 任務 ID。 |
| PASS | 真實 Hugging Face 安裝下載。Wan 2.1 VAE 以四個執行緒下載，實際大小 253,815,318 bytes，通過固定 revision 的 SHA-256。 [Wan 2.1 權重](https://huggingface.co/Comfy-Org/Wan-2.1/tree/123acf1cc74bccbb9bfff8ac1ee72edc08c2341d/split_files/vae) |
| PASS | `eb5cba2` 通過 Windows Server 2022 x64 CI，含 Worker 封裝、Chromium、Tauri NSIS、靜默安裝、桌面及開始功能表捷徑、WebView2 啟動、關閉和卸載保留資料。 [Windows CI](https://github.com/liu11-21/local-llm/actions/runs/42765375251) |
| PASS | 已下載開發安裝包，核對 GitHub 的 ZIP SHA-256、`BUILD.json` 提交與安裝 EXE SHA-256。EXE 校驗值為 `182b61cd0e7f9b78d5fb5be306c55922d27045611bd79dd6d68e909f4cafba6c`。 [Windows 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42765375251/artifacts/13739622530) |
| NEEDS GPU | Wan 2.1 實際影片生成及 ACE-Step 實際音樂生成仍待支援的 GPU 環境驗收。 |
| NOT RUN | Wan 2.1 其餘兩個權重及 ACE-Step 完整下載、新版簽章、正式 Release、付費請求。3D 遠端 Host／Client 及 3E 能力契約尚未實作。 |

## 第三階段 Batch 2

開發基準為 `c83dfca`，工作台版本為 `0.6.2`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | 51 項本機 Python 測試。新增契約、重複工具、輸入與輸出 Schema、未授權拒絕、逾時和取消。計畫測試確認多份計畫互不覆蓋、版本與契約變更使舊計畫失效、過期及重開後不重播。 |
| PASS | Agent 測試確認等待核准時其他本機工作可執行，且只有原請求 ID 可核准。拒絕與取消不讀取工具。偽造的 PowerShell 請求、額外路徑參數和不合法 JSON 均被拒絕。達上限會保留先前事實。 |
| PASS | Team 測試驗證三種模式各自的上下文和依賴輸入、循環與缺少依賴拒絕、審查失敗保留初稿、共用運算槽、取消、設定讀寫及外部授權拒絕。 |
| PASS | TypeScript／Vite 建置。Chromium 保留 1280×900、1024×768、800×600、650×720 的深淺版面測試，另經真實 Worker 及可控的本機 HTTP／SSE 端點驗證 Agent 計畫、逐次核准、兩種工具協定、時間軸、錯誤和取消，以及 Team 角色、依賴、審查、部分失敗和取消。 [實際介面截圖](UI_DESIGN.md#batch-2-工作流程) |
| PASS | `3417b39` 通過 Windows Server 2022 x64 CI。Python、Worker 封裝、Chromium 版面及工作流程、Rust／Tauri 建置、桌面和開始功能表捷徑、WebView2 啟動與關閉 Worker、卸載保留使用者資料均通過。 [Windows CI](https://github.com/liu11-21/local-llm/actions/runs/42616269570) |
| PASS | 已下載並核對開發安裝包 ZIP SHA-256、`BUILD.json` 提交與 EXE SHA-256。EXE 校驗值為 `013833d63e2ed4c9100055d0605f4b42570a0a08da8389f67b14dee4a41fca14`。 [Windows 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42616269570/artifacts/13673231196) |
| NEEDS WINDOWS TEST | 這台 Windows 的真實 llama.cpp 啟動在推理前失敗，Worker 收到程序退出代碼 `3236495362`。原生工具能力、結構化輸出的實際品質及不同本機模型的協作效果需另行驗收。 |
| NEEDS CLOUD AUTH | 外部 Team 端點的授權拒絕已有回歸測試。實際遠端 SSE、服務額度及資料傳送需在授權環境驗收。 |
| NOT RUN | 付費請求、雲端 Agent、任意第三方工具、正式簽章和正式 Release。 |

`npm run test:layout` 在 Chromium 使用隔離資料目錄和可控的本機協定端點。它測試正式的 Worker 任務、權限與儲存路徑。模型回答是固定測試回應。

## 第三階段 Batch 1

基準為 `da4ee33`，工作台版本維持 `0.6.2`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | 33 項本機 Python 測試。使用可控制的 HTTP 回應，在 Windows 子程序中實際強制退出，驗證重開後保留已完成區段且不重抓、取消不發布、上游校驗不符、同名鎖、清理範圍、來源紀錄隨檔案變更而失效，以及引擎健康狀態和媒體預檢。 |
| PASS | 實際同時下載公開的 `stories260K.gguf` 和 `SmolLM2-135M-Instruct-Q4_K_M.gguf`，兩者皆核對固定版本 LFS SHA-256。SmolLM2 模型卡顯示 Apache-2.0，stories260K 的模型卡授權未取得。 |
| PASS | 真實 Hugging Face 傳輸寫入 16,777,216 位元組後，強制終止隔離的下載程序。重開工作台後辨識中斷下載，從 16 MiB 接續並驗證完整 SmolLM2 檔案。 |
| PASS | TypeScript、Vite build 與 `npm run test:layout`。Chromium 測試 1280×900、1024×768、800×600 和 650×720 的深色、淺色。測試資料包含長模型名、長錯誤、模擬的團隊執行中狀態。幾何檢查確認標題維持水平、選擇器在容器內、頁面無水平溢出並有鍵盤焦點。 |
| PASS | Chromium 以實際本機 Worker 和 ComfyUI CPU 版驗證影片權重缺失、圖片工作執行中、Stable Diffusion 1.5 生成 384×384 PNG，以及在創作原頁載入圖片。代理人頁以先前實機保存的報告驗證事實區與模型回答區。 [實際畫面](UI_DESIGN.md#第三階段精修) |
| PASS | 由桌面 Worker 管理的 ComfyUI CPU 版實測啟動、再次探測 API、程序異常退出、手動重啟與停止。 |
| PASS | `6da7d2a` 通過 Windows Server 2022 x64 CI。Python、Worker 封裝、Chromium 版面回歸、Rust／Tauri 建置、靜默安裝、桌面與開始功能表捷徑、WebView2 啟動 Worker、關閉及卸載保留資料均通過。 [Windows CI](https://github.com/liu11-21/local-llm/actions/runs/42556268695) |
| PASS | 已下載並核對開發安裝包的 ZIP SHA-256、`BUILD.json` 提交及 EXE SHA-256。EXE 校驗值為 `a180311af672f85b027d512753a10923cf29dc9c5bce7e5671672748b5de4eb2`。 [Windows x64 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42556268695/artifacts/13648135425) |
| FAIL | 本機 Windows 仍以 WinError 4551 封鎖 llama.cpp。新版正確顯示 `ENGINE_POLICY_BLOCKED`。真實聊天與新代理人推理需在允許引擎的環境驗證。 |
| FAIL | 首輪 Windows CI 將系統暫存路徑的別名視為不安全，四項下載測試因此失敗。修正將上層路徑正規化，並保留下載目錄本身的連結檢查；本機回歸通過。 [首輪 CI](https://github.com/liu11-21/local-llm/actions/runs/42555585807) |
| FAIL | 第二輪 Windows CI 通過 Python 測試及打包 Worker IPC，Chromium 回歸等待 Vite 就緒時逾時。測試改由 Vite API 啟動並等待服務，取代讀取 CLI 終端輸出。 [第二輪 CI](https://github.com/liu11-21/local-llm/actions/runs/42555964797) |
| NEEDS WINDOWS | 一般 Windows 10／11 的原生互動、下載中關閉原生安裝版，以及各防毒套件的行為。 |
| NEEDS GPU | 影片、音樂、不同 GPU 後端及資源預估的實機驗收。 |
| NEEDS CLOUD AUTH | 遠端桌機、雲端服務及 Colab Enterprise 的實際請求、作業和費用。 |
| NOT RUN | 新 Agent 工具協議、Team 協作模式及後續批次；正式簽章、誤判申訴與正式 Release。 |

要重跑本機回歸，在倉庫根目錄執行 `python -m unittest -v`。在 `desktop` 執行 `npm ci`、`npm run test:layout` 和 `npm run build`。版面測試會啟動隔離的本機工作台，使用已安裝的 Chrome；可用 `LOCALLLM_BROWSER` 指定瀏覽器執行檔。

## 第二階段基礎

基準為開發分支 `fa81a2c`。維持工作台版本 `0.6.2`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | 23 項 Python 測試，含兩筆下載與聊天重疊、第二筆本機推理排隊、目的地去重、排隊取消、失敗重試、歷史寫入暫時失敗、重開復原、聊天重新生成及工作流程參數驗證。並行回歸測試用同步事件驗證排程。 |
| PASS | TypeScript 型別檢查及 Vite production build。Chromium 開發預覽連接實際 Worker，以先前本機生成的對話與代理人報告驗證複製、改名、刪除確認、代理人計畫預覽、深淺主題、鍵盤焦點及 650 px 導覽。 |
| PASS | 抽測聊天內容、輸入區標示、模型選擇器、側欄選取項和主要按鈕的靜態文字對比。深色最低 7.71:1，淺色最低 6.24:1。 |
| PASS | 官方 ComfyUI CPU 版實際執行 `sd15-preview`，以種子 42、4 步生成 384×384 PNG。工作台保存 189,967 位元組的作品，作品索引可讀回流程 ID、種子與步數。 |
| PASS | 新版桌面任務 RPC 實際同時下載 Hugging Face 的 `stories260K.gguf`（1,185,376 bytes）和 `SmolLM2-135M-Instruct-Q4_K_M.gguf`（105,454,432 bytes）。每筆使用四個區段執行緒，完成後確認 GGUF 標頭和檔案長度。 |
| PASS | `c01f33c` 於 GitHub Actions 的 Windows Server 2022 x64 完成 Worker 打包、Rust／Tauri 建置、安裝程式與校驗檔產出。靜默安裝、桌面和開始功能表捷徑、WebView2 啟動 Worker、關閉程序，以及卸載保留使用者資料均通過。[CI 紀錄](https://github.com/liu11-21/local-llm/actions/runs/42552053727) · [開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42552053727/artifacts/13645398237) |
| PASS | 從 GitHub 下載的 ZIP 符合 Actions 的 SHA-256。內含 `Local LLM Workspace_0.6.2_x64-setup.exe`，已核對 `BUILD.json` 的提交與 EXE SHA-256 `df4998796d31e14ddc16ac95569d42040f47ee9cf5f272421ebf45fdb3d4b8ff`。 |
| FAIL | 並行測試中另兩個候選檔案發生來源連線重設。工作台顯示失敗且未發布成 GGUF。另一次測試在仍有下載時退出程序，留下隱藏的暫存檔，強制退出後的暫存清理待補。 |
| FAIL | 本機 Windows 的應用程式控制原則封鎖 llama.cpp。新版送出與重新生成的實機推理需在允許執行的 Windows 環境重跑，重新生成的資料庫行為已通過回歸測試。 |
| NEEDS GPU | CUDA／其他 Vulkan 裝置、實際影片與音樂生成及不同硬體的資源估算。 |
| NEEDS CLOUD AUTH | 付費端點與實際 Colab Notebook 作業、額度和結果匯入。 |
| NEEDS WINDOWS TEST | 一般 Windows 10／11 的原生互動和多款防毒軟體。 |
| NOT RUN | 正式簽章、誤判申訴和正式 Release。 |

## 前輪測試

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
