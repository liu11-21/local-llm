# Device Recommendation · E3-D1–D4

## E3-F 現行推薦與資源政策

runtime-recommend 另保存本機推薦憑證；實際採用／派送保存原 Benchmark ID、Run ID、Recommendation ID、Task ID 與 Dispatch ID。採用後 15 分鐘內仍需在開始時重新通過原條件，模型／設備／驅動／證據變動時拒絕舊憑證。未採用的手動設備選擇不偽裝為 Benchmark 推薦。

本輪舊 GPU LUID 與目前不同，舊結果被排除；驗收明確執行新短張量 CPU／GPU Benchmark 後，真實 UI 採用及原生推理通過。[原始完整證據](evidence/media/recommendation-native-real.json)。張量排名不推論文字效能。

固定 8 GiB 隔離上限已改為動態實體 RAM 安全容量與使用者上限；當前不足排隊、總容量不足拒絕。遠端影片與音樂候選依各自受管理 Workflow／完整權重／健康判斷。[記憶體與 ComfyUI 調度](RESOURCE_SCHEDULER.md)。

版本維持 0.6.2，分支 dev/desktop-workspace。D1、D2、D3、D4 已連續實作。Benchmark 提供證據，既有 runtime_recommendation.py 決策，TaskManager 執行。沒有第二套 Benchmark、推薦核心或工作佇列。

## D1 新鮮度與可比較性

benchmark_evidence.py 只讀取既有資料，不啟動 Benchmark。分別輸出 freshness 與 comparability。

| 維度 | 值與規則 |
|---|---|
| freshness | current 表示必要身分一致。stale 包括驅動變更或超過 30 天的更新建議。invalidated 包括權重、格式、量化、Backend、執行檔與裝置變更。unknown 包括缺少必要身分、版本、精度或時間。 |
| comparability | equivalent 需要完整條件與完整算子分配證據；partially_comparable 保留 Backend／放置限制；not_comparable 包括不同輸入、Batch、推理參數、精度、錯誤輸出或 Fallback；insufficient_evidence 包括缺列、未完成及未實測 NPU。 |

檢查 Model ID、全部權重 SHA-256、格式、量化、Context、輸出長度、記憶體上限、Batch、採樣、EOS、Backend 版本、引擎 SHA-256、Device、Driver、Mapping、輸入雜湊、時間與 first／warmup／measured 完整性。E3-C schema 1 原本固定的單 Batch、貪婪解碼及 ignore_eos 條件按該 Runner 契約補齊。

30 天是保守更新建議，不代表硬體失效。歷史保留，不自動重跑。雜湊快取最多 30 秒，以路徑、大小及 mtime_ns 區分。排隊後啟動前再次核對已確認權重及引擎，改變時拒絕並要求重新選擇。

OpenVINO 裝置／版本查詢超過 60 秒不作目前身分證據，硬體／驅動清單超過 90 秒不作新鮮 GPU 身分。可在運算環境按「檢查 OpenVINO 裝置」更新，這不是 Benchmark。GPU 只用 DEVICE_LUID 對應 DXGI LUID。Vulkan 沒有物理映射時，單張 GPU 的一致清單僅作有限 Backend 身分；多張未映射 GPU 不猜索引。

Benchmark 完成、輸出正確、執行裝置、完整算子分配、Backend 設定與 Fallback 各自保存。GenAI／llama.cpp 可作有限 Backend 效能參考，但不提升成完整硬體放置驗證。未驗證 NPU 不參與排名。歷史峰值不是已驗證的最低記憶體需求。

## D2 推薦、資源與偏好

device_recommendation.py 組合即時資料，呼叫同一個 runtime_recommendation.recommend。順序為 Capability、健康／連線、模型格式／安裝、資源、D1 證據、偏好與風險。

結果包含 Runtime、Engine、Device、Model、availability、evidence_level、confidence、performance、resource、cost、needs_consent、替代候選與原因。availability 分為 ready、needs-setup、uncertain、incompatible。未安裝、裝置缺失、NPU 壓縮條件不符、離線及政策不允許者不進入可執行排序。沒有 Adapter 的 AMD／Qualcomm NPU 不列為可執行候選。OpenVINO GPU 與 Vulkan 保持不同 Backend。

System RAM、Dedicated VRAM、Unified／Shared、估計及實測分開。只檢查所選單張 GPU 的可用池，不合併多張 VRAM，不把共享上限當可分配容量。Intel 內顯主要計入共享 RAM，不能因專用顯存小就判為不可用。GPU 原生編譯／驅動工作空間預留至少 2 GiB；隔離程序依動態 RAM 策略與使用者上限准入，不自動切換或下載。

支援 Auto、Speed、Low Memory、Energy、Privacy、Local First、Cost。沒有功耗時不判定最省電，未知費用不當免費。隱私限制本機，節省費用排除可能計費與未知費用。外部 API 需要手動政策與此次確認，配對主機也必須確認目的地及內容。

不使用 0–100 分。先依相容性及本機偏好提出建議，只在同模型、Backend、版本、精度、工作量與條件群組中比較指標。Warm latency、TTFT、Decode、模型載入＋首次推理分開。最後一項只用真正 session_cold 樣本，不把第二組 Warm first 當 Cold，也不包含未量測的程序建立／IPC。

任意提示詞條件未知時顯示「目前無法確定哪個設備最快」。使用者可明確選固定短／長文字 32 Token 作參考，不能代表長文件或本次提示詞。真實 SmolLM2 短文字 Warm 約為 CPU 624 ms、Vulkan 321 ms，但 CPU Decode 約 210 token/s、Vulkan 126 token/s，首次載入又可能改變選擇。[原始資料](HARDWARE_BENCHMARK.md)。

## D3 資源調度與實例隔離

device_resources.py 定義 ResourceDemand，TaskManager 在同一把鎖內一次取得全部資源。舊 compute lane 維持 1 並宣告 local:* 排他鎖；device 上限 4、control 上限 2，數量本身不代表准許並行。

需求包含 Device／Engine、RAM、各 VRAM 池、已含於 RAM 的共享需求、CPU／頻寬預算、排他資源、Backend 限制及時間。每裝置、Engine／Provider、共享加速器與遠端 Runtime 都有鎖。未知 GPU 使用 gpu:*，不同 Backend 不會誤認成不同實體 GPU。一次取得所有資源，沒有部分鎖等待循環。

RAM 保留 max(1 GiB, 實體 RAM 10%) 系統餘量，再保守扣除正在執行的預留，可能低估並行數。CPU／頻寬是規劃預算，推理執行緒有上限，不宣稱作業系統級 CPU 百分比隔離。Windows Job Object 限制程序 committed memory，與 RAM 工作集峰值分開。

ComfyUI 運行期間保守預留全域本機資源。其本地／Host 圖片任務沿用這份保留，仍由原 compute lane 序列化；不會被自己的常駐服務或等候它結束的舊 Benchmark 鎖死。其他引擎與 Benchmark 仍須等候 ComfyUI 停止。Benchmark 獨占本機，避免污染量測。舊閒置 GPU 模型保留 GPU 鎖，可由使用者停止；既有單工作流程取得全域鎖後仍能按原行為換模。停止資源的任務不受公平性鎖死。

暫時不足會 queued，可取消，每 250 ms 重查。長期等待會抑制造成競爭的後續工作，但沒有本機持有者時不因外部程式占 RAM 而永久禁止小任務。總容量或隔離上限不可能滿足的需求拒絕，不形成永久隊頭。逾時／取消在程序清理後釋放資源。

device_execution.py 建立既有 LocalEngine／OpenVINOAdapter 的每任務實例，沒有新佇列。SQLite 12 新增 dispatch_runs，保存任務、模型／引擎雜湊、請求與實際設備、資源及狀態，既有資料不變。重開只標 interrupted，不自動重送。正式 Worker 對資料目錄持有 OS 檔案鎖，第二個程序不會重置活躍任務或建立另一套資源預算。

## D4 平台操作與權限

聊天、Agent、兩種 Team、三種創作、模型中心、運算環境與 Benchmark 共用 DeviceChoice。簡易區提供設備、原因與操作；完整版本、驅動、精度、Freshness、記憶體、替代方案在進階區。推薦或採用設備本身不提交任務。明確選設備並開始後才使用隔離多設備流程；「既有單工作模式」保留相容行為。

Agent 計畫版本、工具清單與逐次核准仍生效。OpenVINO 及已連線文字 Runtime 可使用簡易／結構化模式，原生工具協定僅在 llama.cpp 開放。外部 Agent 必須確認提示詞、工具結果與觀測的傳送，工具權限不等於網路授權。

team_dispatch.py 將 DAG 節點交回同一 TaskManager，每成員可選模型、Runtime、設備，使用獨立訊息與程序。依賴就緒後整合，父取消會取消未結束子任務。外部 Team 仍禁止本機工具資料混入草稿，不繞過同意。OpenVINO 輸入上限 1024 Token；沒有 Tokenizer RPC 的 Agent／Team 採保守 UTF-8 位元組上界預檢，這不是效能 Token 數。

創作依 ComfyUI 節點、權重、服務與遠端圖片契約判斷。遠端影片／音樂仍不顯示為可執行。多任務並行不同於單模型 HETERO 分割，後者仍拒絕。

## 原生驗收與限制

[原生結果](evidence/device/acceptance-real.json) 包含推薦→確認→執行、兩個活躍原生 PID 的 CPU／Intel GPU 重疊、FP32 輸出比對、NPU 拒絕、OpenVINO Agent、CPU／Vulkan Team、取消恢復與關閉清理。既有 E3-C 量測原樣匯入，不重跑 Benchmark，也不使用 Mock 排名。

受控測試驗證 NPU、多 GPU、資源競爭與權限。實體 NPU、其他 GPU、多 GPU 實機、雙實體 Host 與雲端仍 NEEDS 硬體／授權。未知映射 Vulkan 的多 GPU 任務保守互斥。微型模型生成品質不由本次執行驗收評分。

本機 Iris Xe／31.0.101.5590／OpenVINO 2025.4.1 的跨程序 GPU blob 重用可重現 0xC0000005，8 GiB 上限下峰值約 0.78 GB，並非耗盡該上限。改用每次工作獨立 GPU 編譯目錄後重啟恢復已通過，不刪舊快取，代價是重複工作仍需編譯。[診斷資料](evidence/device/gpu-cache-diagnostic.json)。這是本機觀察，不推廣為所有 OpenVINO／GPU 的共同缺陷。
