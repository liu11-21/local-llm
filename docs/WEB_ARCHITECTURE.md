# Web Workspace 0.9.0 Development

基準 `90af62b`（0.8.0 Desktop），工作分支 dev/web-workspace。Desktop 原分支保留。

React → Transport（DesktopIPCAdapter／WebHTTPAdapter）→ WorkspaceApplication →
原 Desktop service → TaskManager／DeviceExecution／RuntimeManager／SQLite。
`workspace_core.py` 是共用外部命令／生命週期邊界；已驗收的商業邏輯不複製。
Desktop 仍用逐行 JSON IPC，Web 用同源 HTTP JSON 與每工作 SSE；推理不在瀏覽器執行。
ComfyUI、OpenVINO、Agent／Team、Remote、Benchmark、模型及作品都由同一服務管理。

選擇最小 Uvicorn + asyncio + h11 ASGI transport，不採 FastAPI／Pydantic-core，
避免基本聊天增加原生擴充；也不採適用範圍有限的 Python http.server 作正式 Web transport。
依賴為固定 hash 的純 Python wheels，沒有 uvicorn[standard]、uvloop、httptools、WebSocket extras。
WebSocket 未納入：現有生成／排程採單向 SSE＋HTTP 取消已足夠，無需雙向 Socket 依賴。
[Python server 限制](https://docs.python.org/3.12/library/http.server.html) ·
[Uvicorn 設定](https://www.uvicorn.org/settings/) · [FastAPI 部署](https://fastapi.tiangolo.com/deployment/manually/)。

Web 限用官方已簽章 llama.exe；Legacy Adapter 留給 Desktop。不執行自製 Worker EXE／Tauri shell。
遠端 Host TLS 的 cryptography 延後到建立憑證才載入；固定 Runtime 的 zstandard、OpenVINO、
ComfyUI 都是另行安裝的選用依賴，可能仍受 Application Control 限制。

最小原型已實跑：官方 Python Valid、官方 llama.app b12360 Valid、Qwen3-0.6B CPU、
真實 HTTP／SSE 繁體回答、取消、SQLite、靜態 React 與關閉清理；基本路徑無 cryptography import。
這台為 Iris Xe，沒有把維護者另一台 RTX／SAC 結果算作本輪測試。
其他階段驗收依 V090_DELIVERY，不以原型通過代表全部移植完成。

最終版本已完成乾淨 ZIP 的部署／升級／更新回滾與 Chrome／Edge 矩陣；另外對相同 78f8f7c CI ZIP
完成真實 CPU／Intel Vulkan、Thinking、Agent／Team、Benchmark、React 聊天與取消清理。
逐項來源與硬體界線見 [完整交付](V090_DELIVERY.md)，不是 pure WebGPU 改寫。
