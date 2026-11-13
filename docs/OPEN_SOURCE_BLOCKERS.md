# MIT 決策與發行的具體缺口

2026-11-13；MIT 採用來源基準 d74bb27，既有來源審查基準 84a3af4；本輪不重掃。**沒有已識別的具體第一方不相容授權或未授權複製證據。** 維護者主導需求、選擇及整合，主要透過 Codex／AI 輔助產碼；不再以「無法逐行證明人類創作」當作全面阻擋。有限證據未識別不等於保證完全不存在第三方。

| ID | 狀態 | 真正待決的問題 | 阻擋的動作／責任 |
|---|---|---|---|
| C1 | VERIFIED | 維護者另確認 A1／A2：無其他需同意權利人；個人 Codex／OpenAI 帳號、所知均 Codex 生成，未新增已知輸入例外 | 依維護者陳述結案，不推論絕對無第三方；有具體新例外再按範圍處理 |
| C2 | VERIFIED | A3／A4 已明確批准第一方範圍、排除、署名及正式 MIT | 根 LICENSE 已採用 MIT，scope／metadata／SBOM 自有宣告已同步；不再阻擋程式碼許可 |
| A1 | MAINTAINER CONFIRMATION | 選用有 OpenAI 工具／提示詞紀錄的新候選，或補齊舊 Logo 來源；決定資產許可及品牌政策 | 現有 Logo 已隨 binary／UI 散布；新候選未接入產品。正式二進位放行需合法資產方案，可獨立於程式碼 MIT 決策，不宣稱商標權 |
| T1 | EXTERNAL REVIEW | 對實際隨包散布的元件完成原 Notice／MPL Covered Source／工具鏈、Python 子元件及 Microsoft 再散布對應 | 阻擋宣稱整包授權已全數放行；已保存 SBOM／325 原文仍不代表義務全履行。build-only／其他平台缺口不可直接推定都是 Windows 違規 |
| T2 | EXTERNAL REVIEW | Comfy portable、CUDA／Torch／FFmpeg、OpenVINO、CDN 與模型的各自條款／來源 | 對應 Runtime／模型下載與再散布需個別結案；不把 C／D 類權重改 MIT，不因此一律否定第一方程式碼 |
| S1 | EXTERNAL REVIEW | Foundation 對 AI 輔助來源、單人兼任角色、Rust 靜態碼／Worker bootloader／NSIS uninstaller 的接受度 | 簽章資格與可簽清單需書面答覆；Worker 缺 PE FileVersion 須補齊／確認規則；不重簽 upstream DLL／PYD |
| S2 | MAINTAINER CONFIRMATION | MFA、實際角色、分支／環境保護及私人安全受理人 | 維護者自行設定並保留證據；本輪未更動帳號／規則，步驟見 CODE_SIGNING_POLICY.md |
| S3 | EXTERNAL REVIEW | Actions artifact 是否符合對應形式發行；更新／第三方 telemetry 的告知與可停用要求；下載 Runtime／模型影響 | 需 Foundation 審閱；未寄出英文草稿見 SIGNPATH_APPLICATION_DRAFT.md |
| P1 | MAINTAINER CONFIRMATION | 舊證據的兩筆 user-path metadata 與截圖／對話的隱私人工複核 | 沿用既有位置報告，不重掃歷史或輸出值；沒有已確認有效憑證事件，不擅自改寫歷史 |

第三方、素材及 SignPath 是獨立 gate；不會因第一方來源有說明就自動批准，也不把每個未知都提升為已證實法律衝突。若日後有具體侵權或有效憑證事件，依受影響檔案／元件縮小處理範圍，必要時停止發行、輪替並依 SECURITY.md 處置。

A1–A4 已結案，原回覆見 [核准清單](MIT_FINAL_APPROVAL_CHECKLIST.md)。本次是獨立第一方授權提交，
不是整包發行／SignPath 核准。main、Stable v0.6.2、產品功能、Logo、第三方原文、依賴圖及 CI 配置未變；
未建立 Release／Tag、提交申請或改帳號設定。
