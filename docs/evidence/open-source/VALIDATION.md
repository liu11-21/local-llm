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
| 版本 | App／npm／Cargo／Tauri／Worker build／IPC 同為 0.7.0 Development；Worker PE FileVersion 未提供，簽章前另確認 |
| 原始上游聲明 | llama.cpp pinned LICENSE 既有 hash 測試 PASS；新 Notice 用 -text 保留原始 bytes |
| Windows Cargo／打包／安裝／provenance | [Run 43409624156 PASS](https://github.com/liu11-21/local-llm/actions/runs/43409624156)，來源 12869bc64cedea0a7a8d562da30384223ed2e531；乾淨 Runner Python 207 cases（build 前僅 packaged worker case 暫略，build 後單獨 PASS）、完整 Chromium、Cargo／Tauri／NSIS、升級／解除安裝／資料保留、Notices 與 PE 皆通過 |

候選 artifact 14029707170，installer 13,457,394 bytes、NotSigned，SHA-256 c0b1e5c6a92ff7cc339561617b73762b0daa29fbbeba8631d1e6a29466842116。下載 ZIP SHA-256 f20c7afd26bff100b3f0a3e2b1960cb0d2b994abd893d273efdece9e8b6b74ea 與 GitHub artifact digest 一致。官方 GitHub CLI 獨立來源證明驗證 PASS，匹配 repo／workflow／commit／ref／GitHub-hosted；見 candidate-verification.json、PROVENANCE.json 與原始 provenance.sigstore.json。共 72 PE、67 upstream Valid／5 NotSigned；installer 未簽章。

持久保存的實際 CI SBOM／Notices 索引與重建方式見 CI_NOTICES.md；325 份原文依 hash 分散保存在 docs/sbom/license-texts 與 ci-extra-license-texts。缺失原文／法律義務仍 REVIEW REQUIRED。CI 成功未改變 SignPath 4/14 PASS 或 MIT 權利 pending。

已從即將提交的原文目錄重建 886 個 indexed Notice references（可共用相同原文），再次通過官方 SPDX schema／refs／SHA 驗證。新增公開證據的 credential／user-path 模式檢查零命中。原始 CI JSON／bundle 及新增上游 Notice 以局部 .gitattributes 禁用換行轉換；不改已驗證應用程式碼或執行檔。

source-ownership.json 與 public-history-screen.json 記錄各自掃描的完整 head。產生報告本身必須在後續提交保存，因此不宣稱報告可對包含其自身新 hash 的同一 commit 完成自我列舉。repository-state.json 為 API 擷取時點快照，不代表未來設定。

第一輪 Windows Run 43409027304：完整測試暴露 Agent restart fixture 的排程 ticker race，清理時仍可能執行先前排隊的任務並持有 SQLite。修正 test_agent_workflow.py：_dispatch mock 保留到 Desktop 關閉，兩個實例都在暫存目錄清理前關閉。保留所有核准／版本／restart 斷言，沒有忽略例外或略過測試；18 項 Agent／授權回歸本機通過，後續 Run 43409624156 全驗證 PASS。這是測試生命週期修正，未改產品資料庫或排程語意。

最終逐檔／歷史快照 head 為 12869bc64cedea0a7a8d562da30384223ed2e531：698 tracked files、122 reachable commits、1,292 文字 blob、92 binary／large blobs 未語意檢查；已設定的 credential patterns 及補充 literal assignment 無命中，兩筆既有 user-path metadata 命中。最後保存本報告的提交僅增加／更新審查文件與公開 CI 證據；不冒充對自身 hash 的同提交完整掃描，也不改變已測試產品碼。
