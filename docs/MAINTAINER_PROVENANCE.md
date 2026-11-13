# Maintainer provenance — 第一方 MIT 已採用

2026-11-13；分支 dev/desktop-workspace；審查基準 84a3af433c94752c3bfb06e73377c8bc37d92e2b，版本 0.7.0 Development。本輪沿用既有 698 檔清單與授權證據，沒有重掃 Git 歷史或重新盤點 641 個依賴。這是來源與範圍判定，不是正式授權或權利保證。

## 2026-11-13 正式採用補充（優先於下列歷史待決狀態）

本次來源基準 d74bb27。維護者另外明確確認 A1–A4：無其他需同意的權利人；
個人 Codex／OpenAI 帳號，所知程式均透過 Codex 生成，沒有新增已知輸入例外；
批准明定的第一方程式／測試／建置／技術文件範圍及排除，並同意正式 MIT 署名
「Copyright (c) 2026 劉仲軒」。回覆原文及問題範圍見
[核准紀錄](MIT_FINAL_APPROVAL_CHECKLIST.md)。這不是逐行著作權或絕對無第三方保證。

現行範圍見 [LICENSE_SCOPE.md](../LICENSE_SCOPE.md)。Logo／品牌／UI 截圖及合成媒體檔
仍排除；不因資產未決而擱置已批准程式碼的 MIT。以下舊審查陳述及來源欄保留歷史，
「候選／待採用」不再代表現行程式授權；Logo／發行／SignPath 待決事項仍有效。
本輪不再重做來源歷史、LocModel 或依賴盤點。僅在發現具體新來源例外時重開該範圍。

## 維護者已提供的事實

第一方程式碼來源描述：**「維護者主導需求與產品架構，主要透過 Codex／AI 輔助產生及修改程式碼。」**

維護者提出產品構想、需求及方向，進行選擇、修改方向與整合；Logo 主要使用 AI 生成；候選 MIT 署名為「劉仲軒」。正式 MIT 採用、資產授權範圍與 SignPath 核准均尚未完成。以上是維護者陳述的紀錄；不等於逐行確認人類著作、不等於全部內容原創，也不將 Codex 或 Git 提交名稱當成法律上的著作權人。

| 分類 | 目前依據 | 判定與界線 |
|---|---|---|
| 人類需求、選擇及整合 | 維護者本輪陳述、現有需求與已整合程式 | VERIFIED：陳述及專案結果存在。哪些具體表達達到著作權門檻未個別認定；構想本身不等於整份程式的著作權 |
| AI 輔助第一方程式 | 維護者陳述、既有 inventory 中 Codex／liu11-21 提交紀錄 | VERIFIED：以此描述開發來源；MAINTAINER CONFIRMATION：帳號／合約主體、已知輸入與引用及最終授權範圍 |
| 第三方來源 | 已有 third_party、SBOM、Notices、套件／Runtime／模型來源 | VERIFIED：第三方內容確實存在，保留原授權；不因 AI 協助而變成第一方 |
| Logo／截圖及其他素材 | 目前檔案、維護者 AI 生成陳述、fixture generator | 個別處理，見下表；不能從來源敘述直接批准所有素材 MIT |

本輪對現有第一方原始碼的來源／copyright／SPDX／copied-from 標示做有限檢查，並核對舊 inventory 的提交名稱。未見另列獨立人類貢獻者、明確未授權複製片段或足以要求整個第一方程式改採不相容授權的具體證據。已知 upstream 內容仍存在且另受授權規範。這不是全面程式相似度鑑識，不能證明沒有未標示引用。先前以 LocModel 為功能參考、以 Tesla 為視覺方向的要求，不直接證明複製其程式／美術，也不授予其權利；若實際貼入外部片段或素材，需維護者補列。

### LocModel 專項覆核補充（2026-11-13）

維護者說明，發想源於使用 LocModel 時的啟動、環境配置及跨應用整合痛點，希望建立獨立工作台。這是新增的背景來源陳述，不把構想相似寫成程式碼或美術授權。

[專項報告](LOCMODEL_PROVENANCE_AUDIT.md) 以 a47ab25 為基準，查核 124 個本地可達提交、1,326 文字 blob／691 程式碼版本，對官方樣本提取的 23 個資源及官網 4 個檔案做身分／詞法與 JS／TS 形狀檢索，沒有找到完整檔案相同或達到本輪門檻的片段候選；圖像及選定 UI 頁未識別具體複製。結論為 **NO ISSUE IDENTIFIED：目前沒有新增足以實質阻擋第一方採 MIT 的 LocModel 來源問題**。

已知曾研究並取得 LocModel 交付資源，故不能宣稱嚴格 clean-room 或從未接觸。LocModel 官方完整原碼庫／OSI 授權未確認、未取得的後端與其他版本、未保存對話／輸入及轉化相似保持 **NOT VERIFIED**，不冒充已排除；也不因此要求為不存在具體指認的內容先取得概括許可。原本的 MIT 最終批准及第三方義務仍各自保留，本補充不是授權採用。

## AI 使用條款與人類創作的不同問題

依 [智慧局 AI 圖畫解釋](https://www.tipo.gov.tw/tw/copyright/692-34252.html)，AI 輔助中有無實際人類創意會影響保護；不能把此判準機械地變成「無法逐行舉證即侵權」。[著作權法第 10 條之 1](https://www.tipo.gov.tw/tw/copyright/694-17731.html) 區分構想與表達。對程式的本輪結論是：**沒有已識別的具體第一方 MIT 衝突；可進入範圍與採用決策**。這是依目前證據的審查推論，並非判決其所有部分必受保護或保證不侵權。

若適用 [OpenAI 個人使用條款](https://openai.com/policies/row-terms-of-use/) 或 [Services Agreement §4](https://openai.com/policies/services-agreement/)，Output 的合約歸屬受適用法律及合約主體限制，不會排除第三方權利。[Service Terms 的 Codex and Code Generation](https://openai.com/policies/service-terms/) 明示產碼可能涉及第三方授權。維護者需確認實際使用帳號是本人或代表公司／雇主，以及有無已知外部程式／參考素材輸入或引用提示。

查閱日為 2026-11-13：個人條款頁標示生效 2026-01-01，Services Agreement 頁標示更新 2025-12-01，Service Terms 頁標示更新 2026-11-12。舊 Logo 的庫內首次紀錄早於最新 Service Terms；目前條款不能直接當成當時合約版本的證明。沒有證據辨識舊 Logo 的實際服務、模型、方案或生成日，不把它猜成 DALL·E、ChatGPT Images 或其他特定服務。依維護者後續要求，本輪另用目前可用的 OpenAI 內建工具生成一個新候選；它的來源可記錄，仍不推定帳號合約主體或法定著作權，見下文。

MIT 若日後正式採用，僅授權維護者依法能授權的權利；無著作權的部分不會因版權列或 MIT 而產生新的專有權利，第三方內容也不會被重新授權。候選版權署名不是「所有輸出均為人類創作」的聲明。

## Logo／Icon／素材核對

| 檔案／群組 | 技術來源及實際散布 | 尚待處理 |
|---|---|---|
| logo.png、desktop/src/logo.png、docs/logo.png | 三份 512×512 PNG 相同，SHA-256 01bc37f1f0cb7782e23365878edb8a8298adb6af89964daf8d24e4860426c057；PNG 無 metadata。desktop/src/App.tsx 匯入 UI，docs/index.html 用於 Pages；root PNG 也用於舊版封裝 | MAINTAINER CONFIRMATION：AI 生成服務／時間／方案、是否有參考圖及可散布條款 |
| logo.ico、desktop/src-tauri/icons/icon.ico | 兩份 ICO 相同，SHA-256 e797045d978c01dd6198bc33e2b5d628348a12369bb2477119df8de994b883eb；檔案只有尺寸資訊，最大 256×256。root ICO 為 Worker／舊版圖示；Tauri ICO 用於 shell／NSIS／捷徑 | 同一 Logo 決策涵蓋所有尺寸及副本；不是五個獨立權利來源 |
| legal/logo-candidate-v1.png（本輪新候選） | OpenAI 內建 image_gen.imagegen 生成／編修；1254×1254 RGB 白底 PNG；SHA-256 4aac92357a32875cd3f2f06089f3d839ad2e3dd69a674666c68d2676f6caaf16；沒有提供外部圖片或舊 Logo 作輸入 | VERIFIED：生成來源及輸入紀錄可核對；MAINTAINER CONFIRMATION：是否採用、合約主體／資產許可；未接入產品或聲稱商標權 |
| docs/ui-preview/ 的 75 張截圖 | 既有 UI／測試紀錄；可能含第一方 UI、upstream 圖示、模型輸出或測試畫面 | 暫不列入第一方程式碼 MIT 候選；逐張內容／個資及素材權利仍待需要時確認；Workspace 安裝來源未引用此目錄 |
| desktop/tests/media-fixtures/sample.png／sample.webm／sample.flac | generate.py 直接產生純色、色塊與正弦波；不載入外部圖片／音樂，不經 AI 模型。這能佐證測試素材來源，不自動證明簡單輸出有著作權 | 可提出納入測試資產範圍的候選，仍由維護者批准；編碼函式庫條款另存。測試目錄不在 release resources |
| Lucide 等 UI 圖示、Runtime 內素材、模型／使用者作品 | upstream 套件或使用者內容；不屬上述自有 Logo | 保留各自授權，不整包改 MIT；C／D 類內容不因顯示於工作台就取得第一方地位 |

Logo 最早新增的既有紀錄是 bd6c93790c0c7ed2c1924e72e29da2a0b733f650（2026-11-08）；這是匯入庫的日期，不是已證實生成日期。目視檢查 PNG 與 ICO 為黑底、白色幾何 L 形及紅斜條；未識別到直接貼入 Tesla T、文字商標或其他已辨識品牌圖案的明確證據。這是有限目視結論，**未做商標資料庫／跨市場近似檢索，不能保證不近似或宣稱已取得商標權**。配色／斜線或「科技風」本身不提供品牌權利的結論。

實際 Workspace 圖片散布依 App.tsx、Tauri tauri.conf.json 與 build_desktop_worker.py 的現有引用判定：Logo PNG 隨 UI，ICO 作為執行檔／安裝程式圖示；docs/logo.png 為 Pages，截圖與 media-fixtures 未被 release resources 引用。動態生成／下載作品是執行時內容。此輪未重建或宣稱完整重列第三方工具鏈內所有圖像。

**建議方案（未採用）：** 來源／輸入權利確認後，可將選定 Logo 及其產品副本另列為允許隨軟體重製與修改的 MIT 資產，並在獨立品牌政策中處理不得誤導官方背書等商標事項；不能透過品牌政策收回已授予的程式碼 MIT 權利。另一方案是選擇清楚的獨立素材授權，並另確認 SignPath 接受度。未決定前 Logo 排除於本次「程式碼 MIT」候選；這不表示已授予 Logo 使用權，也不認定它侵權。因現有 Logo 已在安裝包內，正式二進位發行前須完成這項決定，或另行批准可合法散布的替代素材；本輪只增加新候選，不替換產品圖示、不宣稱商標已註冊。

### 本輪新 Logo 候選的可核對來源

維護者補充要求由本服務生成後，使用 OpenAI 內建圖像工具製作新候選，另存 [候選圖](legal/logo-candidate-v1.png) 與 [完整三步提示詞／來源紀錄](legal/logo-candidate-v1.provenance.json)。第一步為純文字生成；後兩步僅以本輪自身生成圖作編修目標，清除光暈、調整成可清楚審核的白底幾何圖。沒有提供第三方圖片、舊 Logo 或品牌圖作輸入；不能因此保證模型訓練素材或輸出完全不涉及第三方。工具未公開底層模型型號，紀錄如實標示未提供，不猜測型號。

最終候選為兩個錯位開口框與紅色中心方塊。已目視確認無文字／可見商標符號，仍非商標近似檢索或權利保證。這個「已知本輪服務與輸入」的選項，可在批准後用來取代追補舊 Logo 生成紀錄；替換產品 PNG／ICO、決定資產授權與建置驗證是另一步。本輪只增加候選圖，五個既有產品 Logo 全部保持原位元組。候選不是已採用 Logo，也未被正式 MIT 授權。

## 尚需維護者執行的事項

A1–A4 已確認及批准，不再反覆詢問。若日後知道具體外部來源或權利例外，請補列受影響內容。
Logo／品牌／截圖與測試媒體的授權選擇維持獨立待辦，現有產品圖未改。
SignPath 的 MFA、角色、保護及每次人工簽章核准仍需實際人員操作；本次 MIT 決策不代替那些步驟。
