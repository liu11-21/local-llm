# MIT final approval — adopted, scoped first-party code

2026-11-13；版本 0.7.0 Development；批准的來源基準
`d74bb27f7cba65c0bb291e0a50a5fc143fef4062`。本輪任務提示本身沒有被視為批准；
以下採用依據是維護者對集中核准問題的另一次明確回覆。

## A1–A4 實際核准紀錄

維護者原文：**「a1:沒有 a2是，目前都是codex生成的 a3:是   a4 ，同意」**。
原問題及回答的範圍整理如下；不將此陳述擴張為全面無侵權保證。

- [x] **A1 權利主體 — MAINTAINER CONFIRMATION / 已確認。** 問題為是否有需另行同意的雇主、共同開發者、外包者或出資者權利；維護者答「沒有」。不據此認定每行 AI 輸出均有著作權。
- [x] **A2 已知第三方輸入 — MAINTAINER CONFIRMATION / 已確認。** 問題明列個人 Codex／OpenAI 帳號與合約、已記錄依賴／LocModel 靈感／另處理素材，以及是否有其他已知未處理輸入；維護者答「是，目前都是codex生成的」。據此記錄個人帳號及所知開發來源，沒有新增例外；不把它解釋為第三方依賴消失或 AI 輸出自動無第三方權利。
- [x] **A3 授權範圍 — MAINTAINER CONFIRMATION / 已批准。** 第一方 Python／TypeScript／React／CSS／Rust、測試、建置與維護腳本及技術文件採 MIT。第三方元件、Runtime、模型維持原授權；Logo／品牌素材／UI 截圖及合成媒體檔暫時排除。fixture generator 程式屬第一方 MIT。Logo 的後續選擇不再阻擋程式碼 MIT。
- [x] **A4 正式採用 — MAINTAINER CONFIRMATION / 已批准。** 維護者明確同意在上述來源與範圍正式採用標準 OSI MIT，署名 **Copyright (c) 2026 劉仲軒**，同步必要授權 metadata。

獨立採用 Commit：`fae698d30a82340a04384571575fc440679b01e2`。

現行許可：[根 LICENSE](../LICENSE)；適用邊界：[LICENSE_SCOPE.md](../LICENSE_SCOPE.md)。
原狀態聲明完整保留於 [LICENSE_STATUS.md](../LICENSE_STATUS.md)。
核准是範圍明確的維護者授權決策，不是 SignPath、第三方權利人或法院的核准。

## 採用完成項目

- 根 LICENSE 使用 OSI MIT 許可／免責原文，只代入指定署名、正規化引號／換行，不另加限制。
- README、Contributing、npm package 與鎖檔自己的根 package、Cargo package、Notices 產生器同步第一方 MIT。
- 現行 SBOM 僅更新 Workspace 的宣告與採用 overlay；641 項第三方元件、原授權／Notice／hash 及依賴圖保持，不重做盤點。`licenseConcluded` 仍保留 NOASSERTION，避免把宣告當成所有元件的法律結論。
- 來源 inventory 僅增加本次採用紀錄；原 head／逐檔來源與權利觀察保留歷史語義，沒有新歷史掃描。
- 過去 `docs/evidence/open-source/CI-*`、BUILD、簽章／來源證明及驗收結果保持原始 bytes。舊安裝包仍是當時的授權狀態，不因新文件而被重寫。
- 下一次建置的 Notices 帶入正式 LICENSE、LICENSE_SCOPE、歷史狀態；不再把候選模板作現行許可散布。

## 收斂後的結論

| 問題 | 狀態 | 結論 |
|---|---|---|
| 第一方 MIT 的具體阻礙 | VERIFIED | 既有審查未識別具體衝突；A1–A4 已取得明確確認及批准，第一方 MIT 已採用。非絕對無侵權保證 |
| 第三方發行義務 | EXTERNAL REVIEW | 實際 Windows payload 的 Notice／MPL Covered Source／Python 與工具鏈子元件／Microsoft 再散布證據仍需完成；不阻擋本次第一方許可決策 |
| Logo 與資產 | MAINTAINER CONFIRMATION | 暫時排除，沒有替換產品 Logo、批准素材授權或宣稱商標權；仍是整包正式發行／SignPath 的待辦 |
| MIT 正式生效 | VERIFIED | 已依獨立回覆批准並落地；不影響 main、Stable v0.6.2 或重授權第三方 |
| SignPath | EXTERNAL REVIEW | 未申請／未獲准；維持獨立的 MFA、角色、產物及資格核准流程 |

## 驗證與後續

本次授權為獨立提交；檢查 MIT 正文、scope 與 metadata、SBOM 官方 schema／Notice
hash、全數第三方與歷史證據不變，以及 Notices 封裝與既有單元測試。
既有完整 Windows workflow 會重新 collect 全部依賴；為遵守本輪不重新盤點 641 項的限制，
本次使用 [skip ci]，保留 workflow 不變，執行本地必要驗證，不宣稱新的 Windows 安裝驗收結果。

不重掃 Git 全歷史、不重做 LocModel 或 641 依賴盤點，不建立 Release／Tag、寄信、
提交申請或修改帳號／Windows 安全設定。下一步見
[SignPath 資格表](SIGNPATH_ELIGIBILITY.md)、[未寄出的詢問](SIGNPATH_APPLICATION_DRAFT.md#unsent-english-inquiry)。

2026-11-13 實際必要驗證：MIT 正文與歷史狀態、694 個未修改保護檔、641 項第三方完整紀錄、
SPDX 第三方 packages／relationships、來源 inventory 原欄位、npm 第三方鎖檔、14 項表與文件連結均通過。
授權測試 6 項、Notices prepare／schema／原文 SHA、0.7.0 版本檢查與 TypeScript／Vite build 通過；
Vite 僅有既有 bundle-size 建議警告。無新 Windows 安裝包結果。
[本輪機器驗證紀錄](evidence/open-source/mit-adoption-validation.json)。
