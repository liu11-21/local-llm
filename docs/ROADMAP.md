# 桌面工作台路線圖

1. **現在**：Tauri 2 宿主、React 工作台、Windows Worker onedir、聊天與歷史、模型庫、分層估算、按需引擎、既有團隊和三種 ComfyUI 工作流程。
2. **原生驗收優先**：在乾淨的 Windows 10／11 x64 上確認安裝、捷徑、WebView2、IPC、子程序收尾和卸載保留資料；獨立檢查 GPU、網路中斷、實際下載與各防毒產品。完成簽章前維持開發產物。
3. **Runtime 深化**：加入 Windows 安全憑證儲存、持久連線設定、相容性與額度訊號、真正可比較的效能與成本策略、資源實測校正。未知成本或不同意傳送時禁止外部派送。
4. **Colab**：停用的 Adapter 只回報能力，不建立資源。[Colab FAQ](https://research.google.com/colaboratory/intl/en-GB/faq.html) 說明互動服務及使用限制；[Colab Enterprise REST](https://docs.cloud.google.com/colab/docs/reference/rest) 是後續評估路徑。驗收前需使用者擁有的 Google Cloud 專案、IAM、GPU 配額和計費授權。實作暫存作業、結果、逾時、配額顯示及清理，禁止將一般 Colab 當常駐主機。
5. **進階工作流程**：先做有人工確認的唯讀工具和可稽核的代理人任務，再加團隊角色與依賴、作品索引和媒體參數。擴充 Manifest 需定義來源、版本、雜湊、權限與啟停；不以目錄隔離當安全沙箱，也不執行社群任意腳本。
6. **公開發行**：完成乾淨安裝、簽章、簽章後防毒驗收與 Tauri 更新端對端，再建立正式 Release。
