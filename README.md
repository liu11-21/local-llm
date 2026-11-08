# Local LLM

Windows x64 本機模型工作台。需要 Python 3.12（含 Tk）及 llama.cpp 的 Windows x64 CPU 版。

1. 下載 [llama.cpp b11810 Windows x64 CPU ZIP](https://github.com/ggml-org/llama.cpp/releases/download/b11810/llama-b11810-bin-win-cpu-x64.zip)，把整包解壓到專案的 `engine` 資料夾，確認 `engine\llama-server.exe` 和 DLL 在同一層。已有引擎也可在介面按「選擇 llama-server」指定。
2. 雙擊 `Launch.cmd`，或在此資料夾執行 `python app.py`。
3. 在「模型下載」選擇 SmolLM2 測試模型或 Qwen2.5 中文聊天模型，也可以貼上公開 HTTPS 的單檔 GGUF 下載網址。Hugging Face 請使用 `/resolve/` 下載連結。
4. 選擇執行緒數，按「開始下載」。下載完成後，模型會出現在左欄。也可直接選擇已在磁碟上的 GGUF。
5. 按「啟動模型」，等狀態顯示就緒後就能在「對話」頁傳送訊息。

下載器預設使用 4 個執行緒，可調至 1–16。支援 HTTP Range 的來源會同時傳輸不同區段，並在整檔完成後檢查 GGUF 標頭再放入 `models`。若來源忽略 Range，畫面會顯示降為單一連線。取消會清除當次的暫存檔。

引擎使用 CPU 並監聽本機回環位址。對話紀錄保存在本次工作階段。預填的 SmolLM2 適合測試流程，主要使用英文。

引擎和模型由本機準備。Git 會忽略 `engine/` 和 `models/`。

[llama.cpp 發行版 b11810](https://github.com/ggml-org/llama.cpp/releases/tag/b11810) · [SmolLM2](https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF) · [Qwen2.5](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF)
