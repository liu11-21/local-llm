# 桌面 UI 設計

## 0.7.0 最後精修

首頁預設僅硬體摘要，監控可展開／收合，收合時卸載該面板的前端輪詢。內顯明列專用與共享 RAM，128 MiB 不代表全部可用容量，共享上限不重複加到 RAM。切換頁面回頂端；聊天保留串流／Markdown／程式碼／Token／歷史，新增每頁 50 與搜尋。設定頁明列 0.7.0 Development、Worker、建置 SHA、Windows x64、Signed No；更新失敗不影響其他頁面。

之前：[E4/E5 首頁](ui-preview/e4e5/home-daily-controlled.png)。之後：[收合監控](ui-preview/v070/home-monitor-collapsed.png)、[分頁歷史](ui-preview/v070/chat-history-paged.png)、[版本](ui-preview/v070/settings-version.png)、[影片](ui-preview/v070/remote-video-playback-controlled.png)、[音樂](ui-preview/v070/remote-music-playback-controlled.png)。均為真實 React；影音頁為受控 Host 與合法測試檔，非模型生成。四尺寸、深淺色、鍵盤、Reduced Motion 及既有工作流程保留。[量測與限制](V070_DELIVERY.md)。

## E5 實際介面

聊天改為可展開模型／來源操作列，650px 預設隱藏歷史；設定、推薦與 Benchmark 能力保留。任務主列呈現工作／模型／來源／進度，完整 ID、資源、推薦憑證及錯誤置於進階區。首頁依首次、日常、活躍工作與配對主機調整內容。新手操作列固定於底部，完成後輕量提示。

作品有 Grid／List、四種篩選／排序、搜尋、24 筆分頁、播放器與設定重用。縮圖為 16 MiB 有界 PNG 快取；只預覽選中的原始媒體，舊作品首次未預覽時顯示圖示。保留深淺色、鍵盤、Reduced Motion 與四尺寸。

[之前](ui-preview/device/device-chat-vulkan-real-dark.png) · [精簡聊天](ui-preview/e4e5/chat-compact-dark.png) · [窄視窗](ui-preview/e4e5/chat-compact-light-650.png) · [影片](ui-preview/e4e5/remote-video-playback-controlled.png) · [音樂](ui-preview/e4e5/remote-music-playback-controlled.png) · [作品](ui-preview/e4e5/works-grid-light-650-controlled.png) · [情境首頁](ui-preview/e4e5/home-daily-controlled.png)。影音畫面為受控 Host 的合法測試媒體，並非模型生成。[操作量測與完整報告](E4_E5_DELIVERY.md)。

## E3-D 共用運算建議

DeviceChoice 融入聊天、Agent、兩種 Team、圖片／影片／音樂、模型中心、運算環境與 Benchmark，不另做獨立控制台。主畫面只顯示設備、建議原因、有限證據摘要及操作；偏好、Workload、Warm／啟動／TTFT／Decode、版本、驅動、精度、Freshness 和替代來源放進進階區。沿用黑白灰與 Reduced Motion。

可手動選設備、套用建議或保留既有單工作模式；這些操作本身不送出任務。Agent 計畫顯示真正已保存的 Runtime／設備，修改時撤銷待核准計畫。Team 每成員可有自己的選擇。創作不把尚未支援的遠端影音列為可用。任務中心顯示預留 RAM、Engine、裝置、父任務與實際放置是否驗證。

受控 UI 包含長模型／裝置名稱、無 GPU／NPU、Benchmark 缺失／過期、離線、不確定、手動覆寫、無自動派送、鍵盤、四種尺寸與深淺色。原生 UI 驗收走共用建議→採用 Vulkan→隔離聊天→保存新執行 ID→任務證據。[深色聊天](ui-preview/device/device-chat-vulkan-real-dark.png) · [650px 淺色](ui-preview/device/device-chat-vulkan-real-light-650.png) · [實際任務證據](ui-preview/device/device-task-evidence-real-light.png)。

## E3-C Benchmark

運算環境加入折疊的「進階 · 模型效能測試與歷史」。簡易操作先選模型與設備，顯示工作量和整體上限，確認後才開始。次數、記憶體和 Token 參數放在進階選項。沿用既有黑白灰、Panel、按鈕、Reduced Motion 與任務進度，沒有重做 Design System。

結果逐個工作量呈現 Warm 平均、P50／P95、標準差、吞吐、首次推理和程序 RAM。文字另顯示原生 TTFT、首段文字延遲、Prefill、Decode、Token 數。缺少來源時顯示未知，Tensor 不列出不適用的 Token 欄位。載入與編譯、實際裝置和驗證限制另列。歷史可依模型／設備篩選、分頁、比較、刪除及匯出。非等價比較會顯示原因，不產生混合工作量排行榜。

[真實深色結果](ui-preview/benchmark/benchmark-real-history-dark.png) · [真實 650px 淺色比較](ui-preview/benchmark/benchmark-real-compare-light-650.png)。受控回歸涵蓋 1280×900、1024×768、800×600、650×720、深淺色、鍵盤、Reduced Motion、無 GPU／NPU、無紀錄、進行中／失敗、長名稱與未知值。受控數據未作為硬體證據。

## E3-A、E3-B 的實際介面

| 區域 | E1、E2 | 本輪行為 |
|---|---|---|
| GPU 資源 | 顯示專用顯存和共享記憶體 | 補上 UMA／獨立顯存類型，餘量明列估計，後端回報的池容量另列 |
| OpenVINO | 主 Worker 的 Provider 查詢 | 獨立 Runtime 安裝摘要、使用者確認、裝置查詢、IR 匯入與移除 |
| 聊天 | llama.cpp 和原有外部 Runtime | 可選本機 OpenVINO 和已匯入文字模型，進階參數選擇實際裝置，正常串流與保存對話 |
| 裝置證據 | 硬體是否存在 | 可查執行紀錄，明列指定裝置、回報裝置與未取得算子證據的情況 |

以下三張截圖使用真實 React、Worker、TaskManager、隔離 OpenVINO 及官方 Qwen2.5-Coder 0.5B 模型。CPU 文字生成完成並保存，GenAI 算子分配仍標未驗證。 [Runtime 管理](ui-preview/e3/openvino-runtime-real.png) · [深色 CPU 聊天](ui-preview/e3/openvino-chat-cpu-real-dark.png) · [650 px 淺色聊天](ui-preview/e3/openvino-chat-cpu-real-light.png)

上述是 E3-A／B 時的紀錄，當時尚未交付 E5；情境首頁、固定引導操作列、輕量完成提示和作品 Grid／List 現已交付，見本文 E5 段落。 [實測範圍](TEST_REPORT.md)

## Batch 4E＋NPU 的 E1、E2

| 區域 | 更新前 | 本輪行為 |
|---|---|---|
| 資源摘要 | GPU 與 VRAM 一律未知 | 首頁可選擇每張偵測到的 GPU，顯示實際計數器。未知數值繼續保留未知 |
| 運算環境 | 以引擎狀態及 llama.cpp 裝置清單為主 | 加入 GPU／NPU 面板，分列驅動、取樣時間、使用率、專用顯存和共享記憶體。Provider 資料放在進階區 |
| 圖片新手引導 | 固定前往本機 ComfyUI 準備 | 可直接推薦已配對且流程就緒的圖片主機，帶入創作頁的 Runtime 與 Workflow |
| 斷線後作品 | 原提示詞可能空白 | E1 升級後提交的任務可從本機資料庫還原提示詞與設定 |

- 真實 Iris Xe 的監控畫面，來自實際 React、Worker 與 Windows 計數器。其餘模型名稱屬既有 UI 回歸資料。 [硬體監控](ui-preview/batch4e/hardware-runtime-real.png)
- 受控 NPU 資料驗證 650 px 淺色、長名稱和未支援數值。畫面標示受控裝置及推理待驗收。 [NPU 介面回歸](ui-preview/batch4e/hardware-npu-controlled-light.png)
- 已配對主機的遠端圖片引導，主機和生成輸出來自受控測試。 [遠端創作引導](ui-preview/batch4e/onboarding-remote-image.png)

上述是 E1／E2 時的紀錄，當時尚未交付 E5；固定底部操作列、輕量完成提示、情境首頁及作品網格現已交付，見本文 E5 段落。 [驗收範圍](TEST_REPORT.md)

## 首次使用與遠端圖片

- 引導把硬體、用途、模型與準備分開。失敗時在原地提供重試，成功保存首個回答後提供下一項任務。 [推薦與準備](ui-preview/first-use-prepare.png) · [首次任務完成](ui-preview/first-use-complete.png)
- 圖片頁保留同一個模型和運算環境選擇。遠端傳送沿用共用確認視窗，完成後作品庫顯示來源主機、尺寸、種子與工作流程。 [遠端圖片傳送確認](ui-preview/remote-image-consent.png) · [作品庫遠端來源](ui-preview/remote-image-library.png)

畫面來自實際執行的 React 和 Python Worker。首次文字輸出來自受控模型。作品庫截圖使用實際 CPU 生成的 SD 1.5 PNG，經受控傳輸保存。 [實測與限制](TEST_REPORT.md)

## Batch 4A–4C 工作台與任務準備

| 區域 | 原流程 | Batch 4 |
|---|---|---|
| 首頁 | 統計卡及快速連結分區 | 六種任務有直接入口，同畫面看到本機資源、最近任務與作品 |
| 首次聊天 | 在模型中心下載，再到運算環境安裝引擎，最後回聊天 | 進入聊天後可在原頁下載推薦模型與安裝引擎，減少兩次跨頁準備 |
| 文字與創作 | 各自維護運算選擇 | 聊天、代理人、團隊、創作共用選擇器。只顯示該功能現有的運算能力 |
| 外部傳送 | 各頁自行組合確認文字 | 共用確認視窗列出目的地、模型與費用。Esc 返回編輯 |
| Host 分享 | 填位址、埠、憑證路徑、私鑰路徑，再建立邀請 | 選擇私人網路後確認分享，即配置憑證並顯示邀請。四個手動欄位移入進階區 |

視覺改用近黑和中性灰表面，強調色集中在焦點、運作狀態和主要動作。側欄可收合，窄視窗保留展開導覽。短暫淡入與按鈕回饋遵守 reduced motion。CPU 和 RAM 取自實際 Windows 系統，GPU 使用率和 VRAM 用量顯示未知。

- [深色首頁](ui-preview/batch4-home-dark.png) · [淺色 650 px 首頁](ui-preview/batch4-home-light-narrow.png)
- [分享算力](ui-preview/batch4-remote-sharing.png) · [外部傳送確認](ui-preview/batch4-transfer-review.png)

畫面來自連到 Python Worker 的 Chromium 測試。遠端畫面中的回環位址與外部確認中的目的地是測試資料。

## Batch 3D–3E 私人遠端運算

- 「連接另一台電腦」分為筆電配對與本機 Host 管理。首次啟用 Host 展開進階 TLS 欄位。Host 在線與引擎是否已載入模型各自顯示。 [深色 1280 px](ui-preview/remote-1280-dark.png) · [淺色 650 px](ui-preview/remote-650-light.png) · [Host 已啟用與長名稱](ui-preview/remote-host-active.png)
- 「比較運算環境」按任務和模型列出相容性、需要安裝或連線、未知資源、費用及隱私限制。送出遠端聊天時會再次顯示資料目的地。

Host 畫面取自實際桌面開發 Worker 的回環測試。截圖中的長名稱及模型清單為測試情境。

## Batch 3 創作與作品庫

- 流程準備區顯示 ComfyUI 是否可連線及缺少的權重或節點，提供環境選擇、固定來源與授權、磁碟空間、安裝核准和進度。常用參數直接顯示，其他參數由工作流程清單列在進階設定。 [深色 1280 px](ui-preview/batch3-creation-1280-dark.png) · [淺色 650 px](ui-preview/batch3-creation-650-light.png)
- 作品庫以類型、模型及日期搜尋瀏覽，預覽旁顯示模型、尺寸、種子和來源，可回填原始設定。圖中是本機 CPU 實際生成的 SD 1.5 圖片，索引資料來自受控 UI 測試。 [作品庫](ui-preview/batch3-works.png)
- 團隊保留有交付的成果，標出審查未完成、使用部分依賴及失敗或略過的節點。截圖使用受控審查失敗。 [部分交付](ui-preview/batch3-team-partial.png)

舊介面把啟動、下載與大量引擎參數擠在同個視圖。新版左側依「工作台／創作／管理」分組，首頁提供下一步，較少用的參數放在折疊面板。跨頁工作列顯示任務、可計算的進度及取消。

- 深色以石板底和淡藍強調色為主；淺色重新定義背景、表面、邊界及文字。顏色、字級、邊界、間距、圓角、陰影、焦點及動畫集中在 `desktop/src/style.css`，以 Lucide 統一圖示。
- 內容欄在較窄的視窗改為單欄，650 px 使用可展開的導覽；尊重系統降低動態效果設定。聊天可用 Ctrl + Enter。
- 首頁以四張資訊卡呈現最近模型、任務和作品。聊天有歷史、串流、模型／環境選擇與生成參數。回答支援 Markdown、程式碼上色、複製及重新生成。使用標題旁的按鈕可改名，刪除需再次確認。文字模型啟動後可顯示實際輸入 Token 和上下文預算。
- 模型中心顯示 GGUF、硬體推薦、搜尋、下載與載入預估。運算環境可在背景安裝 ComfyUI，完成後再啟動，並管理 llama.cpp 和外部 HTTPS 端點。使用頂部「任務」可查看進度、取消或重試下載。
- AI 團隊重用現有排程、草稿和整合。獨立代理人可先預覽並核准本機唯讀工具，報告保留工具原始資料。創作頁接入三種需要各自權重的 ComfyUI 工作流程。運算環境可連線至使用者既有的 Colab Enterprise 專案。介面目前提供繁體中文。

實際畫面來自連接 Python Worker 的 React 開發預覽。聊天與代理人頁載入先前在本機生成的 SQLite 紀錄。

- [首頁](ui-preview/workspace-home.png) · [深色聊天](ui-preview/workspace-chat.png) · [淺色聊天](ui-preview/workspace-light.png)
- [模型中心](ui-preview/workspace-models.png) · [運算環境](ui-preview/workspace-runtime.png) · [任務中心](ui-preview/workspace-tasks.png)
- [AI 代理人](ui-preview/workspace-agent.png) · [AI 團隊](ui-preview/workspace-team.png) · [創作中心](ui-preview/workspace-creation.png)

## 第三階段精修

- 團隊把成員標題與動作放在第一列，運算環境與模型在第二列。長名稱的選擇器可以縮放，窄視窗仍能保留成員標題的閱讀順序。 [深色 1280 px](ui-preview/phase3-team-dark.png) · [淺色 1024 px](ui-preview/phase3-team-light.png) · [深色 800 px](ui-preview/phase3-team-800.png) · [淺色 650 px](ui-preview/phase3-team-narrow.png)
- 代理人將任務、角色、模型、核准工具與執行步驟整理成同一區。CPU 執行緒和記憶體等數值直接取自已保存的工具輸出，模型回答另設一區。截圖載入的是先前實機報告，保留了模型誤讀 CPU 數值的範例。 [代理人事實與回答](ui-preview/phase3-agent.png)
- 創作頁生成前顯示連線和權重狀態，生成中顯示實際工作狀態，完成時直接預覽。使用「沿用上次設定」可讀回同類型最近作品的生成參數。 [缺少影片權重](ui-preview/phase3-creation-missing.png) · [實際生成中](ui-preview/phase3-creation-running.png) · [生成結果](ui-preview/phase3-creation-result.png)
- 運算環境先選本機、另一台電腦、雲端 AI 或 Colab Notebook。只有選定來源才出現該類設定。外部服務保留資料傳送和可能費用說明。模型中心可檢視來源或從中斷的下載續傳。 [來源選擇](ui-preview/phase3-runtime.png) · [Colab 進階設定](ui-preview/phase3-runtime-colab.png) · [模型來源未知](ui-preview/phase3-models.png) · [已核對模型來源](ui-preview/phase3-models-verified.png)
- 引擎健康診斷顯示實際錯誤碼和可採取的操作。 [Windows 原則封鎖時的引擎診斷](ui-preview/phase3-runtime-policy.png)

## Batch 2 工作流程

- Agent 從模式、模型、允許工具及任務開始。計畫預覽顯示版本與授權範圍。核准整體計畫後，逐次模式會分開顯示當次工具和參數。時間軸保留決策、工具結果、拒絕、錯誤及最終回答。 [計畫](ui-preview/batch2-agent-plan.png) · [工具核准](ui-preview/batch2-agent-approval.png) · [時間軸](ui-preview/batch2-agent-timeline.png) · [格式錯誤](ui-preview/batch2-agent-error.png)
- 團隊保留多模型整合入口。角色工作流程先套用範本並指派模型，再展開角色、System Prompt、工具、節點與限制。預覽顯示依賴，執行結果保留初稿、審查、修正版與失敗或略過的節點。 [角色](ui-preview/batch2-team-roles.png) · [工作流程](ui-preview/batch2-team-workflow.png) · [審查結果](ui-preview/batch2-team-review.png) · [窄版部分失敗](ui-preview/batch2-team-error.png)

這組截圖來自實際 React 開發預覽及 Python Worker。推理回應由可控的本機 SSE 協定測試端點產生，畫面中的 Protocol Fixture 是測試資料。
