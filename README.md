# Local LLM v0.4.0

Local LLM 是 Windows x64 本機聊天與媒體創作工作台。發行版的 `LocalLLM-v0.4.0-Windows-x64.exe` 包含 Python 執行環境和 llama.cpp Vulkan／CPU 引擎。雙擊即可開啟。

1. 到「模型清單」選擇依本機硬體排序的推薦模型，或搜尋 Hugging Face 公開單檔 GGUF。選好檔案後按「前往下載」。已有 GGUF 可直接按「選擇本機 GGUF」。
2. 在「模型下載」按「開始下載」。預設 4 個執行緒，可調整為 1–16。支援 HTTP Range 的來源會平行下載，下載完成才將模型放入資料夾。
3. 在左欄選擇模型，查看「啟動資源預估」，再按「啟動模型」進行串流對話。

聊天引擎啟動前會重新讀取 GGUF 檔案大小、層數與引擎回報的可用 GPU 記憶體。程式按預留的 GPU 記憶體分配卸載層數，其餘層由 CPU 使用 RAM。引擎支援時會映射原本的 GGUF 檔案，由 Windows 按需將檔案頁載入 RAM。磁碟映射顯示的是原模型檔大小。共用 GPU 記憶體會計入 RAM 預估。實際佔用會隨模型架構、上下文和 Windows 快取而變化。GPU 啟動失敗時會嘗試 CPU。

EXE 下載的模型與生成的作品會分別儲存在 `%LOCALAPPDATA%\LocalLLM\models` 和 `%LOCALAPPDATA%\LocalLLM\outputs`。從原始碼執行時使用專案內的 `models` 和 `outputs`。舊版的本機 GGUF 可在新版用檔案選擇器匯入。

## 圖片、影片與音樂

安裝並啟動 [本機 ComfyUI](https://docs.comfy.org/installation/desktop/windows)，並將下表檔案放入 ComfyUI 的模型庫。進入 Local LLM「創作」，填入 ComfyUI 的本機連接埠（預設 `8188`），選擇類型、輸入描述並按「開始生成」。音樂可另填歌詞。作品完成後可用「開啟作品」預覽。這些模型和生成引擎需另行安裝，ComfyUI 管理媒體模型的記憶體配置。

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
