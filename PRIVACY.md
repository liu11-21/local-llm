# Privacy and network behavior

適用 0.7.0 Development；這是目前程式行為說明，尚非第三方 Runtime 的隱私保證。詳見 docs/PRIVACY_STORAGE.md。安裝前可從本文件了解資料與網路行為。

| 功能／觸發 | 資料及目的地 | 儲存／控制 |
|---|---|---|
| 本機聊天、Agent、Team、作品 | 提示詞、對話、草稿、工具結果、生成內容存於本機；目前 Agent 工具僅能核准後唯讀查詢硬體、模型、引擎、任務及作品數值參數 | %LOCALAPPDATA%/LocalLLM；請勿把私人資料庫／輸出提交至 Git |
| 啟動／手動檢查更新 | GitHub API、GitHub 下載服務會看到 IP、標準請求資訊與版本查詢；不附帶聊天 | 自動查詢不是自動安裝；下載及執行由使用者決定，目前啟動查詢沒有獨立停用開關 |
| 搜尋與下載模型 | Hugging Face、其檔案服務及重新導向 CDN 收到搜尋詞、檔案請求、IP；需授權的模型可能使用使用者提供的認證 | 下載時由使用者選擇；模型條款依各上游而定 |
| 安裝引擎／ComfyUI／OpenVINO | GitHub、Python／套件來源及 CDN 收到安裝請求；下載後的第三方程式有自己的網路及隱私行為 | 不在本輪自動下載大型 Runtime 或模型；可選元件需使用者操作 |
| 雲端 Team／主模型 | 所選 API 供應商收到提示詞；雲端主模型還會收到成功草稿 | 選擇雲端即有對外傳輸及可能費用；不宣稱供應商零留存 |
| 遠端 Host | 使用者配對的 Host 收到任務、提示詞及必要媒體，並回傳結果 | 應使用 TLS、核對身分及權限；配對資料應保密 |
| GitHub Pages | GitHub Pages、jsDelivr/WebLLM 及模型來源收到頁面／腳本／權重請求 | 網頁版另有瀏覽器快取及 CDN 依賴；不能視為桌面版離線模式 |
| WebView2 安裝 | 缺少 WebView2 時 NSIS 會向 Microsoft 取得 bootstrapper／Runtime | Microsoft 的授權及隱私條款另行適用 |

本專案未新增對維護者的聊天分析或遙測端點；這不等於整個依賴鏈沒有遙測。OpenVINO 鎖檔含 openvino-telemetry，ComfyUI portable 的 PyTorch／CUDA／其他套件、WebView2 及網頁 CDN 的完整資料流尚待審查。正式 SignPath 申請前需確認條款要求的安裝告知及可停用選項是否充分。

解除安裝移除應用程式及捷徑，保留模型、對話與作品。需清除資料時請先備份，再由使用者自行刪除對應資料目錄。不要分享完整診斷檔；遮蔽使用者路徑、Token、遠端位址及私人對話。尚未驗證的資料流列在 OPEN_SOURCE_BLOCKERS，不能稱為隱私審查通過。
