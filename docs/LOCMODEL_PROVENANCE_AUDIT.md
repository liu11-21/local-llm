# LocModel 來源與具體表達相似性專項審查

日期：2026-11-13（Asia/Taipei）。Local LLM 基準：dev/desktop-workspace，**a47ab25ab0e96c8f1829b2fda029c7865e6d21f5**，0.7.0 Development。本輪只讀來源並更新三份審查文件，未修改產品、UI、Logo、依賴、授權原文或 CI，未正式採用 MIT。

**NO ISSUE IDENTIFIED：在以下已檢查範圍，未發現足以實質阻擋 Local LLM 採 MIT 的 LocModel 來源問題。** 沒有找到直接複製檔案、達到本輪檢索條件的程式片段、相同參考素材，或明確移植其受保護表達的證據。此結論不等於所有部分絕對原創、全部歷史均可取得或法律上的無侵權保證；不能把資料不足的部分改標為已排除。

## 1. 狀態與判定方式

| 狀態 | 本報告意義 |
|---|---|
| VERIFIED | 有直接證據支持所述事實；不延伸為整體權利保證 |
| POTENTIAL ISSUE | 找到具體可疑相似性，尚需人工判斷；不是侵權結論 |
| NOT VERIFIED | 原碼、歷史、輸入或對照資料不足，不能確認 |
| NO ISSUE IDENTIFIED | 在明列的範圍／方法中，未識別具體問題 |

沒有把功能相同、使用側欄／聊天／模型卡或共享開源依賴直接當作複製證據。程式 token 與像素比對僅作檢索與人工覆核，不提供「侵權機率」。構想與具體表達的區分依 [智慧局第 10 條之 1 說明](https://www.tipo.gov.tw/tw/copyright/694-17731.html)；本專案的個案結論屬以下證據的有限審查推論。

## 2. 官方來源、版本及授權

| ID／狀態 | 來源／位置 | 結論與理由 |
|---|---|---|
| O1 VERIFIED | [官網](https://locmodel.com/)，擷取 HTML 行 5–8、665、682–685 | 官網識別產品為 LocModel，連出下載、terms／privacy 及自身前端腳本；不是第三方同名工具。當前官網標示版本 3.1.0 |
| O2 VERIFIED | [更新紀錄](https://locmodel.com/changelog.html)，行 153、254–256、336 | 記載 v2.1.0 為 2026-11-05、已歸檔；v3.1.0 為 2026-11-08。當前官網圖片不能逐張推定都是 3.1.0 製作版本 |
| O3 VERIFIED | [協議](https://locmodel.com/terms.html)，行 79–91，頁面更新 2026-11-10 | 自有軟體提供有限安裝／使用許可，第三方模型另受其條款約束；不是 LocModel 自有程式碼／美術的 MIT 複製改作授權。頁面自述提供者不等於本輪完成其法律身分核驗 |
| O4 NOT VERIFIED | 官網、協議、privacy、changelog、官網兩個 JS；公開 GitHub 名稱搜尋 | 未建立官方網站到任何完整原始碼 Repository／OSI 授權的可信連結鏈。不能聲稱已確認所有可能原碼都未公開 |

GitHub 同名搜尋包括自述為「桌面重建項目」的 single2339/LocModel，以及 jaja1620 的 patch／MCP／injector、gzc184123/locmodel-catalog。**沒有官網連結證明它們是官方完整原碼**，沒有取得或執行其二進位，也沒有將其授權套給 LocModel。使用開源模型或 llama.cpp，也不能推導 LocModel 自有程式採 MIT。

協議提到對本服務的使用限制，不能直接解讀成任何獨立同類軟體皆侵權。本輪不認定維護者接受了哪一版協議，也不將 2026-11-10 條款倒推成較早行為的適用條款；歷史契約適用為 NOT VERIFIED，不是已證實的程式複製或新增 MIT 阻擋。

### 可比對樣本的身分

| 證據 | 本輪核對 |
|---|---|
| [官方 2.1.0 ZIP](https://locmodel.com/LocModel_2.1.0_x64-setup.zip) | 唯讀取得 5,483,830 bytes；SHA-256 d4c9615e846b8787334d8a65b2e7176a06df3b66dd14f08da8a966e50643b3bf，與既有留存 ZIP 完全相同；不是只用檔名／大小／ETag 推定 |
| ZIP 內安裝檔 | LocModel_2.1.0_x64-setup.exe，5,511,800 bytes；SHA-256 e2d98303d2fc15d2937db5782295542c1486113e6c8050d71414d8063321ce7b，與留存安裝檔相同；未執行或安裝 |
| 前次靜態提取的 LocModel.exe | SHA-256 3e0a470f801e94d9b66771f497e0fe4b92479c4949b4c28964089549108aa35b；前次 REA 證據 ev_58dc38fc465026bf06e569ea1e3bcd163f1be45ece081e76cd91d31bb772db64。此輪未重新解整個 NSIS payload；沿用該提取紀錄，不能把此步說成本輪新驗證的完整安裝解包鏈 |
| 已提取前端資源 | 依 asset-provenance.json 的 PE 位移與長度，重新讀取壓縮 bytes、Brotli 解壓並核對全部 **23 個資源**的壓縮／解壓 SHA 與留存檔相同；不執行 JS 或 PE |
| REA 靜態來源分析 | app.js／agent.js／chatmgr.js／markdown.js／imagegen.js 的驗證副本，共 262,942 bytes、5 個語法解析成功、0 parse failures；parent Evidence **ev_7e577d3c02317530ab8c70fdf46cc421508829ddec332a793c2e79f2a42a5a1c**；副本集 SHA-256 b22a353fea828bfcc7ac4f3b63a78c4dbfd9f5d423da7062ceea06322a820e31 |

交付包內可讀的 JS／CSS／HTML 是「交付的前端資源」，不等於官方公開、允許再散布的完整原始碼庫。REA 語意圖仍有 8,539 個保守未知點，未把語法解析成功當作全部行為或後端等價已驗證。完整本輪樣本與原文僅保留在 ignored build/locmodel-audit，不加入產品或提交官網／LocModel 的原始碼。

官方擷取定位用 SHA-256：首頁 18b1616c50455ba76184fab443ea9365ed7236d5850b078ff45d3f3a96f38ebe；協議 82b9b6bf0c9c925cb0a6897ae6c71bc9d65aa3b30c2facbaf81ee6bbe890fb38；changelog 51a546224386f08b0244ed97b05f190b53a9f25d645749c8440ccabbb5d35832。上述 HTML 行號對應本日取得的檔案，網站後續變更可能移位。

## 3. Local LLM Git 歷史與原始碼

查核全部本地可達 refs：main、dev/desktop-workspace、各自 origin tracking ref，以及既有 v0.2.0／v0.3.0／v0.4.0／v0.5.0／v0.6.0／v0.6.1／v0.6.2 七個 tags，共 11 refs；不是 shallow repository。共有 **124 個可達提交、1,326 個文字 blob、691 個程式碼版本 blob**，程式碼詞法檢索涵蓋 1,785,461 tokens；另有 93 個 binary blob 不當作文字解析，沒有超過 4 MiB 的 blob 因大小排除。本輪沒有建立或修改 tags。

| ID／狀態 | 檔案／Commit／比對位置 | 結論與理由 |
|---|---|---|
| G1 VERIFIED | 單一 root 90097a24a2e4b919dbf5a696b17162f9b159c631；app.py:1–22；[GitHub repo API](https://api.github.com/repos/liu11-21/local-llm) fork／parent／source | 初始提交是 Python／Tkinter Local LLM。GitHub fork=false，parent／source=null；只證明目前註冊關係與可達祖先，不排除未註冊手動複製 |
| G2 VERIFIED | aa97042 catalog.py；4530495 web_bridge.py；9f33317 desktop/src/App.tsx、desktop/src-tauri/src/main.rs | 可達歷史顯示由本地 Python 工具，逐步加入模型目錄、網頁橋接，再加入 Tauri 工作台；這是演進觀察，不是每行原創性的證明 |
| G3 NO ISSUE IDENTIFIED | 全部可達 commit message、路徑與文字 blob；唯一內容命中為 a47ab25 的 docs/MAINTAINER_PROVENANCE.md:18，blob e4bdc78bfc21e738a5941b6c198a28567b11a50c | LocModel／locmodel.com／同名路徑檢索沒有命中第一方產品程式、移植註記或原碼匯入；唯一命中是前輪主動披露功能參考的審查文件。沒有 commit message／檔名命中；不表示未留存輸入不存在 |
| G4 NO ISSUE IDENTIFIED | 27 個參考檔：2.1.0 全部 23 個前端資源，加本日官網 index.html、app.js、language.js、styles.css；對全部可達 Git blob 身分 | **0 完整檔案相同**。包含 third-party OpenCC 與付款 SVG 的原始檔身分檢查；即使命中共享 upstream，也須先區分其獨立授權，不能直接視為 LocModel 自有碼被抄 |
| G5 NO ISSUE IDENTIFIED | 691 個歷史程式碼 blob 對可讀參考碼；含 docs 網頁、Python／Rust／TS／TSX／CSS／HTML／建置程式 | 以 48 個連續 token 忽略註解／空白但保留字串拼法；另對 JS／TS 用 120 個 identifier／literal 正規化 token、至少四個控制關鍵字作形狀檢索；**0 候選**。門檻是檢索條件，非侵權標準；不是完整 AST 或語意等價驗證 |
| G6 VERIFIED | Local desktop/src/api.ts:99；desktop/src-tauri/src/main.rs:46–115、127–157；LocModel 2.1 app.js:1–4、1406、2242 | Local 使用 React／TS，Tauri 的 workspace command 轉接 Python Worker stdin／stdout；參考前端使用原生 JS、DOM／全域狀態及多個 invoke command／事件。結構與具體接口不同；共用 Tauri 不等於複製，LocModel 完整 native 後端仍未取得 |
| G7 VERIFIED | Local catalog.py:14–38、120；參考 PE offset 0xE2C170、catalog version 20261027；前次 catalog 證據檔 | Local 現有 5 筆推薦 repo 與參考 16 筆 repo ID 無交集；不能將此一資料集檢查延伸到全部版本。使用公開 HF 搜尋參數／GGUF／HTTP Range 只是服務與格式重疊，不是獨特程式碼複製證據；參見 [HF API](https://huggingface.co/docs/hub/api) |
| G8 NOT VERIFIED | LocModel 未取得的 native 後端原始碼、其他版本／私有分支、未留存程式輸入 | 未對不可取得內容作全碼比對，無法排除跨語言改寫、重組、非連續或低於門檻的片段。沒有把此未知改標為已排除，也沒有憑空推測後端實作 |

詞法檢索排除 Git 中的 SBOM／evidence／third_party 原文作「第一方程式」候選，但這些檔案仍在全文名稱檢索與完整檔案身分檢查內。OpenCC 大型字典不作第一方形狀檢索，原始檔身分仍有檢查；正規化只為尋找值得人工看的片段，並無相似度／侵權機率分數。

## 4. UI／Logo／素材

目視對照選定首頁、模型、聊天、Agent、圖片創作、運算／啟動及 Local Team。Local 圖片為 repository 中的既有截圖，不假稱本輪重新啟動產品；LocModel 對照為官方公開圖及已驗證的 2.1 前端。

| ID／狀態 | 具體位置 | 判定理由 |
|---|---|---|
| V1 VERIFIED | Local App.tsx:20–23、124–131；LocModel 2.1 index.html:15–40 | 均有側欄、聊天／模型等功能入口。這是通用 UI／合理功能相似；Local 的工作台／創作／管理群組、Team／音樂／作品／任務路徑不等於參考頁逐項移植 |
| V2 NO ISSUE IDENTIFIED | [hardware.webp](https://locmodel.com/assets/hardware.webp)、[models.webp](https://locmodel.com/assets/models.webp)；Local docs/ui-preview/workspace-home.png、workspace-models.png、v070/home-daily-controlled.png；ModelLibrary.tsx:32–65 | 硬體建議／模型搜尋相同功能，但容量層條與分類／量化呈現，對比 Local 工作恢復、任務與作品／推薦面板，沒有識別相同的獨特組版或文案 |
| V3 NO ISSUE IDENTIFIED | [feature-code.webp](https://locmodel.com/assets/feature-code.webp)、[feature-agent.webp](https://locmodel.com/assets/feature-agent.webp)；Local v070/chat-compact-light-650.png、workspace-agent.png；ChatWorkspace.tsx:150–203、AgentWorkspace.tsx:167–216 | 對話歷史與輸入框、計畫步驟是通用模式；LocModel 展示附件／工作資料夾及檔案操作，Local 顯示 Runtime／模型及工具核准／結構化報告。未見直接套用其具體報告文字或組版 |
| V4 NO ISSUE IDENTIFIED | [feature-image.webp](https://locmodel.com/assets/feature-image.webp)、[launch.webp](https://locmodel.com/assets/launch.webp)；Local workspace-creation.png、workspace-runtime.png；CreationWorkspace.tsx:331–375；LocModel imagegen.js:171–198 | prompt／seed／尺寸是生成參數重疊；固定工作流程／Runtime／作品庫與參考表單／畫布、模型啟動面板呈現不同。未找到重用官網人物圖／截圖的證據 |
| V5 NOT VERIFIED | Local workspace-team.png 與音樂／部分進階管理頁 | 沒有取得 LocModel 相應頁面時不宣稱該功能為 Local 獨有，也不推斷已逐頁排除其未公開設計；此未知不是複製證據 |
| V6 NO ISSUE IDENTIFIED | Local desktop/src/style.css:3–17、33–45；LocModel styles.css:1–29、69–100、144–155 | Local 為藍灰配色、218px 分組 grid 側欄與圖像品牌；參考為暖色／184px flex 側欄與 serif 品牌。圓角卡片、系統字型、線性圖示等通用規則不直接構成具體複製 |
| V7 VERIFIED | LocModel 2.1 index.html:17／styles.css:146–147、204–211；[當前 favicon.svg](https://locmodel.com/favicon.svg)；Local logo.png、docs/legal/logo-candidate-v1.png | 2.1 品牌為三條橫色條，當前官網 favicon 是兩條；Local 舊圖為斜 L／紅條，新候選為錯位框／紅方塊，可見幾何不同。不將不同版本混成單一 Logo，也未進行完整商標近似檢索 |
| V8 NO ISSUE IDENTIFIED | 82 個目前 tracked 圖像、歷史中 90 個可解碼圖像 blob，對 16 個參考素材（10 官網截圖、favicon、5 付款 SVG） | 0 完整 bytes 相同、0 同尺寸 RGBA 完全相同；未發現直接相同素材。SVG 不做像素 rasterization，ICO 只用預設解碼 frame；未排除裁切、縮放、重繪或其他版本的轉化複製 |

Local 的 Lucide 等 upstream 圖示有既有獨立依賴來源；不能只因某線性圖示看起來相近就認為是 LocModel 獨創或已被複製。本輪沒有重新盤點第三方授權。

## 5. AI 開發指示與來源接觸

| ID／狀態 | 位置／證據 | 結論 |
|---|---|---|
| A1 VERIFIED | 本輪維護者背景；a47ab25 的 MAINTAINER_PROVENANCE.md:18；本工作區前次 REA／模型目錄證據 | LocModel 確實是產品痛點與功能研究的參考，且已有前次靜態分析資源。**不能宣稱嚴格 clean-room 開發或從未接觸 LocModel**；接觸本身不是具體複製證據 |
| A2 NO ISSUE IDENTIFIED | 本輪可見的先前對話指示、repo 可達文字／開發紀錄、docs/legal/logo-candidate-v1.provenance.json | 可見指示包括對 LocModel 網址做 REA／功能研究、建立整合工作台及通用風格要求；未見逐字複製 LocModel 原碼／截圖／界面文本的明確指示。新 Logo 的已保存生成鏈未提供 LocModel 圖片作輸入。此判定僅限可見內容 |
| A3 NOT VERIFIED | 未保存於 repository、未在本輪上下文提供的 Codex 對話、附件全文、個人筆記／AI 輸入 | 沒有宣稱能讀取所有歷史聊天，也不能確認未取得內容是否包含額外片段或指示。未保存不等於不存在，不把它記成「全部排除」 |

## 6. 是否發現直接複製，以及尚未確認的部分

本輪沒有找到需要標為 POTENTIAL ISSUE 的具體候選。已確認存在的是功能研究、一般 UI／格式與框架重疊，以及取得過交付前端的事實；沒有從這些事實直接跳到侵權結論。

NOT VERIFIED 的界線集中為：完整／其他版本 LocModel 後端原碼、未保存的對話與輸入、歷史條款是否適用或被接受、跨語言／重構／短片段／裁切等不在檢索保證內的轉化相似，以及完整商標／外觀法律判斷。這些是資料／方法界線，並非已發現問題清單，也不是繼續無限調查的先決條件。

## 7. 對 MIT 決策的實際影響

**NO ISSUE IDENTIFIED：本輪沒有增加「須先取得 LocModel 授權，Local LLM 才能採 MIT」的具體來源障礙。** 依目前證據，不因功能概念／側欄／共同開源依賴而延長第一方授權審查。

維護者仍需依原 MIT_FINAL_APPROVAL_CHECKLIST 明確批准自己可授權的第一方範圍；本報告不代為採用 MIT，不處理掉所有第三方 Notice／Runtime／模型義務，也不給予 LocModel 素材或軟體的使用授權。尚未確認的抽象可能性不自動變成實質阻擋。

## 8. 何時才需進一步處理或取得授權

只有在新增具體片段、檔案／素材匹配、可核對的直接移植指示，或權利人提出具體內容時，才重開對應範圍：固定雙方版本／位置、區分 upstream／通用表達、確認實際授權，必要時取得權利人許可或另行批准替代實作。不能以現在的有限安裝許可當作可複製其自有程式碼的依據；也不因目前沒有這種 grant，就推定 Local 已使用了其受保護內容。

本輪不要求為尚未找到的內容先索取概括授權函，不改程式／UI／Logo，不啟用 MIT，不建立 Release／Tag，不提出 SignPath 申請，也不改 main。下一步是既有的維護者 MIT 範圍／採用決策，不是將 LocModel 未確認事項一律升成阻擋。

### 驗證與重現定位

Git 基準、非 shallow、refs／root、marker、27 個參考的 SHA 與 token 檢索方法，保存於本機 ignored build/locmodel-audit/history-and-clones.json；原始碼比對工具不執行目標。圖像比對與官網 URL／SHA 位於 visual/；歷史圖像位於 history-assets.json；官網／協議擷取位於 official/；ZIP 與 PE 位移資料位於 official-archive-identity.json、verified-front-end.json。REA 完整 bundle 已保存於同一工作目錄，沒有把受比對的 LocModel 原碼／官網圖片提交至本庫。

可用 git rev-list --all --count、git rev-parse --is-shallow-repository、git rev-list --max-parents=0 --all、git rev-list --objects --all 及指定 Commit 的 git show 重新定位。機器檢索為上述明列條件，不等同對未知歷史的證明。此輪只檢查三份 Markdown、連結與受保護檔案完整性；既有第三方審查與 Windows CI 不重跑，文件提交使用 [skip ci]，不改 workflow。

文件驗證已通過：23 筆有定位的結果、比對數量／方法界線與來源紀錄一致，三份文件的相對連結可解析，原 A1–A4 未核准欄位保持；root LICENSE、產品碼、圖示、依賴清單及 workflow 未變。最後保存本報告的提交只包含報告更新，沒有把其自身當成已被前述 a47ab25 歷史掃描涵蓋。
