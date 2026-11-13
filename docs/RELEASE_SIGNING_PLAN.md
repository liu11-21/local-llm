# Release signing implementation plan

已實作候選階段：GitHub-hosted Windows、固定 Actions SHA、npm／Cargo／Python 鎖檔、unsigned NSIS、SBOM 原始 Notices 隨安裝、安裝後 PE／uninstaller 清單、完整 build identity、SHA-256、升級／解除安裝、GitHub provenance。公開建置成功不代表法律審核或 SignPath 核准。

`.github/workflows/signing-review.yml` 只有 workflow_dispatch，job 使用 literal false，無 secrets、無服務呼叫。`signpath/signing-request-step.yml.example` 是非執行範例，所有必要值空白；不會被一般 push／PR 觸發。這不是已運作的正式簽章管線。

未來啟用前必須：完成權利及第三方審查、決定同形式公開發行、Foundation 核准、全團隊 MFA、Authors／Reviewers／Approvers、審查強制規則、受保護的 release-signing 環境、SignPath App 與 branch／workflow／runner policies。這些設定本輪均未擅自啟用。

正式設計應由獨立、人工啟動的受保護 release workflow 在固定來源 SHA 上建置／驗證，先上傳 unsigned artifact，再將該 upload 的 artifact-id 傳給核准 action；全部前置 jobs 使用 GitHub-hosted Runner。若跨 workflow 選取既有 candidate，需先確認平台 origin／artifact ID 驗證，不可用任意重上傳規避來源鏈。範例僅示意 request step，並非完整可投入生產流程。

上游 `signpath/github-action-submit-signing-request` 已核對 v3 的 Commit f6d04783b4569d051e0c80105fe66e82819d0092。固定頂層 Action SHA 不代表已審查所有嵌入／轉引工具；啟用前需再次審閱並由 Approver 確認 policy 不允許自動核准。

installer／uninstaller 需先決定 Tauri NSIS 模板的嵌套簽署順序與供應者可接受的 artifact 設定，不在 Windows CI 中臨時塞假 SignTool。簽後重新校驗每個被更改的 PE 與 installer hash；驗證上游檔案未被重簽、版本一致、安裝／升級／解除安裝正常。保留原始 unsigned 候選與簽章稽核鏈。

正式發行將是另一次維護者核准；此輪無 Release、Tag、對外申請或正式簽章請求。官方：[SignPath GitHub integration](https://docs.signpath.io/trusted-build-systems/github)、[GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)。
