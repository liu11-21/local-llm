# Device Recommendation · E3-D 待實作

本輪依需求允許的分階段策略，先完整交付 E3-C。E3-D1 的 Benchmark 驅動推薦、Freshness Check、偏好排序，以及 E3-D2 的 CPU／GPU／NPU 異質並行調度尚未交付。既有 runtime_recommendation.py 的能力／資源推薦仍照原流程執行，不會讀取新 Benchmark 決定派送。

Benchmark 提供證據，現有 Recommendation 負責候選與理由，TaskManager 負責執行。後續應擴充既有 runtime_recommendation.py，而不是另外建立矛盾的推薦系統。現在只有使用者選擇裝置並確認執行，compute lane 仍為 1，不宣稱多裝置獨立任務並行。

E3-C 已提供可用的接入資料，包括 Session comparison_key、精確模型 hashes、量化、工作量 SHA-256、參數、Backend 版本、精度設定、GPU LUID／Windows 驅動映射、硬體快照、逐筆 Warm 指標與裝置驗證證據。歷史比較只檢查可比較性，沒有宣稱這些結果永久新鮮，也不自動重跑。

下一批的 Freshness Check 需要把目前模型、權重、後端、裝置身分、驅動、精度與主要參數逐項比對。舊資料保留，缺欄、過期或不相容結果不能標成最新 Verified Benchmark。CPU、GPU、NPU 缺數據都不能按零分排名。

例如本輪 IR MatMul CPU 和 GPU 都有正確性及執行裝置證據，但只能比較該固定 FP32 模型的 Batch 1 或 Batch 8。它不能決定任意文字模型的最佳設備。Qwen OpenVINO CPU 文字有真實 Token／時間量測，但 GenAI 未暴露完整算子放置證據，不能視為完整的裝置驗證。llama.cpp Vulkan 的配置層數也不等於已證明所有算子在 GPU。

使用者偏好、無功耗資料時的省電不確定性、遠端離線、未知費用與傳送同意，仍需下一批實作與測試。HETERO 目前明確拒絕。Remote Benchmark 契約為 unsupported，尚未建立實體雙機效能證據。
