# Web Workspace 安全邊界

只綁定 `127.0.0.1`，Uvicorn asyncio／h11，不信任 forwarded headers。固定 Host 必須是實際 `127.0.0.1:port`，
拒絕重複 Host／Origin／Cookie 安全標頭、非 loopback client、外部 Origin、cross-site／same-site 其他來源。
不接受自訂 LAN bind；遠端運算另用原有明確啟用的 TLS／配對 Host，不公開本機 Web API。

啟動器以高熵 fragment credential 打開瀏覽器，React 之前先移除 fragment；不放 query、access log 或 referrer。
同源 POST 換 HttpOnly／SameSite=Strict host-only cookie；寫入再驗證 Origin＋session＋獨立 CSRF header。
session 最長 8 小時，重啟失效，需從啟動器重新開啟；不透明 Runtime API Key／port 仍由後端管理。
控制檔在 Windows 使用目前帳戶 DPAPI 加密，停止透過驗證 API，不按任意 PID kill。

API、SSE、作品及匯出需登入；同源 UI 可公開載入但無資料權限。CORS 不提供跨來源授權。
SSE 只讀既有 Job，不重送工作；斷線後查詢同一 ID，POST 失敗不自動重試。
限制 body、連線／SSE 數量、閒置與 HTTP 解析大小，關閉 access logs。
RPC 沿用核心欄位驗證、排程、Agent allowlist／逐項核准與審計；Web 拒絕任意檔案開啟與 Desktop EXE 更新。
Web 新文字 Runtime 必須有效官方簽章，保存內容 pin，啟動後另檢查主／子映像與 DLL；不把主 EXE Valid 當 SAC 保證。

GGUF 上傳：只接受安全 basename、容量上限／磁碟保留、每 session 一筆、受管暫存、連續位移、逐塊 hash、GGUF header、
原子不覆蓋發佈；不接受使用者指定儲存路徑。作品只提供既有固定 ID／副檔名，支援受限 Range；
Benchmark 匯出使用伺服器產生的短期 ID，不能讀任意本機路徑。拒絕符號連結／重新導向與路徑穿越。

CSP 限 self scripts／connect，禁 object／frame／base；樣式保留既有必要 inline styles。API／靜態檔 no-store。
PWA service worker network-only，無 API／聊天／憑證／過期 UI 快取；離線只顯示停止服務指引。
同源多視窗只廣播 invalidation，不廣播提示詞或憑證；服務閒置回收與停止流程見安裝文件。
Windows Job Object kill-on-close 管理 Python Host 與繼承的子程序，正常停止另沿用核心清理；建立保護失敗會拒絕啟動。

界線：此本機 HTTP 服務不是多使用者／公網伺服器；未經外部滲透測試。Cookie 不按 port 隔離，
同帳戶惡意程式／可讀寫使用者資料的惡意瀏覽器擴充不在此邊界內；請勿在同一來源部署其他不可信網站。
manifest／SHA 是完整性與來源核對工具，不是發行者數位簽章；同帳戶能修改程式及 hash 檔不能被視為已防護。
不修改 Defender／SAC／WDAC／PowerShell 政策，不執行遠端安裝腳本，基本依賴 hash 與 HTTPS 驗證不可略過。
