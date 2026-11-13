# MIT final approval checklist — 未批准

2026-11-13；審查基準 84a3af4；0.7.0 Development。本文件是可審核的決策包，**不是使用者已批准的證明**。根 LICENSE 保持原有狀態聲明；沒有將 MIT 原文作現行授權，metadata／SBOM 也沒有改成 MIT。

## 狀態定義與五個結論

VERIFIED＝所述證據／有限檢查已核對，不是全面法律保證；MAINTAINER CONFIRMATION＝需維護者確認事實或決策；EXTERNAL REVIEW＝需第三方條款、Foundation 或個案專業判斷；BLOCKED＝目前不能執行的具體動作。

| 問題 | 狀態 | 最終審查結論 |
|---|---|---|
| 1. 有具體證據阻止第一方採 MIT 嗎？ | VERIFIED | 現有證據未識別出此種衝突；AI 輔助本身、沒有逐行人類創作證明，不是已證實侵權。合約主體／輸入／範圍仍需維護者確認，亦不保證每部分有著作權 |
| 2. 哪些第三方問題仍阻擋發行批准？ | EXTERNAL REVIEW | 對實際散布內容完成 Notice／MPL Covered Source、Python／工具鏈／Microsoft 再散布證據；下載 Runtime／模型依其條款處理。這是尚未完成的放行條件，不是已證實整個第一方須改 GPL；非 Windows／build-only 項目需先確認散布範圍 |
| 3. Logo 如何處理？ | MAINTAINER CONFIRMATION | 舊 Logo 來源細節待確認；本輪另生成 OpenAI 候選並保存提示詞／hash，沒有提供外部圖片輸入。先選用哪個資產與許可，再另行接入產品；不宣稱取得商標權 |
| 4. MIT 生效前還需何確認？ | BLOCKED | 尚缺維護者對下面 A1–A4 的最終確認／批准。禁止僅因來源紀錄更新就把候選模板覆蓋 root LICENSE |
| 5. SignPath 還缺何外部核准？ | EXTERNAL REVIEW | Foundation 對 AI 來源／單人角色／混合二進位／下載 Runtime、模型及既有發行形式的答覆與正式接受；帳號 MFA／保護由維護者設定，不能用本報告代替 |

## 第一方 MIT 候選範圍

| 候選範圍 | 例示／限制 |
|---|---|
| 第一方應用及測試程式 | 根目錄自有 Python、desktop/src 的 TS／TSX／CSS、desktop/src-tauri/src／build.rs、docs 中的第一方網頁 HTML／CSS／mjs、第一方測試及 fixture generator |
| 第一方建置與維護程式 | 自有 cmd／ps1／iss、GitHub workflows、設定及 manifest 中依法可授權的自有部分；鎖檔中的 upstream 版本／license 資料保持原意 |
| 第一方技術文件 | 維護者有權釋出的自撰／AI 輔助敘述；不包含嵌入的 upstream 授權原文、受引用內容或另有授權的資料 |
| 可另選的合成測試媒體 | sample.png／webm／flac 有 generate.py 的來源依據；是否納入需 A3，不能因此宣稱純色／音調必有專有著作權 |

以上均以維護者依法可授權的權利（如有）為限。AI 輔助成分不整體排除，也不假定全部具完整人類著作權。具名第三方片段或檔案的原授權優先，不因放在第一方資料夾而變成 MIT。

明確排除：third_party 原聲明、npm／Cargo／Python 及其 runtime、docs/sbom 的 upstream 原文與 SPDX schema、docs/evidence 的原始 upstream Notice／外部證據資料、各模型權重與模型卡／條款、下載 ComfyUI／OpenVINO／llama.cpp／CUDA 等、使用者資料及作品。SPDX metadata 的 CC0／schema 的 CC-BY 等獨立規則保持。舊 Logo／Icon 五個檔、新 Logo 候選及 docs/ui-preview 截圖目前另列待決，不在程式碼 MIT 候選裡。

## 維護者最終核准欄（目前全部未勾選）

- [ ] **A1 權限主體：** 確認本人可處分本輪第一方範圍的相關權利；列出任何雇用、出資、外包或其他作者例外。這不是確認 AI 每一行都有著作權。
- [ ] **A2 已知第三方輸入：** 確認所知的複製片段、引用提示、參考素材與 AI 使用帳號／適用合約；有例外則附來源、授權及處置，不要求不可能的絕對無侵權保證。
- [ ] **A3 範圍與資產：** 批准上表的程式／文件範圍及排除；決定合成測試媒體與 Logo 的明確授權方案。程式碼可獨立作決策，二進位發行仍須合法 Logo 方案。
- [ ] **A4 正式採用：** 明確批准用「劉仲軒」作候選版權署名，並在上述範圍正式採用未加限制的 OSI MIT；指定最終採用的來源 Commit。提供姓名或表示 AI 輔助開發不等於這一項批准。

第三方發行與 SignPath 是另外的 gate：A1–A4 通過不會把所有第三方變成 MIT，也不會自動取得 SignPath 憑證。若出現具體無權轉授內容，先限制在該檔／元件處理，不把整份 AI 輔助專案一律判為侵權。

## 候選改動如何落地（未執行）

1. 根目錄新建的 LICENSE_STATUS.md 是目前狀態的候選保存位置。正式採用時將舊狀態標成歷史，記錄核准範圍／日期／Commit；現在 root LICENSE 完全未替換。
2. 採用時 root LICENSE 應只放 docs/legal/LICENSE-MIT.candidate.txt 的 BEGIN／END 標記間正文，移除候選說明與標記；候選包含署名「劉仲軒」。以 [OSI 官方](https://opensource.org/license/mit) 為準，只進行換行及引號的排版正規化，不加額外限制。
3. 保留獨立範圍說明、THIRD_PARTY_LICENSES、原始 copyright／Notices。資產與商標政策放在獨立文件，不能偷偷改 MIT 的許可。
4. 另一次獲准的授權採用提交才同步 README／package／Cargo／SBOM 與實際發行包。該提交涉及發行 metadata／建置，再執行相應建置驗證；本輪不做此步。

## 本輪必要驗證

確認 root LICENSE 及 Logo bytes 未變、全部既有 inventory 的 path／hash／作者／來源 Commit 欄位保持原值、只增加來源判定；原依賴清單、鎖檔、第三方原文、產品碼與 workflows 未變。檢查 JSON、文件相對連結、MIT 候選正文與官方文字、14 項表及五題狀態。來源 inventory 的 head 仍是舊快照，review_overlay 記錄本輪基準，不能當作新掃描。

本輪為文件／審核用新圖提交，沒有接入新產品資產；使用 GitHub 支援的 [skip ci] 提交標記，依要求不重跑 Windows CI，也不重新設計 CI。這不會替日後修改產品、替換正式 Logo 或正式授權的提交省略必要驗證。[GitHub 說明](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs)。

2026-11-13 必要驗證結果：

| 檢查 | 結果 |
|---|---|
| root LICENSE、5 個產品 Logo、依賴清單／鎖檔及原始 llama.cpp Notice | 12 個保護檔 hash 全部未變；只新增獨立審核圖 |
| 既有來源 inventory | 698 檔 path／SHA／觀察作者／首次 Commit／宣告／保留原授權欄位保持；326 個 upstream 原文／schema 的全部既有欄位保持；增加人工分類及 review_overlay |
| 候選 MIT | 直接取得 OSI 官方頁，比對許可／免責正文通過，僅正規化空白／引號；候選 Copyright 2026 劉仲軒；狀態搬移預覽與原 root LICENSE 文字一致 |
| 五題與最終核准 | 五題狀態完整；A1–A4 均未勾選，不把來源說明或生成 Logo 當批准 |
| SignPath | 保留 14 項與 4 PASS／7 REVIEW REQUIRED／1 BLOCKED／2 NOT VERIFIED；英文詢問未寄 |
| JSON／相對文件連結／新 Logo | 語法與連結通過；候選 SHA、尺寸及三步生成／編修輸入 hash 鏈通過 |
| 變更界線 | 文件與未接入產品的審核圖；產品碼、建置、workflows、main 與 upstream 原文未變 |
| 本輪不執行 | Git 全歷史重掃、641 依賴重盤、Windows CI、Release／Tag、SignPath 申請、帳號／Windows 安全設定 |
