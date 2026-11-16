# Web Workspace 相容性與驗收界線

| 項目 | 實作／驗證範圍 |
|---|---|
| Python | 官方 3.12 x64（3.12.10+），原型 Python Software Foundation Authenticode Valid；不用自製 Worker／NSIS／Tauri shell。 |
| 文字 Runtime | 官方 llama.app b12360／2d8a32502，有效 Hugging Face 簽章；原型 Qwen3-0.6B CPU 真實 HTTP／SSE、取消、SQLite與清理通過。 |
| GPU | 本機 Intel Iris Xe；維護者另一台 RTX 5070 Ti＋SAC Vulkan 基準只作供應資訊，本輪 RTX／CUDA NEEDS HARDWARE。 |
| Chrome／Edge | 最終 CI ZIP 的四尺寸／深淺模式／12 頁、匯入、服務管理與重啟通過；另 Chrome 對同一 ZIP 的真實 Qwen3 聊天／SSE 通過。 |
| PWA | manifest＋network-only service worker；安裝入口依瀏覽器／裝置政策，離線無推理能力，後端仍需啟動。 |
| 影音 | 原有 ComfyUI 不重寫；完整權重與原生可攜版按需安裝。模型真實 GPU 生成仍 NEEDS HARDWARE。 |
| OpenVINO／NPU | 原獨立 Adapter／格式／排程保留；原生 PYD／DLL 政策相容與 NPU 實機仍 NEEDS HARDWARE。 |
| 雲端／遠端 | 原帳戶、核准、TLS／配對及媒體協定保留；付費帳號 NEEDS AUTH，兩台實體 Host／Client NEEDS HARDWARE。 |
| SQLite | 0.8 與 Web 同一資料格式；升級校驗備份、檔案鎖、版本分離、保留原始模型／作品；未來不相容 schema 仍拒絕舊讀取。 |

基本 HTTP 堆疊只有固定的純 Python uvicorn／h11／click／colorama，不啟用 FastAPI pydantic-core 或 Uvicorn native extras。
官方 Python 本身仍載入標準庫原生元件；Windows venv 建立時可能複製上游 launcher，但本程式不執行它。
Runtime 解壓需選用 zstandard；私人 Host 建立憑證需 cryptography／cffi，這些 wheel hash 可驗證但不能保證 SAC 放行。
ComfyUI／OpenVINO 也各有原生依賴；阻擋時指出對應功能／檔案，不停用安全政策或假冒 ready。
已有官方 llama.exe 可直接選擇，不必為了聊天安裝 zstandard。原有手動 TLS 憑證 Host 接口保留，
可由維護者另行配置受信任的憑證來源；未將其視為已完成裝置政策驗收。

SAC／WDAC 實機驗收必須另記政策模式、版本、實際 Python／腳本／EXE／DLL／PYD 與 3077。
一般 Windows CI、單一 EXE Valid、安裝成功或正常推理都不能代替這份證據。本輪預設為 **NOT VERIFIED**。
簽章與憑證方案依維護者方向停止推進；歷史 MIT／第三方授權與素材範圍仍有效，沒有重啟 SignPath 申請。

0.9.0 Runtime 偵測修復的目標 RTX 5070 Ti／Intel Graphics 安裝偵測及 SAC 驗收另標 **BLOCKED**：
開發主機沒有目標已安裝 Runtime。Mock 測試、手動既有 SDK、歷史推理與 Windows CI 結果各自記錄，
不合併成該主機已通過。原生選擇器使用官方 Python＋Win32 common dialog；需要互動桌面，
本輪互動點選尚未驗證。[詳細驗收](RUNTIME_DETECTION_REPAIR.md)。
