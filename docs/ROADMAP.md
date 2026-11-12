# 桌面工作台路線圖

## 0.7.0 Development 整合

V／A／B／C／D／E 已實作：版本一致性與握手、Runtime 任務門檻、可理解的錯誤恢復、明確 opt-in 的硬體驗收、重複效能基線、歷史分頁、SQLite 備份／移轉／降級隔離及 UI 收尾。Windows CI 驗證真正 Workspace 0.6.2 → 0.7.0 安裝升級，結果依最新 TEST_REPORT。

下一階段優先是 RTX 5070 Ti 實體 Host 的固定權重生成、與 Iris Xe 筆電的 LAN／VPN 長時間恢復。NPU、其他 GPU／多 GPU、大型模型真實載入與雲端授權仍依證據區分。main、正式 Tag／Release、簽章不在本輪。[完整交付與阻擋](V070_DELIVERY.md)。

## E4–E5 目前交付狀態

E3-F、E4-A～D 協定／傳輸／管理與 E5-A～C 介面已交付。真實 OpenVINO CPU／Intel GPU Benchmark→推薦採用→派送已串聯；遠端影片／音訊以合法媒體完成協定與播放器驗收。

Wan 2.1／ACE-Step v1 真實 GPU 生成及雙實體 Host、NPU、多 GPU 仍需硬體；本輪 llama.cpp 原生重測受 Windows 應用程式控制阻擋。正式 Release、簽章、雲端授權與單模型 HETERO 不在本輪。[逐項證據及限制](E4_E5_DELIVERY.md)。

**E3-D1–D4 已交付**，版本 0.6.2。獨立提交涵蓋證據有效性、既有推薦器擴充、多設備資源准入及全平台共用 Picker。CPU／Intel GPU 活程序重疊、OpenVINO Agent、CPU／Vulkan Team、取消恢復及關閉清理有原生證據。實體 NPU、其他 GPU、多 GPU、雙機與雲端授權驗收保持限制，不冒稱成功。E4 遠端影音協定與 E5 UI 已接續交付；實際模型 GPU／雙機及正式簽章／發行仍受驗收界線限制。[實際規則](DEVICE_RECOMMENDATION.md)。

**E3-C1–C3 已交付**。Benchmark Core、版本化 SQLite、資源／時間限制、Cold／Warm、OpenVINO CPU／Intel GPU IR／CPU 文字、llama.cpp CPU／Vulkan 真實資料、歷史比較與匯出，皆由 E3-D 直接複用。Benchmark 保持獨占本機，HETERO 單模型分割仍拒絕。[Benchmark](HARDWARE_BENCHMARK.md)。

**Batch 4E E3-A、E3-B** 已交付統一資源語意及可選 OpenVINO Adapter。Intel NPU 待實體驗收，AMD／Qualcomm 維持契約，不宣稱已有推理 Adapter。[支援範圍](NPU_SUPPORT.md)。

**第三階段 Batch 3**。3A 已加入部分交付與固定工具參數。3B 接入 SD 1.5、Wan 2.1、ACE-Step 的受管權重安裝。3C 加入作品查詢、媒體中繼資料、原檔與參數回填。3D 加入私人網路文字 Host／Client。3E 加入 Runtime 能力與推薦，並區分權重偵測和校驗。下一項驗收是兩台實體 Windows 電腦上的 GPU 文字推理和斷線恢復，之後再擴充遠端媒體與憑證配置體驗。

1. **第三階段 Batch 1**。新增下載續傳與歸屬檢查、GGUF 來源校驗、受管引擎健康，以及團隊、代理人、創作與運算環境精修。跨硬體與使用者端的驗收另行進行。
2. **原生驗收優先**：在乾淨的 Windows 10／11 x64 上確認安裝、捷徑、WebView2、IPC、子程序收尾和卸載保留資料；獨立檢查 GPU、網路中斷、實際下載與各防毒產品。完成簽章前維持開發產物。
3. **Runtime 深化**：加入 Windows 安全憑證儲存、持久連線設定、相容性與額度訊號、真正可比較的效能與成本策略、資源實測校正。未知成本或不同意傳送時禁止外部派送。
4. **Colab**：已接入 [Colab Enterprise REST](https://docs.cloud.google.com/colab/docs/reference/rest) 的既有範本、Notebook 作業和狀態查詢。使用者須提供已有的 Google Cloud 專案、IAM、範本、配額及 Cloud Storage，並逐次確認可能的費用。雲端實際驗收、配額提示與產物匯入待後續完成。
5. **第三階段 Batch 2**。Agent 已接入工具契約、版本核准、有限步驟與逐次審核。團隊已接入角色、三種協作模式、依賴驗證和設定及結果保存。團隊成員的 Agent 工具模式、子程序隔離及模型原生工具能力仍需後續實作或驗收。
6. **P2 擴充與路由**。先完成 Runtime 能力、成本與資源資料，再加入推薦和智慧路由。插件 Manifest 需定義來源、版本、雜湊、權限與啟停。
7. **更新與發行**。工作台會查詢 `workspace-vX.Y.Z` 的 GitHub 發行、下載並核對 SHA-256。使用者執行安裝包。正式 Release、簽章與無人值守更新另行驗收。
