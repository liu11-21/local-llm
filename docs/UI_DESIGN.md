# 桌面 UI 設計

## 首次使用與遠端圖片

- 引導把硬體、用途、模型與準備分開。失敗時在原地提供重試，成功保存首個回答後提供下一項任務。 [推薦與準備](ui-preview/first-use-prepare.png) · [首次任務完成](ui-preview/first-use-complete.png)
- 圖片頁保留同一個模型和運算環境選擇。遠端傳送沿用共用確認視窗，完成後作品庫顯示來源主機、尺寸、種子與工作流程。 [遠端圖片傳送確認](ui-preview/remote-image-consent.png) · [作品庫遠端來源](ui-preview/remote-image-library.png)

畫面來自實際執行的 React 和 Python Worker。首次文字輸出與遠端圖片傳輸在這組畫面使用受控模型和圖片資料。 [實測與限制](TEST_REPORT.md)

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
