# SignPath eligibility — 2026-11-13

**5 PASS / 14；7 REVIEW REQUIRED；0 BLOCKED；2 NOT VERIFIED。** 這是對使用者指定 14 項的本地證據對照，不是 Foundation 的核准、官方計分或保證。申請尚未提交。

| # | 項目 | 狀態 | 證據／缺口 |
|---|---|---|---|
| 1 | OSI 專案授權 | PASS | 維護者另確認／批准 A1–A4；根 LICENSE 已採 MIT，署名 Copyright (c) 2026 劉仲軒。僅第一方範圍；資產／整包元件資格仍見第 2／3 項，不代表 Foundation 已接受 |
| 2 | 專有元件／系統例外 | REVIEW REQUIRED | VC／UCRT／API sets／WebView2 的條款及 System Library 適用性待核對 |
| 3 | 全元件授權／商業雙重授權 | REVIEW REQUIRED | 沒有已確認商業雙重授權安排；仍缺 binary、工具鏈、模型與 portable 全圖證據；一般 MIT OR Apache 選擇不等於商業雙重授權 |
| 4 | 持續維護 | PASS | 起始 119 reachable commits、持續 Actions；不推論專案聲譽已獲接受 |
| 5 | 對應 Windows 發行形式 | REVIEW REQUIRED | 有舊 Tk／Inno Release、Workspace Tauri 僅限期 Actions artifact；是否足夠待書面確認 |
| 6 | 公開用途及下載入口 | PASS | dev README 說明用途、unsigned 與 Actions 取得方式 |
| 7 | 公開來源建置 | PASS | Windows CI 從公開 commit、鎖檔、固定工具鏈建置；不宣稱位元組重現 |
| 8 | 安全與隱私 | REVIEW REQUIRED | Agent 核准、可執行 Runtime 下載、雲端／遠端流量、第三方 telemetry 與啟動更新查詢需審閱 |
| 9 | 正式解除安裝 | PASS | NSIS per-user uninstall、捷徑移除及使用者資料保留有 CI 測試 |
| 10 | Authors／Reviewers／Approvers | NOT VERIFIED | 單人兼任是待 Foundation 確認的方案，不假定必須三人或已允許自審；維護者仍未批准實際角色 |
| 11 | 全團隊 MFA | NOT VERIFIED | 未取得 GitHub／未來 SignPath 帳號證據；不能從 Token 可用推定 |
| 12 | 程式碼審查 | REVIEW REQUIRED | 既有 protected=false 快照未由本輪重查。官方明定非 committer 提案由團隊審查；所有變更獨立非作者審查屬專案較嚴建議，不是已證實統一硬性門檻；單人方案待確認 |
| 13 | 自有二進位簽章範圍 | REVIEW REQUIRED | Rust shell、PyInstaller Worker、NSIS installer／uninstaller 各別確認；Worker PE metadata 待補／確認。上游 DLL／PYD 不列專案簽章對象 |
| 14 | 下載 Runtime／模型書面澄清 | REVIEW REQUIRED | ComfyUI／CUDA／模型限制及下載器可執行內容，需 Foundation 審閱；本輪未聯絡 |

本表依 [Foundation 官方條件](https://signpath.org/terms.html) 與 [GitHub trusted-build 整合](https://docs.signpath.io/trusted-build-systems/github) 建立。沒有自訂最低專案年齡要求，也不把短期維護紀錄當聲譽保證。對 Actions 發行形式、系統元件、混合二進位及下載模型的判斷均保留 REVIEW REQUIRED。

2026-11-13 文件覆核：公開條件未列出 AI 輔助開發專案的專屬禁令／額外清單，也沒有明文規定三個角色必須由三個不同人擔任。這不是已確認豁免或保證接受單人自批；已準備未寄出的英文詢問，見 SIGNPATH_APPLICATION_DRAFT.md。AI 應用被列為服務專案也不能證明其程式為 AI 產生、或推定本專案獲准。沿用同一 14 項；只有第 1 項因明確批准與根 LICENSE 正式採用改為 PASS，其餘不變，沒有新增標準或推定整包／Foundation 已通過。
