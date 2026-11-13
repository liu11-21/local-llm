# SignPath application — UNSENT DRAFT

未提交申請、未取得組織／專案／policy ID、Token 或憑證。需維護者及 Foundation 審查，不能原樣作已符合條件的聲明。

| 欄位 | 草稿內容 |
|---|---|
| 專案 | Local LLM Workspace |
| Repository | https://github.com/liu11-21/local-llm |
| 開發來源 | dev/desktop-workspace；0.7.0 Development；每個候選以完整 SHA 與 Actions Run 識別 |
| 用途 | Windows AI 工作台：本機／雲端聊天、Agent 工具核准、多模型 Team、模型下載、ComfyUI 媒體工作流程、遠端 Host 及 CPU／GPU／NPU 運算適配 |
| 授權 | 第一方已依 A1–A4 明確批准採 MIT，Copyright (c) 2026 劉仲軒；Logo／品牌／UI 截圖／合成媒體排除，第三方、Runtime／模型原授權；整包資格未放行 |
| 發行架構 | React／TypeScript UI、Tauri Rust shell、PyInstaller Python Worker、NSIS current-user installer／uninstaller；AI Runtime／權重依使用者操作另行下載 |
| 維護／發行 | 2026-11-08 起公開；審查起始 119 commits；已發行舊 Tk／Inno v0.6.2，Tauri Workspace 暫以限期 Actions artifact 提供 |
| 來源驗證 | GitHub-hosted Windows 2022、固定 Action SHA／工具鏈／鎖檔、完整 commit、SHA-256、SPDX／Notices、安裝 PE inventory、GitHub provenance；BUILD.json 本身不是平台認證 |
| 使用者隱私 | 本地資料庫／輸出保留本機；雲端／配對 Host 依選定目的地處理；下載、更新、WebView2 及第三方遙測詳 PRIVACY；尚未完成全鏈審查 |
| 第三方 | npm／Cargo／Python 全鎖檔、Microsoft 系統元件、可選 llama.cpp／OpenVINO／Comfy portable、各模型條款；不把權重視為 MIT，不替上游 DLL 簽章 |
| Authors | 維護者角色候選，姓名／權限範圍／MFA 尚待明確指派；AI 工具不取代人類責任 |
| Reviewers | 外部非 committer 提案由團隊審查；單人兼任候選或另邀獨立人，尚待 Foundation 確認；不假定所有本人變更強制非作者審查 |
| Approvers | 單人兼任是否可接受待書面確認，否則另邀核准者；每次正式簽章仍需人工核准，沒有啟用自動核准 |
| 資格結論 | 尚不具備正式申請聲明條件；本地對照 5/14 PASS，詳 SIGNPATH_ELIGIBILITY |

## 最少需要 Foundation 回覆的四組問題

本次不把抽象 AI 著作權疑慮重新設為 MIT gate。公開條件未列 AI 輔助專屬要求，
在來源說明中如實揭露，請 Foundation 如有額外文件要求一併指出即可。

1. **單人責任與來源文件：** 一人兼任 Author／審查外部提案／逐次 Approver 是否可接受，需要何種可執行的保障？如 AI 輔助來源有額外要求，請明示。
2. **確切產物與系統元件：** Tauri 靜態 OSS、PyInstaller Worker、NSIS installer／uninstaller 的可簽清單／嵌套順序，及 Microsoft runtime／WebView2 的 System Library 要件。Logo 尚須另完成可接受許可，不要求豁免其全部元件規則；Worker 版本資源須在請求前補齊。
3. **可選下載與隱私：** 未隨包的 ComfyUI／OpenVINO／llama.cpp 與獨立授權模型（包括受限模型）是否影響資格，以及相關 telemetry／啟動更新查詢需要的安裝告知與可停用安排。
4. **既有發行證據：** 限期的同形式 unsigned NSIS Actions 產物是否足夠；若不足，先建立持久公開 Workspace 預發行版及應附證據為何？本輪未建立 Release／Tag。

附件建議：權利確認、現行正式 LICENSE 與 LICENSE_SCOPE（已具備）、SBOM 原始文檔、第三方 Notice／Covered Source 提供方式、PE 映射、公開 Windows Run、candidate hashes／provenance、roles／MFA／分支保護證據。不要在申請草稿附私人金鑰或真實使用者對話。

## Unsent English inquiry

**DRAFT ONLY — not sent; not an application or statement of eligibility.**

Subject: Eligibility clarification — Local LLM Workspace (MIT, single maintainer)

Dear SignPath Foundation team,

I maintain Local LLM Workspace: https://github.com/liu11-21/local-llm
(dev/desktop-workspace, 0.7.0 Development). I direct its requirements and integration;
first-party development is primarily Codex/AI-assisted. Following explicit maintainer
approval, first-party code, tests, build scripts and technical documentation now use
MIT (Copyright (c) 2026 劉仲軒; adoption commit fae698d).

Third-party components retain their terms. Logos, brand assets, screenshots and
synthetic media are excluded from that grant for now; we will resolve distributable
asset licensing before applying. The installed Logo is reported as AI-generated;
a separate review candidate has recorded OpenAI generation inputs. We do not assert
copyright in every AI output or claim that the entire installer is cleared.

Before applying, could you clarify:

1. May one maintainer be Author, review external contributions and manually approve
   each signing request? What safeguards are required? Please also identify any
   additional provenance requirements for AI-assisted source or generated assets.
2. Can your artifact policy cover a Tauri shell with linked OSS, a PyInstaller Worker
   and NSIS installer/uninstaller? What nested-signing order and Microsoft runtime /
   WebView2 system-library evidence are required? Upstream DLL/PYD files would not be
   re-signed; the Worker's missing PE version metadata must be addressed first.
3. Do optional post-install downloads of ComfyUI, OpenVINO, llama.cpp and separately
   licensed model weights (including restricted models) affect eligibility? What
   installer notices or opt-outs are required for third-party telemetry and update
   checks? These optional AI runtimes/weights are not bundled; Python is bundled.
4. Is an expiring, unsigned Tauri NSIS GitHub Actions artifact sufficient prior-release
   evidence, or must a persistent corresponding unsigned release be published first?

We have GitHub-hosted build evidence, SBOM, original notices, PE inventory and verified
provenance. Redistribution/asset obligations, named roles and MFA/protection evidence
will be resolved before an application or signing request.

Thank you,
Local LLM Workspace maintainer (sender identity/contact to be confirmed)

本草稿 **未寄出、不是申請、不是資格通過聲明**。送件身分與聯絡方式仍待維護者確認；
未授權寄信或送件前不對外提交。沒有 Token、金鑰、使用者對話或機密附件。
正式入口為 [官方申請頁](https://signpath.org/apply.html)，其嵌入表單尚未填寫，未取得欄位不臆填。
公開條件的解讀與外部待決見 [14 項表](SIGNPATH_ELIGIBILITY.md)，
帳號操作見 [Code signing policy](CODE_SIGNING_POLICY.md)。
