# 桌面 UI 設計

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

- 團隊把成員標題與動作放在第一列，運算環境與模型在第二列。長名稱的選擇器可以縮放，窄視窗仍能保留成員標題的閱讀順序。 [深色 1280 px](ui-preview/phase3-team-dark.png) · [淺色 1024 px](ui-preview/phase3-team-light.png) · [淺色 650 px](ui-preview/phase3-team-narrow.png)
- 代理人將任務、角色、模型、核准工具與執行步驟整理成同一區。CPU 執行緒和記憶體等數值直接取自已保存的工具輸出，模型回答另設一區。截圖載入的是先前實機報告，保留了模型誤讀 CPU 數值的範例。 [代理人事實與回答](ui-preview/phase3-agent.png)
- 創作頁生成前顯示連線和權重狀態，生成中顯示實際工作狀態，完成時直接預覽。使用「沿用上次設定」可讀回同類型最近作品的生成參數。 [缺少影片權重](ui-preview/phase3-creation-missing.png) · [實際生成中](ui-preview/phase3-creation-running.png) · [生成結果](ui-preview/phase3-creation-result.png)
- 運算環境先選本機、另一台電腦、雲端 AI 或 Colab Notebook。只有選定來源才出現該類設定。外部服務保留資料傳送和可能費用說明。模型中心可檢視來源或從中斷的下載續傳。 [來源選擇](ui-preview/phase3-runtime.png) · [Colab 進階設定](ui-preview/phase3-runtime-colab.png) · [模型來源未知](ui-preview/phase3-models.png) · [已核對模型來源](ui-preview/phase3-models-verified.png)
