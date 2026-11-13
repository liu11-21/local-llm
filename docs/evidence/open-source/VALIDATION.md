# Open-source preparation validation

2026-11-13，0.7.0 Development。起始 HEAD adbe209a50286eb1ff1321c770dd8927c45d3e1d。MIT 未採用，SignPath 未申請，候選保持 unsigned。

| 檢查 | 本機結果／限制 |
|---|---|
| Python full suite | 207 tests PASS、7 TLS skips；本機 LOCALLLM_TEST_TLS_INTERCEPTED=1，不能當乾淨 TLS 驗證 |
| 新授權／Worker 回歸 | 17 tests PASS；覆蓋鎖檔全圖、未知權利、Notice 篡改、簽章 allowlist、無法執行的候選 workflow、SPDX 不合法式 |
| TypeScript／Vite | PASS；既有約 721 kB chunk warning，沒有為授權工作更動 UI 功能 |
| Chromium | PASS；第一次 loopback 被沙盒阻擋，獲准在正常本機環境重跑既有完整驗收通過 |
| SPDX／Notices | 官方 2.3 JSON schema、ID／relationship references、索引 SHA-256 PASS；法律資格仍 REVIEW REQUIRED |
| Actions lint | PASS；僅針對 signing-review 的刻意 constant-false guard 設定狹窄 lint 例外，未移除鎖定 |
| 版本 | App／npm／Cargo／Tauri／Worker 同為 0.7.0 Development |
| 原始上游聲明 | llama.cpp pinned LICENSE 既有 hash 測試 PASS；新 Notice 用 -text 保留原始 bytes |
| Windows Cargo／打包／安裝／provenance | 待本輪公開 Windows CI，完成後在此補入 Run／Commit／artifact／PE 結果，不以本機 UI 測試代替 |

source-ownership.json 與 public-history-screen.json 記錄各自掃描的完整 head。產生報告本身必須在後續提交保存，因此不宣稱報告可對包含其自身新 hash 的同一 commit 完成自我列舉。repository-state.json 為 API 擷取時點快照，不代表未來設定。

第一輪 Windows Run 43409027304：完整測試暴露 Agent restart fixture 的排程 ticker race，清理時仍可能執行先前排隊的任務並持有 SQLite。修正 test_agent_workflow.py：_dispatch mock 保留到 Desktop 關閉，兩個實例都在暫存目錄清理前關閉。保留所有核准／版本／restart 斷言，沒有忽略例外或略過測試；18 項 Agent／授權回歸本機通過。這是測試生命週期修正，未改產品資料庫或排程語意，待新 Windows Run 全驗證。
