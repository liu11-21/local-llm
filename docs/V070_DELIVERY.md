# Local LLM Workspace 0.7.0 Development 交付

本輪基準 dcab454，僅 dev/desktop-workspace。程式／CI 來源 HEAD `90b10231ff07c9e0cbbcb2c9f95f1326f886cb46`；最終文件／證據提交另見 Git 紀錄與對話交付報告。main 保持 v0.6.2 Stable，不建立正式 Release／Tag，不處理簽章或自動安裝。

## 提交

| Group | Commit | 內容 |
|---|---|---|
| V | dbdd817 | 0.7.0、正規 Cargo lock、版本一致性、建置識別與混搭拒絕 |
| A | 04faf59 | Runtime 任務門檻、結構化錯誤與恢復指引 |
| B | 6d673b6 | opt-in GPU／雙機生成／取消／恢復驗收工具，預設不下載 |
| C | 626b678 | 2000 對話／500 作品重複基線、50 筆聊天分頁、目錄 metadata 優化 |
| D | 0e6bb9f | SQLite 備份、失敗恢復、舊資料庫隔離、真正 NSIS 升級驗收 |
| E | e0b1b3a | 首頁監控／UMA、版本 UI、完整穩定性回歸 |
| E 修正 | d6a5a97 | Windows runner 短路徑 fixture 正規化，保留安全檢查 |
| E 修正 | db32081 | OpenVINO 刷新走本機，導覽回頂端 |
| E 安裝修正 | e794108 | 安裝測試等完整 schema 就緒、舊封裝 Worker 版本驗證，避免過早關閉 |
| E UI 收尾 | 4bdeb54 | 歷史區內捲動、長名稱不撐寬、輸入框可見 |
| E 診斷收尾 | 80ce6b5 | 基線報告不將本機 OS 限制當作其他環境的實測結論 |
| E 桌面修正 | 90b1023 | 僅圖片 CSP 放行已驗證 PNG 快取，實際解碼測試 |
| E 文件 | 本文件所在提交 | 原始證據、截圖、Windows 驗收與安裝包 |

## 版本與更新

| 來源 | 預期／已驗證 |
|---|---|
| package.json／package-lock 根版本 | 0.7.0 |
| Cargo.toml／Cargo.lock 本專案 package | 0.7.0，Cargo generate-lockfile 正規產生，第三方版本未改 |
| tauri.conf.json／Worker／UI | 0.7.0，Development |
| 安裝 EXE／BUILD.json／封裝 Worker | 由 Windows CI 核對版本、來源 SHA、FileVersion、實際 IPC，最終結果見 TEST_REPORT |

`check_workspace_version.py` 檢查第一方來源；打包時產生 workspace-build.json，Rust 拒絕不同版本／通道或不同封裝 SHA，React 也在首項產品 RPC 前驗證。設定顯示 App、Worker、Development、Commit、Windows x64、Signed No。受控舊 Worker 不能送出任何產品操作。[來源檢查](evidence/v070/version-consistency.json) · [設定實際畫面](ui-preview/v070/settings-version.png)。

舊程式使用 vX.Y.Z；工作台僅接受可校驗、非草稿／預發行、較新的 workspace-vX.Y.Z。0.7.0 不把 Stable v0.6.2 或 v99.0.0 誤當 Workspace 更新；空清單、等版、不可信 URL／雜湊不顯示可下載，未來有效 0.7.1 可辨識。檢查失敗僅更新設定訊息，不阻止聊天。不提供不存在的 Release 連結。

## 整合與資源

CPU／GPU、OpenVINO、NPU 候選、已配對 Host、雲端及 Colab 沿用原 Runtime Contract。可連線不等於所有任務可用：未宣告任務不就緒，影音要求 Media v2／Workflow／完整權重，Colab 僅 notebook。OpenVINO 本機模型刷新不再錯查外部 Provider。

IPC 與 TaskManager 共用可理解的原因／恢復方式，覆蓋模型／引擎缺失、格式、RAM／VRAM、權限、憑證、離線、雜湊、下載中斷、空間、逾時、應用控制及未知失敗。詳細資料與 Team 權限代碼保留，URL 查詢及 Bearer／Token 等遮蔽；不是任意內容的完整 DLP，分享日誌仍須檢查。Worker 意外退出不自動重送有副作用的工作。

動態 RAM 保留 max(1 GiB, 10% 實體 RAM)，使用者上限、安全總容量、目前可用量、工作空間及活躍預留都保留。未知需求不當零，UMA 不重複加總。ComfyUI 只在裝置／記憶體可靠且可信閒置時縮小鎖；生成、異常、未知、UMA、多 GPU 不明仍保守。取消與程序清理後才釋放。資源／排程回歸 PASS，不代表已執行 >8 GiB 模型或實體多 GPU／NPU。

## 實機與媒體界線

| 狀態 | 結果 |
|---|---|
| PASS | 本機實際 Iris Xe，16 執行緒、約 16 GiB RAM；目前未偵測到 RTX 5070 Ti／實體 NPU。[本輪診斷](evidence/v070/hardware-diagnosis.json) |
| PASS | 0.7.0 真實 React 使用有效 CPU／Intel GPU Benchmark，採用推薦、TaskManager 派送，OpenVINO CPU FP32 張量輸出正確，保存推薦／Benchmark／Dispatch／Job 及 Job Object 實際限制。[原生鏈](evidence/v070/recommendation-native-real.json) |
| PASS | 遠端圖片／影片／音訊協定、Owner、TLS、冪等、Range、SHA、配額、取消／恢復及保留的自動回歸。合法 VP9／FLAC 可播放、保存 Prompt／Lyrics／設定及重用。[播放器](evidence/v070/ui-playback-controlled.json)；受控推理並非真實模型生成 |
| PASS | 已存在的約 333 MB Qwen2.5-Coder 0.5B IR，三次真實文字生成完成；另三次擷取 GenAI loaded 事件，載入含 Runtime／pipeline／tokenizer 初始化為 2489.751、2367.017、2331.147 ms，中位數 2367.017 ms。指定 CPU，GenAI 算子放置仍未完整驗證。[文字合約](evidence/v070/text-cpu-real-1.json) · [載入三次原始資料](evidence/v070/text-cpu-load-baseline.json) |
| NEEDS GPU | RTX 5070 Ti 的 CUDA／PyTorch／ComfyUI 固定權重生成；Wan 2.1、ACE-Step v1 真實 GPU 生成；其他 GPU／多 GPU、ComfyUI 獨顯＋CPU 真實並行 |
| NEEDS NPU | NPU 實體載入、推理與調度；沒有把 CPU fallback 算成 NPU |
| NEEDS REMOTE HOST | RTX Host＋Iris Xe Client 雙實體機長時生成、LAN／VPN 斷線、Host 重啟、Range 恢復 |
| NEEDS CLOUD AUTH | 真實付費 API／Colab 授權，未啟用或傳送私密提示 |
| NOT RUN | llama.cpp 本輪版本探測回 0xc0e90002，原生推理未強行執行；未修改 Windows／Norton 安全原則 |
| NOT RUN | >8 GiB 大模型實體載入、llama.cpp 文字模型首次載入效能、單模型 HETERO、正式簽章與 Release |

張量原生鏈於同版 e0b1b3a 產生，文字合約與載入量測於最終程式 90b1023 產生，Windows 最終 CI 亦為 90b1023；其後只提交文件與重跑工具。CPU 任務不被稱為新的 GPU 推理；使用既有 GPU Benchmark 也不等於重測 GPU。原始量測沿用上輪相同有效條件的 [Benchmark](evidence/media/benchmark-native-current.json)。本輪缺少 RTX／完整影音權重，不因 UI 播放成功就改標模型推理 PASS。[本輪限制](evidence/v070/native-limitations.json)。

`workspace_acceptance.py` 預設診斷、不下載。Host execute 先驗證目前裝置與真正 CUDA 小型核心運算，所有權重已存在才重新 SHA-256，啟動既有管理服務並生成；Client 額外 consent，核對原 Host／指紋、保存 Job／媒體。recover 只抓原 Job；取消有確認上限。每秒 RAM／nvidia-smi 是觀察峰值，非硬體真峰值。原 ComfyUI 日誌與生成檔需一併保留。[可重跑操作](HARDWARE_ACCEPTANCE_070.md)。

## 效能基線

`workspace_perf.py` 每次新 Worker 程序，5 次取樣，使用 2000 對話與 500 份合法小 PNG；不是模型或 GPU 基準，未清 OS 快取。[原始優化前](evidence/v070/performance-before-scan.json) · [優化後](evidence/v070/performance-baseline.json)。

本機中位數：Worker 首次身份回應約 338 ms、info 約 402 ms、首頁摘要 3.36 ms、50 筆聊天查詢 3.93 ms、500 件作品的一頁查詢約 37.53 ms、資源 RPC 約 0.63 ms。作品原始清單查詢優化前中位數約 550 ms，兩組各 5 次；只是此環境觀察，不宣稱整體應用或模型加速百分比。目錄掃描只讀 metadata、不跟隨連結，開原檔仍重新驗證。仍為 O(n) 檔案掃描，超大庫尚需索引策略。

OpenVINO 文字載入另以 [可重跑工具](evidence/v070/text_load_baseline.py) 記錄三個新程序及新臨時匯入／快取，沒有下載權重、未清 OS 快取，沒有推論 GPU 或 NPU。其 GenAI 算子放置與量化仍未驗證，不能把檔名 int4 當量化證據。既有低層 IPC 基線沒有執行模型，其 NOT RUN 只限該工具。

真正 React 首頁載入與 Runtime 選擇器各 3 次，保存全部數值；該 Runtime 為受控 fixture，不是引擎／模型載入量測。[UI 基線](evidence/v070/ui-stability.json)。[背景監控 CPU 原始基線](evidence/v070/background-monitor.json) 用 GetProcessTimes，比較三組閒置與三組每 3.5 秒輪詢，各 7 秒，僅量 Worker，不包含 WebView／外部程序；零值可能是計時粒度，不代表零成本。[可重跑腳本](evidence/v070/background_monitor.py)。

Windows CI 另測已安裝 App 的三次程序冷啟動、封裝 Worker 的三次基線；首次升級含 Migration 的樣本另列，沒有拿單次舊版與新版宣稱改善。

## 資料與安裝

0.6.2 原始 Worker 建立資料庫，再填入 18 表合成 Migration 資料與使用者檔案標記；對話、Agent／Team、模型來源、權重校驗、Benchmark、設定、Runtime／DPAPI BLOB、作品與參數都比對表內容指紋。新 workspace.sqlite3 與原 desktop.sqlite3 內容相符，原檔不改寫，備份 SHA／完整性通過。[本機結果](evidence/v070/upgrade-worker-local.json)。合成 Benchmark 僅測資料保留，不作效能證據。

Migration 先檢查 schema／reader 與完整性，備份包含 WAL；空間不足／損毀拒絕，失敗保留部分檔再恢復校驗快照。舊 0.6.2 沒有新 guard，故用新檔名隔離；它不能寫入 0.7.0 新資料庫，後續新版資料不自動回填舊 DB。模型與作品原檔留在原目錄。備份不等於媒體完整備份或加密；DPAPI 不能無條件跨 Windows 帳號。[升級與恢復](UPGRADE_070.md)。

真正 0.6.2 Tauri NSIS 由固定 4354605 重新建置，再原地安裝本輪 0.7.0，核對安裝版本、桌面／開始功能表、WebView／Worker、資料及卸載保留。舊 Tk Stable 的 Inno Setup 是另一產品，未拿它當升級基線。Windows 最終來源、CI、下載、EXE SHA-256 見 [TEST_REPORT](TEST_REPORT.md)。

## UI 前後

| 原本 | 0.7.0 |
|---|---|
| 首頁常駐完整資源面板 | 先顯示繼續工作、模型／任務；硬體摘要可展開監控，收合停該面板 RPC |
| 內顯專用記憶體易被當總容量 | 專用／共享 RAM 分列，明確說明共享上限已含實體 RAM |
| 歷史僅最新 100 | 50 筆分頁＋搜尋，歷史獨立捲動，可找到更舊對話且輸入框保持可見 |
| 版本與通道不夠明確 | App／Worker 0.7.0 Development、來源 SHA、Windows x64、Signed No |
| 返回頁面沿用捲動位置 | 導覽回頁首，保留各聊天內容與設定 |

前：[E4/E5 首頁](ui-preview/e4e5/home-daily-controlled.png)、[聊天](ui-preview/e4e5/chat-compact-dark.png)。後：[收合首頁](ui-preview/v070/home-monitor-collapsed.png)、[監控展開](ui-preview/v070/home-daily-controlled.png)、[歷史](ui-preview/v070/chat-history-paged.png)、[版本](ui-preview/v070/settings-version.png)、[窄視窗](ui-preview/v070/chat-compact-light-650.png)、[作品](ui-preview/v070/works-grid-light-650-controlled.png)、[原生證據](ui-preview/v070/recommendation-native-real.png)。畫面為實際 React，不是設計稿；影音為合法受控檔。

保留串流、Markdown、程式碼、Token、創作進度／取消、作品 Grid／List／篩選／重用／24 筆分頁。封裝版 CSP 另以真正 PNG data URL 解碼驗證，未放寬腳本／default-src。四尺寸、深淺色、Reduced Motion、鍵盤及既有 Agent／Team／Benchmark／新手流程全套回歸。

## 正式 Release 前阻擋

需完成 RTX 5070 Ti＋Iris Xe 的固定權重真實生成、長時工作／重啟／斷線恢復、VRAM／RAM 峰值與 ComfyUI 並行；NPU／其他 GPU 按目標設備補測。未簽章開發包在受管理 Windows 仍可能受政策攔截，不能保證免警告。正式簽章、各防毒廠商驗收、正式更新通道與 Release 規劃另外進行。保留本輪所有安全餘量及未知資源回退，不為並行量降低保護。
