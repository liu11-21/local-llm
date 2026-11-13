# Local LLM Workspace 0.7.0 · Development

React／Tauri Windows AI 工作台，整合文字聊天、Agent、Team、圖片／影片／音樂創作、模型下載及本地／遠端運算。

第一方程式碼、測試、建置腳本及技術文件已於 2026-11-13 經維護者明確批准採用 **[MIT](LICENSE)**，署名「Copyright (c) 2026 劉仲軒」。維護者主導需求與產品架構，主要透過 Codex／AI 輔助開發；不宣稱所有 AI 輸出均有著作權或絕對無第三方權利。Logo／品牌素材／UI 截圖及合成媒體檔暫時獨立處理；第三方元件、Runtime、模型權重維持原條款，詳 **[授權範圍](LICENSE_SCOPE.md)**。[核准紀錄](docs/MIT_FINAL_APPROVAL_CHECKLIST.md) · [來源紀錄](docs/MAINTAINER_PROVENANCE.md) · [開源準備](docs/OPEN_SOURCE_READINESS.md) · [第三方授權](THIRD_PARTY_LICENSES.md) · [隱私](PRIVACY.md) · [建置](BUILDING.md) · [Code signing policy](CODE_SIGNING_POLICY.md)。SignPath **未申請、未核准**，安裝包仍 **unsigned**；MIT 不等於整包發行或簽章資格已獲准。

Windows 10/11 x64，需 WebView2；原始碼建置需 Python／Node／Rust／MSVC，固定版本見 BUILDING。聊天、Agent 工具核准與 Team 可依選擇在本機、雲端或配對 Host 執行；選用雲端／遠端會把必要內容送至該目的地。更新檢查、模型／Runtime 安裝及缺少 WebView2 時的安裝另有網路請求。模型所需 RAM／VRAM 依模型與工作流程而變。

| 通道 | 版本／分支 | 取得方式 |
|---|---|---|
| Stable | v0.6.2 · main | [既有正式發行](https://github.com/liu11-21/local-llm/releases/tag/v0.6.2)，保留舊桌面版 |
| Development | 0.7.0 · dev/desktop-workspace | [Windows Actions](https://github.com/liu11-21/local-llm/actions/workflows/desktop-windows.yml?query=branch%3Adev%2Fdesktop-workspace)，開啟成功建置的 artifact |

開發安裝包解壓後執行 `Local LLM Workspace_0.7.0_x64-setup.exe`，會建立桌面與開始功能表捷徑。Actions 下載可能需要登入 GitHub，產物保留 14 天。這是未簽章開發版，目前沒有正式 0.7.0 Release。請選擇本分支最新成功的建置，並核對隨附的 BUILD.json／SHA256SUMS.txt。

工作台支援：

- 串流聊天、Markdown／程式碼、歷史，Agent 工具核准及多模型 Team。
- Hugging Face 搜尋、模型校驗、可續傳的多執行緒下載、受管理引擎。
- ComfyUI 固定工作流程；圖片、Wan 2.1 影片及 ACE-Step v1 音樂，完整權重需另行確認下載。
- 配對遠端 Host、TLS、能力檢查、媒體續傳／SHA-256、作品庫與播放器。
- CPU／GPU／NPU 偵測、可選 OpenVINO、Benchmark、證據型推薦、動態 RAM 與安全排程。
- 精簡深淺色 UI、情境首頁、新手引導、作品 Grid／List 與分頁。

偵測到硬體不代表該模型已能推理。Wan／ACE-Step 真實 GPU 生成、雙實體機與 NPU 仍須實機驗收；不會自動啟用付費雲端或傳送提示詞。[目前功能與驗收](docs/TEST_REPORT.md) · [介面截圖](docs/UI_DESIGN.md) · [架構](docs/ARCHITECTURE.md)。

工作台只檢查 `workspace-vX.Y.Z` 的正式發行，與舊桌面版 `vX.Y.Z` 分流；沒有可校驗的較新 Workspace Release 時不提供更新，不自動安裝。設定頁顯示 App／Worker 版本、Development、建置 SHA 與目標；版本混搭會拒絕啟動工作。

Workspace 與舊桌面版為不同產品，不能把舊版 Setup 當成 Workspace 升級包。兩者歷史上使用 `%LOCALAPPDATA%\LocalLLM` 的模型／作品目錄；請先關閉兩套程式並備份資料。Workspace 0.6.2 → 0.7.0 是同產品的原地升級路徑，原資料庫保留，0.7.0 使用獨立 workspace.sqlite3；升級前自動建立校驗快照。[升級與恢復](docs/UPGRADE_070.md) · [0.7.0 完整交付](docs/V070_DELIVERY.md)。

開發：Python 3.12、Node 24、Rust／MSVC／WebView2；執行 `python check_workspace_version.py`、`python -m unittest -v`、`python build_desktop_worker.py`，再於 desktop 執行 `npm ci`、`npm run tauri -- dev`。只預覽 UI 可用 `npm run dev`；完整安裝包由 Windows CI 產生。main 的既有發行與說明不變。

---

## 舊版 Stable v0.6.2 使用說明

以下為舊桌面版說明，與上方 Workspace 0.7.0 Development 分開。


**[下載 Windows x64 安裝程式](https://github.com/liu11-21/local-llm/releases/download/v0.6.2/LocalLLM-v0.6.2-Windows-x64-Setup.exe)** · [免安裝版](https://github.com/liu11-21/local-llm/releases/download/v0.6.2/LocalLLM-v0.6.2-Windows-x64.exe) · [最新發行頁](https://github.com/liu11-21/local-llm/releases/latest)

雙擊 `LocalLLM-v0.6.2-Windows-x64-Setup.exe`，依安裝精靈完成安裝。預設建立桌面與開始功能表捷徑，可在 Windows「已安裝的應用程式」解除安裝。安裝在目前使用者帳號下，模型和作品存放於獨立資料夾。發行版內含 Python 與 llama.cpp Vulkan／CPU 引擎。GitHub 的「Source code (zip)」提供開發用原始碼。

v0.6.2 的安裝包尚未做 Windows 程式碼簽署，Windows 或防毒軟體可能依裝置政策攔截。

Local LLM 是 Windows x64 本機聊天與媒體創作工作台。

## 網頁工作台

[GitHub Pages 網頁版](https://liu11-21.github.io/local-llm/) 可使用 WebGPU 聊天、瀏覽器模型團隊，以及搜尋和直接下載 Hugging Face GGUF。第一次載入瀏覽器模型需要下載權重。

本機 GGUF 對話、多執行緒下載、硬體推薦、GGUF／雲端團隊和 ComfyUI 創作，使用本機工作台。下載或複製本專案，安裝 Python 3.12，雙擊 `Launch-Web.cmd` 或執行 `python web_bridge.py`。瀏覽器會開啟 `http://127.0.0.1:8765/`。服務只在本機監聽，沿用桌面版的模型和作品資料夾。GGUF 功能會使用桌面安裝版內附的引擎，也可依下方說明在專案的 `engine-vulkan` 準備 llama.cpp。關閉啟動工作台的命令視窗即可停止服務。

## 程式更新

Tauri 工作台可在「設定」查看更新，程式啟動時也會自動檢查 `workspace-vX.Y.Z` 發行。下載後會驗證 SHA-256，再由使用者開啟安裝程式。GitHub Actions 的開發產物可由各次建置頁手動下載。

Windows EXE 開啟時會在背景檢查 GitHub 的最新正式版，右上角的「程式更新」也能手動檢查。安裝版會下載新版 Setup，免安裝版會下載新版單檔 EXE。待 SHA-256 核對完成後，開啟下載資料夾，關閉目前版本，再雙擊下載的 EXE。各版本的模型、作品和 ComfyUI 資料共用 `%LOCALAPPDATA%\LocalLLM`。

要從免安裝版改用安裝版，請直接下載 Setup 一次。v0.6.0 或更早的版本也請先手動下載新版。

1. 到「模型清單」選擇依本機硬體排序的推薦模型，或搜尋 Hugging Face 公開單檔 GGUF。選好檔案後按「前往下載」。已有 GGUF 可直接按「選擇本機 GGUF」。
2. 在「模型下載」按「開始下載」。預設 4 個執行緒，可調整為 1–16。支援 HTTP Range 的來源會平行下載，下載完成才將模型放入資料夾。
3. 在左欄選擇模型，查看「啟動資源預估」，再按「啟動模型」進行串流對話。

聊天引擎啟動前會重新讀取 GGUF 檔案大小、層數與引擎回報的可用 GPU 記憶體。程式按預留的 GPU 記憶體分配卸載層數，其餘層由 CPU 使用 RAM。引擎支援時會映射原本的 GGUF 檔案，由 Windows 按需將檔案頁載入 RAM。磁碟映射顯示的是原模型檔大小。共用 GPU 記憶體會計入 RAM 預估。實際佔用會隨模型架構、上下文和 Windows 快取而變化。GPU 啟動失敗時會嘗試 CPU。

EXE 下載的模型與生成的作品會分別儲存在 `%LOCALAPPDATA%\LocalLLM\models` 和 `%LOCALAPPDATA%\LocalLLM\outputs`。從原始碼執行時使用專案內的 `models` 和 `outputs`。舊版的本機 GGUF 可在新版用檔案選擇器匯入。

## 模型團隊

1. 開啟「模型團隊」，加入 2–6 個本機 GGUF 或支援 Chat Completions 的雲端模型。加入雲端模型時，填入服務的 HTTPS API 網址（例如 `https://api.openai.com/v1` 或 `https://openrouter.ai/api/v1`）、模型 ID 和 API 金鑰。金鑰只保留在本次開啟的程式內。
2. 選一個成員當「主模型」，輸入一份提示詞，按「執行團隊」。所有成員獨立收到同一份提示詞；主模型在草稿階段完成後再合併。RAM 或顯存不足以並行時，本機模型會依序載入和卸載；也可勾選「本機一律排隊」。若單一模型也放不下，該成員會標示失敗。雲端請求可與本機推理同時執行。
3. 最終回答會顯示在程式並存成 `answer.md`。「開啟結果資料夾」可查看原始提示詞、各份草稿 `member-XX.md` 和狀態 `run.json`。有成員失敗時仍可合併成功的草稿；若合併失敗，已完成的草稿會保留。若本機主模型的上下文不足以容納全部草稿，合併時會使用節錄，完整草稿仍會保存。

EXE 將結果存到 `%LOCALAPPDATA%\LocalLLM\outputs\teams`，原始碼版本使用 `outputs/teams`。只選本機模型時，提示詞與草稿留在本機；選用雲端成員會把提示詞送給該服務，雲端主模型還會收到所有成功的草稿。請求可能按服務商的方式計費。

## 圖片、影片與音樂

1. 開啟「創作」，選擇符合硬體的 [ComfyUI Windows 官方便攜版](https://docs.comfy.org/installation/comfyui_portable_windows) 後按「下載並啟動」。不確定可先選 CPU 試跑，生成速度會較慢。
2. 首次下載約 1.4–1.9 GiB。安裝時會核對 SHA-256 並解壓，建議在安裝磁碟預留 10 GiB，另加模型的空間。之後可以直接按「啟動 ComfyUI」。
3. 按「模型資料夾」，將下表對應檔案放到指定子目錄。模型權重需另外下載。選擇創作類型、輸入描述並按「開始生成」。音樂可另填歌詞，完成後按「開啟作品」。

內建啟動器使用官方 ComfyUI v0.44.0，服務只監聽 `127.0.0.1`，預設連接埠為 `8188`。「開啟網頁」可進入原生 ComfyUI 介面。按「停止 ComfyUI」或正常關閉 Local LLM 會停止它啟動的服務。如果已有 ComfyUI 在執行，可直接填入其本機連接埠並生成。ComfyUI 管理媒體模型的記憶體配置。

EXE 安裝的便攜版位於 `%LOCALAPPDATA%\LocalLLM\comfyui`，從原始碼執行時則位於專案的 `comfyui`。啟動失敗可查看該版本資料夾內的 `local-llm-comfyui.log`。

| 類型 | 放入 ComfyUI 的位置 | 模型檔案 |
| --- | --- | --- |
| 圖片 · Stable Diffusion 1.5 | `models/checkpoints/` | [v1-5-pruned-emaonly-fp16.safetensors](https://huggingface.co/Comfy-Org/stable-diffusion-1.5/blob/main/v1-5-pruned-emaonly-fp16.safetensors) |
| 影片 · Wan 2.1 1.3B | `models/diffusion_models/` | [wan2.1_t2v_1.3B_fp16.safetensors](https://huggingface.co/Comfy-Org/Wan-2.1/blob/main/split_files/diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors) |
| 影片 · 文字編碼器 | `models/text_encoders/` | [umt5_xxl_fp8_e4m3fn_scaled.safetensors](https://huggingface.co/Comfy-Org/Wan-2.1/blob/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors) |
| 影片 · VAE | `models/vae/` | [wan_2.1_vae.safetensors](https://huggingface.co/Comfy-Org/Wan-2.1/blob/main/split_files/vae/wan_2.1_vae.safetensors) |
| 音樂 · ACE-Step v1 | `models/checkpoints/` | [ace_step_v1_3.5b.safetensors](https://huggingface.co/Comfy-Org/ACE-Step/blob/main/all_in_one/ace_step_v1_3.5b.safetensors) |

## 從原始碼執行或重建 EXE

需要 Python 3.12（含 Tk）。將 [llama.cpp b11810 Windows x64 Vulkan ZIP](https://github.com/ggml-org/llama.cpp/releases/download/b11810/llama-b11810-bin-win-vulkan-x64.zip) 解壓到專案的 `engine-vulkan`，並放入 [llama.cpp 授權文件](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11810/LICENSE)，檔名為 `LICENSE-llama.cpp`。雙擊 `Launch.cmd` 或執行 `python app.py`。

要產生 EXE，安裝 `pyinstaller==6.22.3` 後執行 `python build_windows.py`。輸出位於 `dist/`。引擎和模型檔案均由本機準備，Git 會忽略這些目錄。

要重建安裝包，另準備 [Inno Setup](https://jrsoftware.org/isdl.php)，執行 `python build_windows.py --iscc "C:\path\to\ISCC.exe"`。要加入繁體中文安裝介面，可將 [Inno Setup 繁體中文語言檔](https://jrsoftware.org/files/istrans/) 放到編譯器的 `Languages` 資料夾。持有 Windows 信任的程式碼簽署憑證時，可將 Windows SDK 的 `signtool.exe` 加到 PATH，並加上 `--sign-thumbprint <憑證指紋>` 簽署安裝包、解除安裝程式及尚無有效簽章的執行元件。

## 新桌面工作台（開發分支）

新的 React／Tauri 桌面版仍在驗收。既有 Windows v0.6.2 與 GitHub Pages 可照常使用。

- [介面與實際畫面](docs/UI_DESIGN.md) · [架構](docs/ARCHITECTURE.md) · [路線圖](docs/ROADMAP.md)
- [Windows 打包、安全與簽章](docs/SECURITY_AND_RELEASE.md) · [測試結果](docs/TEST_REPORT.md)

在 Windows 開發機安裝 Python 3.12、Node 24、[Tauri 的 Rust／MSVC／WebView2 先決條件](https://v2.tauri.app/start/prerequisites/)，於庫根目錄執行：

```powershell
python -m pip install --only-binary=:all: -r desktop/requirements-windows.lock
python -m unittest -v
python build_desktop_worker.py
cd desktop
npm ci
npm run tauri -- dev
# 只產生未簽署的本機 Windows x64 開發安裝程式：
npm run tauri -- build --target x86_64-pc-windows-msvc -- --locked
```

暫時只想驗證 UI 時，於 `desktop` 執行 `npm run dev` 並開啟 [本機預覽](http://127.0.0.1:1420/)。它會啟動相同 Python Worker；不需要 Rust／MSVC，也不是可部署的網頁版。第一次聊天可從「運算環境」安裝官方 llama.cpp，再從「模型與應用」下載一個小型 GGUF。
