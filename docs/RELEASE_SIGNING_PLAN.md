# Release signing implementation plan

已實作候選階段：GitHub-hosted Windows、固定 Actions SHA、npm／Cargo／Python 鎖檔、unsigned NSIS、SBOM 原始 Notices 隨安裝、安裝後 PE／uninstaller 清單、完整 build identity、SHA-256、升級／解除安裝、GitHub provenance。公開建置成功不代表法律審核或 SignPath 核准。

`.github/workflows/signing-review.yml` 只有 workflow_dispatch，job 使用 literal false，無 secrets、無服務呼叫。`signpath/signing-request-step.yml.example` 是非執行範例，所有必要值空白；不會被一般 push／PR 觸發。這不是已運作的正式簽章管線。

未來啟用前必須：完成範圍與第三方審查、決定同形式公開發行、Foundation 核准、全團隊 MFA、明確的 Authors／Reviewers／Approvers、符合獲准角色方案的審查規則、受保護 release-signing 環境、SignPath App 與 branch／workflow／runner policies。單人兼任是否允許待服務方確認；不將非作者審查的較嚴建議冒充官方一律要求。這些設定本輪均未啟用。

正式設計應由獨立、人工啟動的受保護 release workflow 在固定來源 SHA 上建置／驗證，先上傳 unsigned artifact，再將該 upload 的 artifact-id 傳給核准 action；全部前置 jobs 使用 GitHub-hosted Runner。若跨 workflow 選取既有 candidate，需先確認平台 origin／artifact ID 驗證，不可用任意重上傳規避來源鏈。範例僅示意 request step，並非完整可投入生產流程。

上游 `signpath/github-action-submit-signing-request` 已核對 v3 的 Commit f6d04783b4569d051e0c80105fe66e82819d0092。固定頂層 Action SHA 不代表已審查所有嵌入／轉引工具；啟用前需再次審閱並由 Approver 確認 policy 不允許自動核准。

installer／uninstaller 需先決定 Tauri NSIS 模板的嵌套簽署順序與供應者可接受的 artifact 設定，不在 Windows CI 中臨時塞假 SignTool。簽後重新校驗每個被更改的 PE 與 installer hash；驗證上游檔案未被重簽、版本一致、安裝／升級／解除安裝正常。保留原始 unsigned 候選與簽章稽核鏈。

正式發行將是另一次維護者核准；此輪無 Release、Tag、對外申請或正式簽章請求。官方：[SignPath GitHub integration](https://docs.signpath.io/trusted-build-systems/github)、[GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)。

## MIT 採用後的 Actions 準備進度（2026-11-13）

| 項目 | 目前可核對的進度 | 下一個具體條件 |
|---|---|---|
| 第一方授權／封裝 | `fae698d` 已正式採 MIT；Notices seed 帶入 LICENSE／SCOPE／STATUS，測試及本地 prepare 通過 | 不把既有 unsigned 安裝包視為已按新許可重建 |
| 來源及 unsigned 建置證據 | 既有 Windows Run 43409624156、鎖檔、SHA、PE inventory、來源證明可用 | 選定真正要簽的 source SHA／新候選；本輪未執行會 collect 全依賴的完整 workflow |
| GitHub 服務整合 | 文件與固定 SHA 的 Action 範例已備；正式服務未設定 | Foundation 接受後，授權安裝 SignPath App，取得 organization／project／policy IDs，綁定 GitHub trusted build |
| 可簽物件與版本 | Rust shell、Worker、NSIS installer／uninstaller 已各自列出；不簽 upstream DLL／PYD | Foundation 確認 allowlist／nested signing；Worker 缺 PE FileVersion，請求前應加入與 shell／installer 相同產品名及 0.7.0 版本並重建核對 |
| MFA／角色與保護 | API 未提供 MFA 欄；開發分支 protected=false、rulesets=0；單人方案僅候選 | 維護者確認 GitHub 2FA、安排實際人員及保護；SignPath 全員 MFA，逐次人工核准，遵守獲准單人方案 |
| 簽章請求與 secrets | workflow job literal false；範例 if false、必要 IDs／Token 空白；沒有服務請求 | 資格與角色批准後才建立受保護環境及最小權限 Secret，以同一 upload 的 artifact-id 發送人工核准請求 |
| 簽後驗證／發布 | 僅設計，尚無 Foundation 簽章或 Windows 信任結果 | 驗證 signer／時間戳／來源 SHA／PE 版本／安裝與解除安裝、保留上游 bytes；另獲准發布，不自動建立 Release |

Foundation 對 AI 來源／單人方案／產物與系統元件／下載模型／既有發行形式的最少詢問，
已收斂在 [未寄出的四組問題](SIGNPATH_APPLICATION_DRAFT.md#最少需要-foundation-回覆的四組問題)。
若既有發行形式不足，候選方案是另行批准「Workspace unsigned 預發行版」，附 source SHA、
installer SHA、SBOM／Notices、provenance 及未簽章說明，保持 Stable v0.6.2 不變；本輪不建 Release／Tag。

立即可執行的維護者步驟：確認 GitHub MFA，指定可落實的角色方案與聯絡人；
審核並明確授權寄出四組問題的草稿。此核准與本次 A1–A4 不同，不能以 MIT 批准代替寄信或申請授權。
在取得 Foundation 接受及實際產物設定前，保持 Actions 簽章入口禁用。
