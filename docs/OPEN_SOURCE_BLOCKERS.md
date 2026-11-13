# Open-source and signing blockers

| 優先 | 缺口 | 解決條件／責任 |
|---|---|---|
| BLOCKED | 自有程式、外部貢獻、Logo／圖片／fixture 的權利未確認 | 維護者提供來源／創作或授權證據；目前只確認署名 劉仲軒，不能正式 MIT |
| REVIEW REQUIRED | 第三方原始聲明、Covered Source、模型及 runtime 義務 | 依逐項清單補上缺失 LICENSE、上游來源／確切版本、再散布及商用條件；不能刪功能假裝通過 |
| REVIEW REQUIRED | 下載套件／CDN／工具鏈全圖 | Comfy portable、CUDA／Torch／FFmpeg、WebLLM transitive、Rust stdlib／NSIS／WebView2、Python 嵌入子元件仍需完整證據 |
| REVIEW REQUIRED | Windows 系統檔分發與簽章邊界 | 確認 Microsoft 再散布合法來源、System Library 例外及混合 wrapper／uninstaller 的 Foundation 書面意見 |
| REVIEW REQUIRED | Worker PE metadata | CI 確認 build／IPC 0.7.0，但 FileVersion 未提供；若將 Worker 列為簽章對象，需補齊版本資源或先取得服務方規則確認 |
| REVIEW REQUIRED | 對應形式持久發行 | Workspace 僅 Actions artifact，舊 Tk／Inno Release 不足以直接推定；先確認是否需公開 unsigned Workspace NSIS |
| NOT VERIFIED | MFA／角色／私人安全聯絡人 | 維護者答覆尚未決定；逐一指定並證明，不把帳號名稱自動填為 approver |
| REVIEW REQUIRED | 分支／環境保護與非作者審查 | 已知 protected=false；需之後配置並驗證。候選 signing job 保持 false |
| REVIEW REQUIRED | 安全／隱私與下載可執行 Runtime | Agent 工具與目的地說明、啟動更新停用選項、OpenVINO telemetry／第三方網路行為、安裝前告知需審查 |
| REVIEW REQUIRED | 公開歷史個人路徑 | evidence/v070/upgrade-worker-local.json 的兩個 blob 命中；未確認憑證外洩。先評估替換目前證據／撤下附件及歷史影響，不擅自重寫 Git |
| REVIEW REQUIRED | 語意／圖片秘密審查 | 模式掃描不是完整 DLP；截圖、真實對話／提示詞、任意格式 Token／配對資料、binary 需人工複核 |

若後續發現有效憑證外洩，立刻暫停公開發行準備，撤銷／輪替並依 SECURITY.md 走事件處置。現有報告僅保留位置及類型，不重新輸出秘密。

完成所有可自動化工作不會消除上述法律／外部核准缺口。模型及現有產品功能保留；本輪不更動 main、不建立 Release／Tag、不提交 SignPath 申請。
