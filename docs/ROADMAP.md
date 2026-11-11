# 桌面工作台路線圖

**E3-C1–C3 已交付**，版本維持 0.6.2。Benchmark Core、版本化 SQLite、受控資源／時間、同一載入實例的 Cold／Warm 分離、OpenVINO CPU／Intel GPU IR 與 CPU 文字，以及 llama.cpp CPU／Vulkan 文字的真實原始數據均已加入。進階介面提供手動測試、取消、歷史比較與 JSON／CSV 匯出。新鮮度與 Benchmark 驅動設備推薦 E3-D1、異質並行調度 E3-D2 尚待下一批，compute capacity 仍為 1，HETERO 拒絕。[Benchmark](HARDWARE_BENCHMARK.md) · [推薦交付邊界](DEVICE_RECOMMENDATION.md)。

**Batch 4E E3-A、E3-B** 已交付統一資源語意及可選 OpenVINO Adapter。實測包含空白環境安裝、真實 CPU 文字聊天、CPU／Intel GPU 的 IR 張量推理與裝置證據。Intel NPU 同一路徑待硬體驗收，AMD／Qualcomm 維持契約。E3-C 本輪完成後，接著依序實作 E3-D 的智慧分工與推薦，E4 的遠端影音，以及 E5 的情境首頁、新手操作列與作品網格。 [支援範圍](NPU_SUPPORT.md)

**第三階段 Batch 3**。3A 已加入部分交付與固定工具參數。3B 接入 SD 1.5、Wan 2.1、ACE-Step 的受管權重安裝。3C 加入作品查詢、媒體中繼資料、原檔與參數回填。3D 加入私人網路文字 Host／Client。3E 加入 Runtime 能力與推薦，並區分權重偵測和校驗。下一項驗收是兩台實體 Windows 電腦上的 GPU 文字推理和斷線恢復，之後再擴充遠端媒體與憑證配置體驗。

1. **第三階段 Batch 1**。新增下載續傳與歸屬檢查、GGUF 來源校驗、受管引擎健康，以及團隊、代理人、創作與運算環境精修。跨硬體與使用者端的驗收另行進行。
2. **原生驗收優先**：在乾淨的 Windows 10／11 x64 上確認安裝、捷徑、WebView2、IPC、子程序收尾和卸載保留資料；獨立檢查 GPU、網路中斷、實際下載與各防毒產品。完成簽章前維持開發產物。
3. **Runtime 深化**：加入 Windows 安全憑證儲存、持久連線設定、相容性與額度訊號、真正可比較的效能與成本策略、資源實測校正。未知成本或不同意傳送時禁止外部派送。
4. **Colab**：已接入 [Colab Enterprise REST](https://docs.cloud.google.com/colab/docs/reference/rest) 的既有範本、Notebook 作業和狀態查詢。使用者須提供已有的 Google Cloud 專案、IAM、範本、配額及 Cloud Storage，並逐次確認可能的費用。雲端實際驗收、配額提示與產物匯入待後續完成。
5. **第三階段 Batch 2**。Agent 已接入工具契約、版本核准、有限步驟與逐次審核。團隊已接入角色、三種協作模式、依賴驗證和設定及結果保存。團隊成員的 Agent 工具模式、子程序隔離及模型原生工具能力仍需後續實作或驗收。
6. **P2 擴充與路由**。先完成 Runtime 能力、成本與資源資料，再加入推薦和智慧路由。插件 Manifest 需定義來源、版本、雜湊、權限與啟停。
7. **更新與發行**。工作台會查詢 `workspace-vX.Y.Z` 的 GitHub 發行、下載並核對 SHA-256。使用者執行安裝包。正式 Release、簽章與無人值守更新另行驗收。
