# 桌面工作台路線圖

1. **現在**：Tauri 2 宿主、React 工作台、Windows Worker onedir、聊天與歷史、模型庫、分層估算、按需引擎、既有團隊和三種 ComfyUI 工作流程。
2. **原生驗收優先**：在乾淨的 Windows 10／11 x64 上確認安裝、捷徑、WebView2、IPC、子程序收尾和卸載保留資料；獨立檢查 GPU、網路中斷、實際下載與各防毒產品。完成簽章前維持開發產物。
3. **Runtime 深化**：加入 Windows 安全憑證儲存、持久連線設定、相容性與額度訊號、真正可比較的效能與成本策略、資源實測校正。未知成本或不同意傳送時禁止外部派送。
4. **Colab**：已接入 [Colab Enterprise REST](https://docs.cloud.google.com/colab/docs/reference/rest) 的既有範本、Notebook 作業和狀態查詢。使用者須提供已有的 Google Cloud 專案、IAM、範本、配額及 Cloud Storage，並逐次確認可能的費用。雲端實際驗收、配額提示與產物匯入待後續完成。
5. **進階工作流程**：獨立代理人可預覽、核准唯讀工具並留存結果。團隊角色與依賴、作品索引和媒體參數待深化。擴充 Manifest 需定義來源、版本、雜湊、權限與啟停。
6. **更新與發行**：工作台會查詢 `workspace-vX.Y.Z` 的 GitHub 發行、下載並核對 SHA-256。使用者執行安裝包。正式 Release、簽章與無人值守更新另行驗收。
