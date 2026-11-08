# Local LLM v0.2.0

Windows x64 本機模型工作台。需要 Python 3.12（含 Tk）及 llama.cpp 的 Windows x64 CPU 版。

1. 下載 [llama.cpp b11810 Windows x64 CPU ZIP](https://github.com/ggml-org/llama.cpp/releases/download/b11810/llama-b11810-bin-win-cpu-x64.zip)，把整包解壓到專案的 `engine` 資料夾，確認 `engine\llama-server.exe` 和 DLL 在同一層。已有引擎也可在介面按「選擇 llama-server」指定。
2. 雙擊 `Launch.cmd`，或在此資料夾執行 `python app.py`。
3. 在「模型清單」選擇推薦模型，或輸入名稱搜尋 Hugging Face。留空搜尋會顯示最多 40 筆熱門 GGUF 倉庫。選取結果後按「查看 GGUF 版本」，選好檔案再按「前往下載」。也可在「模型下載」直接貼上公開 HTTPS 的 GGUF 下載網址。
4. 選擇執行緒數，按「開始下載」。下載完成後，模型會出現在左欄。也可直接選擇已在磁碟上的 GGUF。
5. 按「啟動模型」，等狀態顯示就緒後就能在「對話」頁傳送訊息。

下載器預設使用 4 個執行緒，可調至 1–16。支援 HTTP Range 的來源會同時傳輸不同區段，並在整檔完成後檢查 GGUF 標頭再放入 `models`。若來源忽略 Range，畫面會顯示降為單一連線。取消會清除當次的暫存檔。

線上清單支援可公開下載的單檔 GGUF。清單會顯示 Hugging Face 提供的檔名與大小，並以選取當下的倉庫版本產生下載連結。

引擎使用 CPU 並監聽本機回環位址。對話紀錄保存在本次工作階段。預填的 SmolLM2 適合測試流程，主要使用英文。

引擎和模型由本機準備。Git 會忽略 `engine/` 和 `models/`。

[llama.cpp 發行版 b11810](https://github.com/ggml-org/llama.cpp/releases/tag/b11810) · [SmolLM2](https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF) · [Qwen2.5](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF)
