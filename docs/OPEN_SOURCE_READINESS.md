# Open-source readiness — 0.7.0 Development

MIT：**候選，未採用**。SignPath：**未申請／未核准**。Windows：**unsigned review candidate**。維護者指定署名「劉仲軒」，其餘權利待確認；MFA／審查與簽章角色未定。

| 階段 | 交付及驗證 | 判定 |
|---|---|---|
| A 原始權利 | source_audit.py、逐檔來源／hash／作者觀察／未知點、歷史掃描 | 工具及清單可交付；權利仍待確認 |
| B 依賴 | npm／Cargo 全鎖、Python／審查工具、Runtime／模型 manifest、SPDX 2.3／原始 Notice | 掃描完成不等於法律批准；未知保持 REVIEW REQUIRED |
| C MIT | 根狀態 LICENSE、OSI 候選原文／劉仲軒 | 未正式重新授權；第三方聲明保持原授權 |
| D 文件 | README、Contributing／Conduct／Security／Privacy／Building／Release／Signing | 已建立；私人聯絡／角色待維護者指定 |
| E SignPath | 14 項證據表、未送出申請草稿 | 4 PASS、7 REVIEW REQUIRED、1 BLOCKED、2 NOT VERIFIED |
| F 建置 | CI notices、PE inventory、provenance、SHA／版本、禁用簽章範例 | 候選驗證結果見本輪 evidence；非正式簽章管線 |
| G 公開秘密 | redacted reachable-history scan | 無已確認有效憑證；模式／圖片／二進位審查有明示限制 |
| H 驗收 | Python／Vite／Chromium／Windows Cargo與安裝CI／SBOM schema | 見 evidence/open-source/VALIDATION.md；未執行項目不宣稱通過 |

文件索引：[權利與授權](LICENSE_AUDIT.md)、[依賴義務](THIRD_PARTY_LICENSES.md)、[機器清單與原文](sbom/)、[SignPath 資格](SIGNPATH_ELIGIBILITY.md)、[申請草稿](SIGNPATH_APPLICATION_DRAFT.md)、[簽章政策](CODE_SIGNING_POLICY.md)、[發行規劃](RELEASE_SIGNING_PLAN.md)、[阻礙清單](OPEN_SOURCE_BLOCKERS.md)。

Windows 安裝包需包含所有應有原始 Notices，並保留 upstream PE 身分；本輪增加獨立 notices resource，修正舊版遞迴重簽風險。缺失的上游著作權 Notice／Covered Source 或 Microsoft 分發證據必須在正式採用／申請前補齊。不能用把整包命名 MIT 的方式通過。

本輪公開 [Windows Run 43409624156](https://github.com/liu11-21/local-llm/actions/runs/43409624156) 全通過，來源 12869bc64cedea0a7a8d562da30384223ed2e531；候選下載後的 SHA、72 PE、SPDX／Notices 與 GitHub 來源證明均已獨立核對。[完整驗收與原始證據](evidence/open-source/VALIDATION.md) · [實際 CI Notices](evidence/open-source/CI_NOTICES.md)。Worker PE FileVersion 尚未提供，正式簽章範圍與 metadata 仍需確認。版本仍為 0.7.0 Development，沒有新增正式 Release 或簽章請求。
