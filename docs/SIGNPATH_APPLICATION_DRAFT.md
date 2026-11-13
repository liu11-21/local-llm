# SignPath application — UNSENT DRAFT

未提交申請、未取得組織／專案／policy ID、Token 或憑證。需維護者及 Foundation 審查，不能原樣作已符合條件的聲明。

| 欄位 | 草稿內容 |
|---|---|
| 專案 | Local LLM Workspace |
| Repository | https://github.com/liu11-21/local-llm |
| 開發來源 | dev/desktop-workspace；0.7.0 Development；每個候選以完整 SHA 與 Actions Run 識別 |
| 用途 | Windows AI 工作台：本機／雲端聊天、Agent 工具核准、多模型 Team、模型下載、ComfyUI 媒體工作流程、遠端 Host 及 CPU／GPU／NPU 運算適配 |
| 授權 | 擬 MIT，候選署名 劉仲軒；已記錄維護者主導 Codex／AI 輔助來源，未識別具體第一方衝突；合約／輸入例外、資產及最終範圍／採用待確認，尚非現行 OSI 授權 |
| 發行架構 | React／TypeScript UI、Tauri Rust shell、PyInstaller Python Worker、NSIS current-user installer／uninstaller；AI Runtime／權重依使用者操作另行下載 |
| 維護／發行 | 2026-11-08 起公開；審查起始 119 commits；已發行舊 Tk／Inno v0.6.2，Tauri Workspace 暫以限期 Actions artifact 提供 |
| 來源驗證 | GitHub-hosted Windows 2022、固定 Action SHA／工具鏈／鎖檔、完整 commit、SHA-256、SPDX／Notices、安裝 PE inventory、GitHub provenance；BUILD.json 本身不是平台認證 |
| 使用者隱私 | 本地資料庫／輸出保留本機；雲端／配對 Host 依選定目的地處理；下載、更新、WebView2 及第三方遙測詳 PRIVACY；尚未完成全鏈審查 |
| 第三方 | npm／Cargo／Python 全鎖檔、Microsoft 系統元件、可選 llama.cpp／OpenVINO／Comfy portable、各模型條款；不把權重視為 MIT，不替上游 DLL 簽章 |
| Authors | 維護者角色候選，姓名／權限範圍／MFA 尚待明確指派；AI 工具不取代人類責任 |
| Reviewers | 外部非 committer 提案由團隊審查；單人兼任候選或另邀獨立人，尚待 Foundation 確認；不假定所有本人變更強制非作者審查 |
| Approvers | 單人兼任是否可接受待書面確認，否則另邀核准者；每次正式簽章仍需人工核准，沒有啟用自動核准 |
| 資格結論 | 尚不具備正式申請聲明條件；本地對照 4/14 PASS，詳 SIGNPATH_ELIGIBILITY |

提交前需向 Foundation 書面詢問：

1. Tauri 的限期 Actions artifact 能否作相同形式既有發行證據？若不足，持久公開的 unsigned NSIS 發行應附何資料？
2. 系統再散布 VC／UCRT／API sets、WebView2 bootstrapper 是否適用允許範圍？需要哪些來源／授權證據？
3. Rust shell 靜態連結 OSS、PyInstaller bootloader wrapper、NSIS installer／uninstaller 的可簽範圍及 artifact configuration 為何？上游 DLL 保持原簽章可否接受？
4. 使用者選擇下載的 Comfy portable、CUDA／FFmpeg、OpenVINO、受限制模型權重及 Agent 核准工具能力，會如何影響資格？
5. 啟動更新查詢、可選 Runtime 的第三方 telemetry、網頁 CDN 與雲端／遠端目的地，還需哪些安裝告知或停用選項？

附件建議：權利確認、現行正式 LICENSE（目前尚無）、SBOM 原始文檔、第三方 Notice／Covered Source 提供方式、PE 映射、公開 Windows Run、candidate hashes／provenance、roles／MFA／分支保護證據。不要在申請草稿附私人金鑰或真實使用者對話。

## Unsent English inquiry

**DRAFT ONLY — not sent; not an application or statement of eligibility.**

Subject: Eligibility clarification: AI-assisted, single-maintainer Local LLM Workspace

Dear SignPath Foundation team,

I maintain Local LLM Workspace: https://github.com/liu11-21/local-llm (dev/desktop-workspace, 0.7.0 Development). I direct its requirements and integration; first-party code is primarily Codex/AI-assisted, and the Logo is reported as AI-generated. We are preparing MIT adoption, which is not approved yet. Upstream code and assets retain their own terms; we do not claim exclusive copyright in every AI output.

A separate new Logo candidate was generated with the OpenAI built-in image tool, without external image references. The installed Logo is unchanged.

Before applying, could you clarify:

1. Are there additional provenance or rights-documentation requirements for AI-assisted source or an AI-generated Logo?
2. May a single maintainer hold Author, Reviewer and Approver responsibilities, review external contributions and manually approve each signing request, or is another human required? Which safeguards would you require?
3. Which artifacts could be signed: a Tauri shell with linked OSS crates, a PyInstaller Worker with upstream bootloader, and generated NSIS installer/uninstaller? We would preserve upstream DLL/PYD signatures and address the Worker's missing PE version metadata.
4. Does an application that optionally downloads ComfyUI portable, OpenVINO, llama.cpp and separately licensed AI weights qualify? Models/runtimes are not bundled in the Workspace installer. Please advise on restricted model terms, system libraries and third-party telemetry.
5. Is the existing expiring unsigned Tauri NSIS Actions artifact sufficient evidence of prior release, or should we first publish a persistent corresponding unsigned release?

We have GitHub-hosted build evidence, SBOM, notices, PE inventory and verified provenance. Roles, MFA/protection evidence and remaining redistribution obligations will be resolved before any application or signing request.

Thank you,
Local LLM Workspace maintainer (sender identity to be confirmed)

本草稿不包含有效 Token、私人金鑰或已批准的角色；送件身分與內容仍由維護者確認。本輪只保存文字，未向 Foundation 聯絡。公開條款的 AI／單人安排缺口見 SIGNPATH_ELIGIBILITY.md；帳號操作步驟見 CODE_SIGNING_POLICY.md。
