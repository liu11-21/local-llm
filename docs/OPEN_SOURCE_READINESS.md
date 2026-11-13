# Open-source readiness — 0.7.0 Development

MIT：**第一方已正式採用**；維護者於本次集中詢問後另行批准 A1–A4，署名「Copyright (c) 2026 劉仲軒」。
維護者主導需求與產品架構，主要透過 Codex／AI 輔助產生及修改程式碼；不宣稱全部 AI 輸出都有著作權或絕對無第三方。
Logo／品牌／UI 截圖及合成媒體暫時排除。SignPath：**未申請／未核准**；Windows：**unsigned review candidate**。
[現行範圍](../LICENSE_SCOPE.md) · [來源](MAINTAINER_PROVENANCE.md) · [核准紀錄](MIT_FINAL_APPROVAL_CHECKLIST.md)。

| 階段 | 交付及驗證 | 判定 |
|---|---|---|
| A 原始權利 | 沿用逐檔 inventory，增加維護者陳述與人工分類 overlay | 未見具體衝突；A1–A4 已確認／批准，資產獨立；不重掃歷史 |
| B 依賴 | npm／Cargo 全鎖、Python／審查工具、Runtime／模型 manifest、SPDX 2.3／原始 Notice | 掃描完成不等於法律批准；未知保持 REVIEW REQUIRED |
| C MIT | 正式 OSI MIT／劉仲軒、LICENSE_STATUS 歷史、LICENSE_SCOPE 與採用紀錄 | 已採用第一方 MIT；第三方保持原授權；資產另處理 |
| D 文件 | README、Contributing／Conduct／Security／Privacy／Building／Release／Signing | 已建立；私人聯絡／角色待維護者指定 |
| E SignPath | 14 項證據表、未送出申請草稿 | 5 PASS、7 REVIEW REQUIRED、0 BLOCKED、2 NOT VERIFIED |
| F 建置 | CI notices、PE inventory、provenance、SHA／版本、禁用簽章範例 | 候選驗證結果見本輪 evidence；非正式簽章管線 |
| G 公開秘密 | redacted reachable-history scan | 無已確認有效憑證；模式／圖片／二進位審查有明示限制 |
| H 驗收 | Python／Vite／Chromium／Windows Cargo與安裝CI／SBOM schema | 見 evidence/open-source/VALIDATION.md；未執行項目不宣稱通過 |

文件索引：[權利與授權](LICENSE_AUDIT.md)、[依賴義務](THIRD_PARTY_LICENSES.md)、[機器清單與原文](sbom/)、[SignPath 資格](SIGNPATH_ELIGIBILITY.md)、[申請草稿](SIGNPATH_APPLICATION_DRAFT.md)、[簽章政策](CODE_SIGNING_POLICY.md)、[發行規劃](RELEASE_SIGNING_PLAN.md)、[阻礙清單](OPEN_SOURCE_BLOCKERS.md)。

Windows 安裝包需包含所有應有原始 Notices，並保留 upstream PE 身分；本輪增加獨立 notices resource，修正舊版遞迴重簽風險。缺失的上游著作權 Notice／Covered Source 或 Microsoft 分發證據必須在對應二進位正式發行／申請前補齊；不再擱置已批准的第一方 MIT 決策。不能用把整包命名 MIT 的方式通過。

本輪公開 [Windows Run 43409624156](https://github.com/liu11-21/local-llm/actions/runs/43409624156) 全通過，來源 12869bc64cedea0a7a8d562da30384223ed2e531；候選下載後的 SHA、72 PE、SPDX／Notices 與 GitHub 來源證明均已獨立核對。[完整驗收與原始證據](evidence/open-source/VALIDATION.md) · [實際 CI Notices](evidence/open-source/CI_NOTICES.md)。Worker PE FileVersion 尚未提供，正式簽章範圍與 metadata 仍需確認。版本仍為 0.7.0 Development，沒有新增正式 Release 或簽章請求。

上述 Run 是前輪既有證據；本輪 d74bb27 上的授權變更不會重寫其安裝包或證明。
本輪只更新授權／封裝 metadata 與文件，執行本地授權封裝、schema／Notice 完整性及既有測試驗證。
既有完整 Windows workflow 會重新 collect 全部依賴，為遵守本輪「不重盤 641 項」限制，本次提交使用
[skip ci]，不重跑整條 Windows CI、不修改 workflow；本次沒有新 Windows 安裝包驗收結果。
正式簽章仍待 Foundation 答覆。[未寄出的英文詢問](SIGNPATH_APPLICATION_DRAFT.md#unsent-english-inquiry)。
