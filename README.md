# Local LLM v0.7.0

Local LLM 是 Windows x64 本機聊天與媒體創作工作台。發行版的 `LocalLLM-v0.7.0-Windows-x64.exe` 包含 Python 執行環境和 llama.cpp Vulkan／CPU 引擎。雙擊即可開啟。

## 程式更新

從 v0.7.0 起，Windows EXE 開啟時會在背景檢查 GitHub 的最新正式版。右上角的「程式更新」也能手動檢查。有新版時按「下載更新」，待 SHA-256 核對完成後開啟下載資料夾，關閉目前版本，再雙擊新版 EXE。各版本的模型、作品和 ComfyUI 安裝資料共用 `%LOCALAPPDATA%\LocalLLM`。

v0.6.0 或更早的 EXE 請先從 [GitHub Releases](https://github.com/liu11-21/local-llm/releases/latest) 下載一次新版。

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
