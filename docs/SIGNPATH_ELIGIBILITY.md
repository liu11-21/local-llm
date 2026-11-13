# SignPath eligibility — 2026-11-13

**4 PASS / 14；7 REVIEW REQUIRED；1 BLOCKED；2 NOT VERIFIED。** 這是對使用者指定 14 項的本地證據對照，不是 Foundation 的核准、官方計分或保證。申請尚未提交。

| # | 項目 | 狀態 | 證據／缺口 |
|---|---|---|---|
| 1 | OSI 專案授權 | BLOCKED | MIT 僅候選；權利待確認，GitHub license=null |
| 2 | 專有元件／系統例外 | REVIEW REQUIRED | VC／UCRT／API sets／WebView2 的條款及 System Library 適用性待核對 |
| 3 | 全元件授權／商業雙重授權 | REVIEW REQUIRED | 沒有已確認商業雙重授權安排；仍缺 binary、工具鏈、模型與 portable 全圖證據；一般 MIT OR Apache 選擇不等於商業雙重授權 |
| 4 | 持續維護 | PASS | 起始 119 reachable commits、持續 Actions；不推論專案聲譽已獲接受 |
| 5 | 對應 Windows 發行形式 | REVIEW REQUIRED | 有舊 Tk／Inno Release、Workspace Tauri 僅限期 Actions artifact；是否足夠待書面確認 |
| 6 | 公開用途及下載入口 | PASS | dev README 說明用途、unsigned 與 Actions 取得方式 |
| 7 | 公開來源建置 | PASS | Windows CI 從公開 commit、鎖檔、固定工具鏈建置；不宣稱位元組重現 |
| 8 | 安全與隱私 | REVIEW REQUIRED | Agent 核准、可執行 Runtime 下載、雲端／遠端流量、第三方 telemetry 與啟動更新查詢需審閱 |
| 9 | 正式解除安裝 | PASS | NSIS per-user uninstall、捷徑移除及使用者資料保留有 CI 測試 |
| 10 | Authors／Reviewers／Approvers | NOT VERIFIED | 維護者答覆尚未決定；政策草案不是角色指派 |
| 11 | 全團隊 MFA | NOT VERIFIED | 未取得 GitHub／未來 SignPath 帳號證據；不能從 Token 可用推定 |
| 12 | 程式碼審查 | REVIEW REQUIRED | 草案已建立；觀察到兩分支 protected=false，無 enforcement 證據 |
| 13 | 自有二進位簽章範圍 | REVIEW REQUIRED | 已移除舊腳本全 DLL 重簽；Rust 靜態連結、PyInstaller wrapper、NSIS uninstaller 仍待確認 |
| 14 | 下載 Runtime／模型書面澄清 | REVIEW REQUIRED | ComfyUI／CUDA／模型限制及下載器可執行內容，需 Foundation 審閱；本輪未聯絡 |

本表依 [Foundation 官方條件](https://signpath.org/terms.html) 與 [GitHub trusted-build 整合](https://docs.signpath.io/trusted-build-systems/github) 建立。沒有自訂最低專案年齡要求，也不把短期維護紀錄當聲譽保證。對 Actions 發行形式、系統元件、混合二進位及下載模型的判斷均保留 REVIEW REQUIRED。
