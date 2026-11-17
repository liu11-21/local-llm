# 0.9.0 Session Recovery Repair

日期：2026-11-17（Asia/Taipei）。基準產品 `fe2a363`、checkout `a7edf98`，分支 `dev/web-workspace`。版本仍為 0.9.0 Development。

## 根因與界線

**PASS：已重現的缺陷。** 舊版 `main.tsx` 只在首次 module boot 呼叫 `initializeWeb()`。
舊啟動連結是 `http://127.0.0.1:port/#bootstrap=...`；在既有同一路徑分頁開啟新片段只觸發 hashchange，不會重新執行 module。
後端重啟會產生新的隨機 bootstrap 並清空記憶體 Session，舊 Cookie 正確失效；前端卻沒有消耗新的登入片段，也沒有可操作的初始化畫面。
舊 CSRF／EventSource 快取沒有統一隨重新驗證清理，初始載入失敗後只留下文字訊息。

[修復前真實 HTTP／Chrome 證據](evidence/session-recovery/BEFORE.json)：服務重啟後，正確 127.0.0.1 Origin／Host 下舊 Session 仍回 401，
同分頁新 bootstrap 沒有消耗。這證明重現案例是工作階段初始化缺口，不能用放寬 CORS 解決。
維護者另一台機器所見的每一筆「跨來源拒絕」沒有原始 Network 記錄，**NOT TESTED：不能推定全部來自相同原因**。
真正 localhost／外部 Origin／錯誤 Host 在本輪仍回 403。

另一項可確認的缺口：Cookie 不以 TCP port 隔離，舊固定名稱在多個 127.0.0.1 工作台並存時會互相覆蓋。
改為 `localllm_web_session_<port>`；這不表示已證明目標桌機當時有多埠衝突。

## 修正

- `web_launcher.py`、`workspace_web.py`：提供 canonical `/launch#bootstrap=...` 登入入口；127.0.0.1 綁定與 Host／Origin 規則不變。
- `transport.ts`：首次及 hashchange 均消耗登入片段，立即移除網址中的 credential；重新驗證後更新 CSRF、清除過期快取、同步其他同源分頁。未授權寫入不重送；只在精確 `CSRF_INVALID` 回應時重新讀取 Session，再要求使用者重試。外部 Origin／Host 拒絕不進入此恢復路徑。
- `WebSessionGate.tsx`、`main.tsx`：首次失敗、逾期、斷線或登出時顯示可操作的恢復畫面。保留已開啟 App 的狀態，提供重新檢查；無有效登入時不會把需要驗證的工作台開放給未授權瀏覽器。
- SSE：斷線後丟棄舊 snapshot，重新確認 Session，再連回既有 job；不重新提交工作。重新驗證後可恢復追蹤，terminal job 關閉連線。取消仍走原已認證 RPC。
- `WebService.tsx`、`/api/logout`：明確登出、撤銷當前 Session、清除相同 port 的 HttpOnly Cookie、停止該 Session 的 SSE，跨分頁同步。登出不刪除資料或自動停止背景工作。
- 後端提供結構化 `SESSION_REQUIRED`／`CSRF_INVALID` 錯誤，前端不靠中文錯誤字串猜測安全例外。

Session、CSRF 為記憶體隨機值；Session 期限 8 小時，服務重啟必須以啟動器持有的新 bootstrap 重新驗證。
bootstrap 在同一服務生命週期可重用，重啟後旋轉；不是公開 API 取得的 bearer，也沒有自動給任意本機網頁登入。
launcher 狀態檔仍使用現有 Windows DPAPI。Cookie 保持 HttpOnly、SameSite=Strict、Path=/、host-only（無 Domain），
本機 HTTP 不宣稱 Secure/TLS。既有無 port 後綴 Cookie 不再作驗證依據，不需使用者手動清除。
Token／CSRF／bootstrap 不放 localStorage、BroadcastChannel、查詢參數或日誌；同源廣播只送狀態通知。

## 測試

| 項目 | 狀態／證據 |
|---|---|
| 舊版實際重現 | **PASS**：舊行為 **FAIL**，新片段不消耗、舊 Session 401；BEFORE.json |
| Backend 單元 | **PASS**：重啟旋轉、舊 bootstrap／Cookie 拒絕、Session 過期、CSRF 拒絕、logout、port cookie 隔離；原 Host／Origin／DNS rebinding 測試保留 |
| 真實 Chrome／HTTP | **PASS**：初啟、reload、同頁重啟、新登入、期限過期、跨分頁、登出清 Cookie、模型庫入口 |
| SSE／取消 | **PASS**：真 HTTP＋真 TaskManager 等待任務，刻意中斷一次 EventSource 後重連，取消原 job；不是 AI／GPU 推理 |
| 寫入不重播 | **PASS**：真 Cookie 旋轉造成 stale CSRF，只送一次遭拒的 POST，刷新憑證但沒有提交停止引擎任務 |
| RTX 原 QA 目錄 | **BLOCKED**：目前主機無該目錄；不能把這些測試當作維護者 RTX 桌機已通過 |

結果：[SESSION_RECOVERY_TESTS.json](evidence/session-recovery/SESSION_RECOVERY_TESTS.json)。
測試伺服器 `desktop/tests/session-server.py` 只在測試使用，沒有加入發行 API 或提供 Session 過期控制端點；
等候／期限觸發只在自建暫存資料夾中，沒有修改使用者 QA 資料。
Network 紀錄只保存 path、status、Origin／Host、拒絕訊息；Console 不保存認證值。

完整 CI、Artifact、SHA 及桌機界線見 [V090_DESKTOP_RETEST](V090_DESKTOP_RETEST.md)。
[hashchange 官方說明](https://developer.mozilla.org/en-US/docs/Web/API/Window/hashchange_event)。
