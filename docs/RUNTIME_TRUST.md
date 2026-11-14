# Runtime Trust — 0.8.0 Development

2026-11-14。RuntimeTrust 分開記錄來源、預期 SHA-256、Authenticode、啟動、裝置探索、推理及 SAC，
沒有將任何單一狀態合併成「全部安全」。固定官方套件的真實安裝證據見
[evidence](evidence/v080/managed-runtime-install.json)。

| 證據 | 判定條件 | 不代表 |
|---|---|---|
| 來源確認 | 固定 manifest 官方 HTTPS 來源，內容與預期 EXE hash 相符 | 模型及全部 DLL 自動可信 |
| SHA-256 驗證 | 壓縮檔與解壓 EXE 分別比對固定值；版本目錄不覆蓋衝突檔 | 雜湊本身能提供程式作者身分 |
| Authenticode Valid | OS 驗證有效簽章，新 Adapter 啟用前要求 Hugging Face signer | SAC 已開啟或全部元件放行 |
| 啟動成功 | 隨機 Key 的 /health、/v1/models 與 alias 握手完成 | 已做推理或 GPU 算子全數執行 |
| GPU 辨識 | 選定 Runtime 的 serve --list-devices 成功回報 | 共享容量等於獨立顯存 |
| 推理成功 | 有非空正式 content，保存 usage／timings | 品質、繁體指令服從或效能排名保證 |
| SAC 相容 | 必須另記錄 SAC 政策模式、實機執行及所有相關元件 | 本輪尚未完成，保持 NOT VERIFIED |

下載預設是固定 b12360 / 2d8a32502 的 x86_64 Vulkan `kkkkk` 基礎 CPU preset：
[manifest](../llama-app-runtime.json)。壓縮 SHA `e16cada91c78a6110d08e1f2431f56ca79238e03fbab9855c4f62a9483fa886a`；
EXE SHA `1dd8a275a6466e42c0f849df9beb3b4deb43c107e6a568fd1b5cecf22c905a1a`。
這與維護者另一台主機的 `ad0e800c...` binary 是不同 preset，不混用雜湊或宣稱相同效能。
官方 bucket 的 ETag 未當作 SHA-256；實際 bytes 雜湊與有效 Hugging Face 簽章分別核對。
不執行 install.ps1，不下載執行未檢查的 probe／unzstd；使用固定 Python zstandard 解壓，保留上游原文。

偵測 PATH、使用者 LOCALAPPDATA 下的官方安裝及 Windows App Alias，沒有硬編碼帳號名稱。
Alias／選定檔只是入口。啟動模型後可在進階介面要求檢查實際 process image 與已載入 modules，
各 EXE／DLL 保留自己的 hash／簽章；延遲載入或無權讀取部分保持 NOT VERIFIED。
主程式簽章不得傳播給其他檔案。新 runtime 在版本目錄獨立安裝，完成後仍需確認切換；舊引擎保留。

近期 Code Integrity 3077 僅唯讀；啟動錯誤會關聯 Runtime 檔名，診斷頁列出實際事件 EXE／DLL，
並提示事件也可能屬於其他程式。未取得事件不等於無攔截。沒有自動 unblock、變更防火牆、停用
SAC／Defender／Windows 安全政策，也沒有替上游檔案重簽。

服務只綁定 127.0.0.1，使用每個實例的新隨機 LLAMA_API_KEY，透過 Worker 代理；
前端不取得 Key／port。llama.app 明確限制 cors-origins localhost，停用可用的 webui／agent flags，
不啟用原生 exec 工具。實測未認證推理回 401、外部 Origin 不取得 CORS 授權。
伺服器錯誤保留可用診斷，但遮蔽 Key、Bearer 與已知模型／Runtime 路徑。
父應用的既有 Windows Job Object 加上停止時的 process-tree cleanup 管理子程序。

此文件不改變專案 MIT 範圍；Runtime MIT 與其他依賴依原授權，Windows 應用仍未簽章、SignPath 未核准。

## 本輪已載入元件的實測（非 SAC 保證）

[程序樹檢查](evidence/v080/loaded-component-inspection.json) 顯示主映像與固定 EXE hash 相符；
另觀測到 Microsoft 簽署的 conhost.exe 子程序。這次 54 個已載入元件均為 Authenticode Valid，
各自保存檔名、hash、signer／issuer，而非沿用主 EXE 結果。未讀取、超過上限、未載入或日後新增元件
仍不能據此判通過。SAC 政策模式及其啟用下的完整相容性保持 NOT VERIFIED。

切回 legacy 時清除另一個映像的信任結果；候選／主／子程序的受檢路徑分別顯示，
不能把新版 Hugging Face 簽章誤標到未簽章的舊引擎。此隔離已有單元與 UI 回歸。

官方啟用條件精確比對有效憑證 subject 中的 CN 與 Organization 均為 Hugging Face，
不以包含相似字串的另一個 publisher 當作官方。固定上游授權也以 SHA 比對並強制 LF 檢出，
避免 Windows 換行轉換造成安裝完整性失敗；兩者均有反例回歸。
