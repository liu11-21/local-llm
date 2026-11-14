# llama.app Benchmark — 0.8.0 Development

2026-11-14。本輪使用實際 Desktop Worker → BenchmarkService → TaskManager → LlamaBenchmark，
不是只測獨立 CLI。CPU 與 Intel Vulkan0 的同一 session 均 completed，JSON／CSV 匯出成功。
[完整記錄](evidence/v080/scheduled-benchmark.json) 包含模型 hash、Runtime hash／version、
context=2048、32 output tokens、1 warmup、2 measured iterations、short／long 工作量及冷／暖標記。
OS file cache 未清空，因此 fresh process 不能宣稱硬碟冷啟動。

模型為 SmolLM2-135M-Instruct Q4_K_M，並非維護者 RTX 基準的 Qwen3-4B Q4_0。
本輪數字不得與其 Prompt 160.92／Generation 215.09 token/s 直接比較。
此輪能讀到原始 prompt_per_second／predicted_per_second、Token counts 及 process peak RAM；
完整 GPU 算子分配、功耗與部分監控資料仍 unknown，不把 unknown 轉成 0 或最佳推薦。

另以固定 revision／SHA 的 Qwen3-0.6B Q4_0 實測 Thinking：
[原始結果](evidence/v080/qwen-thinking.json)。關閉時只取得正式回答；開啟時 thinking 與正式 content 分開，
使用 b12360 官方 server-common.cpp 真正接收的 `reasoning_budget_tokens`，最多分配 min(256, max_tokens/3)。
曾發現誤用 reasoning_budget 造成只思考無正式回答，已修正並重測；空白正式回答保持失敗，不能冒稱成功。
這是傳輸／預算功能驗證，不保證 0.6B 量化模型的推理品質、嚴格繁體指令服從或任務正確率。

UI 可比較歷史 session／模型／設備並匯出；更換 Runtime 後的新記錄保留其 binary hash 與版本。
不同版本／工作量／量化／context 的資料由既有 comparability 規則標明限制，不直接混成排名。
智慧推薦仍需實測且新鮮的證據、相同條件與有效映射，不按 GPU 型號宣稱最快。

NEEDS HARDWARE：RTX 5070 Ti 上重做 4B、GPU utilization／power、CUDA／其他 GPU／NPU、
兩台實體 Remote Host／Client。NEEDS AUTH：未授權的雲端服務；本輪不呼叫付費 API。

另完成 [真實 Worker 功能驗證](evidence/v080/worker-workflows.json)：繁體字串輸出、原生 Agent 核准後
確實呼叫 models 並保存 tool_requested／tool_result、Qwen3＋SmolLM2 的四節點 Team 保存最終整合回答、
切換 legacy／llama.app 及對話保留。另有 [已開始串流後的真實取消](evidence/v080/worker-cancellation.json)：
工作 cancelled、不提交被取消回答、停止 Runtime 後程序結束。這些是功能測試，不是模型品質評分。
