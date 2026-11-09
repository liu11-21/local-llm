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
