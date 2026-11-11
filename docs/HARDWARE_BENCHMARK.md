# Hardware Benchmark · E3-C

版本維持 0.6.2。Benchmark Core、引擎 Adapter、TaskManager、儲存與 React 介面分工。只接受使用者確認的工作，不在聊天、推薦或程式啟動時執行 Benchmark。Remote Benchmark 契約目前回報 unsupported，不執行遠端作業。

## 量測契約

預設每個裝置在同一個已載入的模型實例中，依序執行兩個工作量。每組有首次推理 1 次、Warmup 3 次、正式量測 10 次。OpenVINO 只建立一次 CompiledModel 或 LLMPipeline，llama.cpp 只啟動一次獨立 LocalEngine。一般聊天仍維持原有隔離。

Cold 表示新子程序、OpenVINO 空編譯快取及第一組的首次推理，沒有清空作業系統檔案快取。第二組的 first 只是該工作量首次推理，不能當成第二次 Cold。read_model、compile、Pipeline load、input preparation、inference、result processing 各有欄位，API 無法分離的載入與編譯保持 null。程序建立與 IPC 時間不混入推理 latency。

所有延遲用 perf_counter。正式量測才納入母體標準差、平均與 P50／P95，百分位使用 (n−1) 線性內插。req/s = 1000 / 平均延遲，是串行請求吞吐，不是並行硬體飽和吞吐。每個工作量分開保存、顯示，不混成裝置排行榜。

OpenVINO 文字使用 DecodedResults.perf_metrics 原生 Token 數、TTFT 與 TPOT，Decode = 1000 / TPOT(ms)。API 無可靠獨立 Prefill 時為 null。另存首個非空文字 Callback 的牆鐘延遲，不把它冒充精確 TTFT。llama.cpp 保存 SSE usage 與 timings，停用 Prompt Cache，固定 seed=0、temperature=0、ignore_eos=true、輸出長度。沒有原生 TTFT 時保持 null。精確 Token 數絕不以字元數替代。

2025.4.1 原始 token_infer_durations 實測值與公開文件的 ms 單位有疑點，因此以 raw_token_infer_native 原值保存，unit 明確標為 unverified，不拿來換算任何速度。[GenAI PerfMetrics](https://docs.openvino.ai/2025/api/genai_api/_autosummary/openvino_genai.PerfMetrics.html)、[RawPerfMetrics](https://docs.openvino.ai/2025/api/genai_api/_autosummary/openvino_genai.RawPerfMetrics.html)、[固定 llama.cpp b11810 契約](https://github.com/ggml-org/llama.cpp/blob/b11810/tools/server/README.md)。

## 身分、正確性與資源

每筆 Session 固定權重 SHA-256、量化、工作量雜湊與參數。每個 Run 嵌入裝置快照、Backend 版本、OS、Requested Device、可用裝置、實際執行裝置、Fallback、算子分配與驗證限制，合併承擔 benchmark_devices 表的用途。一般日誌不保存 Prompt、完整 Tensor 或生成內容。輸出只保存摘要與雜湊。

IR 支援 expected 參考輸出，採 atol=rtol=1e-4，沒有參考輸出不能宣稱正確性已驗證。文字只有 Token 與非空輸出檢查，沒有語意品質基準。OpenVINO Tensor 依 EXECUTION_DEVICES 與 profiling 記錄證據；GenAI 與 llama.cpp 沒有完整算子分配證據時維持 verified_inference=false。設定 GPU layers 不等於驗證實際放置。

GPU 僅以 OpenVINO DEVICE_LUID 的 little-endian LowPart／HighPart 與 Windows DXGI LUID 精確對應驅動，不依名稱或序號猜測。無法對應為 unknown。NPU 未出現、相容性不符或 HETERO 請求不會默默改成 CPU。

Benchmark 使用既有 compute lane 排隊，不中斷執行中的聊天／Agent／Team。取得 lane 後才釋放閒置文字模型。ComfyUI 仍運行時拒絕測試，使用者可自行停止。共享 RAM 不與 VRAM 相加。

總時間上限 15–600 秒涵蓋準備、所有裝置與量測，排隊等待不計。程序記憶體上限 512–8192 MiB 由既有 Windows Job Object 限制 committed memory。RAM 峰值來自 GetProcessMemoryInfo 的 PeakWorkingSetSize，二者語意不同。程序 VRAM、NPU 獨立記憶體、溫度與功耗無可靠來源，目前為未知，不宣稱硬性 VRAM 限制。大模型的容量先檢查，逾時、取消與錯誤都清理子程序，並保留已寫入的原始列。

## 儲存、查詢與使用

SQLite user_version 11 新增 benchmark_sessions、benchmark_runs、benchmark_measurements，舊對話與其他表不變。啟動時未完成的 Benchmark 標記 interrupted，不自動重跑。使用 benchmark_id 追蹤 TaskManager 任務，未完成紀錄不能刪除。

運算環境的「進階 · 模型效能測試與歷史」可選模型與裝置、調整上限、確認負載、開始或取消、篩選紀錄及比較。文字提供固定長短兩組工作量。Tensor 依實際輸入形狀提供 1–4 組 JSON 工作量，格式為 `[{"inputs": [[[1,2,3,4]]], "expected": [[[2,4,6,8]]]}]`。

JSON 匯出包含環境、證據與完整原始量測，CSV 包含逐列數值。檔案寫入使用者資料目錄的 exports/benchmarks，介面顯示完整路徑。歷史比較檢查相同權重、工作量、參數、Backend、版本與精度設定，不能確認時顯示「非完全等價比較」。同樣設定仍不能證明不同裝置算子已完整驗證。

## 真實驗收

原始數據見 [benchmark evidence](evidence/benchmark/)。執行 `python benchmark_acceptance.py --source <已安裝 Runtime 的測試資料夾> --profile <獨立驗收資料夾> --output docs/evidence/benchmark --llama-source <含已下載 GGUF 的資料夾> --llama-engine <官方 llama-server.exe>`。不使用一般使用者資料夾。取消與逾時見 benchmark_safety_acceptance.py。

測試硬體為 i5-12500H 與 Intel Iris Xe，OpenVINO 2025.4.1，GPU 驅動 31.0.101.5590。正式 Tensor fixture 為 FP32 512×512 MatMul，Batch 1／8，固定權重及參考輸出，不是舊的四元素功能模型。數據僅描述這些工作量，不可推廣成 CPU／GPU 的通用排名。

E3-D 的 Benchmark 新鮮度、設備推薦與異質並行調度另見 [DEVICE_RECOMMENDATION](DEVICE_RECOMMENDATION.md)，尚未交付不得視為已實作。

### 這次驗收的 Warm 原始統計

單位為 ms，全部從原始 JSON 計算，每組先首次推理及 Warmup 3 次，再正式量測 10 次。CPU 文字測試的短工作量變異較大也原樣保留，不挑選較快的樣本。不同模型與不同工作量不能互相排名。

| 模型 | 裝置 | 工作量 | 次數 | Mean | P50 | P95 | Stddev |
|---|---|---|---|---|---|---|---|
| MatMul FP32 | CPU | Batch 1 | 10 | 0.136 | 0.136 | 0.160 | 0.018 |
| MatMul FP32 | CPU | Batch 8 | 10 | 0.196 | 0.185 | 0.266 | 0.045 |
| MatMul FP32 | GPU | Batch 1 | 10 | 0.511 | 0.460 | 0.770 | 0.160 |
| MatMul FP32 | GPU | Batch 8 | 10 | 0.461 | 0.438 | 0.593 | 0.079 |
| Qwen2.5 Coder 0.5B INT4 OV | CPU | short | 10 | 442.828 | 443.539 | 461.480 | 12.937 |
| Qwen2.5 Coder 0.5B INT4 OV | CPU | long | 10 | 439.101 | 436.446 | 450.907 | 6.327 |
| SmolLM2 135M Q4_K_M GGUF | CPU | short | 10 | 623.699 | 480.895 | 877.854 | 194.474 |
| SmolLM2 135M Q4_K_M GGUF | CPU | long | 10 | 543.590 | 540.564 | 571.250 | 15.811 |
| SmolLM2 135M Q4_K_M GGUF | Vulkan0 | short | 10 | 321.350 | 320.771 | 328.494 | 4.587 |
| SmolLM2 135M Q4_K_M GGUF | Vulkan0 | long | 10 | 329.100 | 328.271 | 334.273 | 3.071 |

完整 Cold 讀取／編譯／首次推理、TTFT、原生 Decode／Prefill、精確 Token 數、RAM 峰值與算子資訊均保存於同目錄的 JSON。llama.cpp 實際版本為 0.7.0-dev build 11810，commit e3797b184，本次正確執行檔可運作，先前其他路徑的應用程式控管阻擋不能代替這次的結果。

安全驗收 PASS，取消後保留 1 筆、15 秒逾時後保留 6 筆原始量測，兩次子程序都已清理，之後重新執行測試成功。NEEDS NPU，NEEDS REMOTE HOST，其他廠牌 GPU 與跨硬體驗收 NOT RUN。這台 Iris Xe 的 GPU 身分以 LUID 對應成功，FP32 IR 的 EXECUTION_DEVICES 為 GPU.0。

| 文字模型 | 裝置 | 工作量 | 原生 TTFT 平均 ms | Decode 平均 token/s |
|---|---|---|---|---|
| Qwen OV | CPU | short | 22.047 | 73.980 |
| Qwen OV | CPU | long | 30.415 | 76.120 |
| SmolLM2 GGUF | CPU | short | 不可取得 | 209.932 |
| SmolLM2 GGUF | CPU | long | 不可取得 | 191.255 |
| SmolLM2 GGUF | Vulkan0 | short | 不可取得 | 126.146 |
| SmolLM2 GGUF | Vulkan0 | long | 不可取得 | 124.429 |

每次生成均為 32 Token。首段文字 Callback 時間另外保存，沒有替代原生 TTFT。整體生成時間包含 Prefill，不能只看 Decode 速率判斷整個請求耗時。Windows 開發安裝包與 CI 來源核對見 [測試報告](TEST_REPORT.md)。
