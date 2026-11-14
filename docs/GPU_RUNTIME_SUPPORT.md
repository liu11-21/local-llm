# GPU Runtime support — 0.8.0 Development

2026-11-14。裝置清單從所選可執行檔取得，不沿用另一 Adapter 的列舉結果。
legacy llama-server 用 --list-devices；llama.app 用 serve --list-devices。

| Provider | 本輪實際狀態 | 使用界線 |
|---|---|---|
| CPU | 真實 SmolLM2、Qwen3-0.6B 推理通過 | CPU 模式配置 0 GPU layers；不是 NPU |
| Intel Vulkan | 此開發主機 Intel Iris Xe / Vulkan0，SmolLM2 推理與排程 Benchmark 完成 | Runtime 回報約 8002 MiB 是共享 heap；依 RAM 安全預算限縮，不稱為 8 GB 專屬 VRAM |
| NVIDIA Vulkan | 維護者提供 RTX 5070 Ti / Vulkan0 的另一主機基準 | 本輪未重跑：NEEDS HARDWARE；不能沿用此主機 Vulkan0 名稱猜硬體 |
| CUDA | 新 Adapter 的公開設備清單暫不啟用 CUDA | NEEDS HARDWARE；需對應 toolkit／driver／Runtime 實測，Vulkan 成功不等於 CUDA |
| OpenVINO GPU／NPU | 保留原獨立 Adapter、IR 格式、工具授權與排程 | 不把 Vulkan provider 當 OpenVINO；NPU 真實推理仍依硬體證據 |
| 多 GPU | 既有排程能按明確設備保留資源 | 每個 llama session --split-mode none，沒有宣稱勾兩張卡就能合併；協同推理 NEEDS HARDWARE |

CPU／自動分層及明確裝置選擇沿用 DeviceChoice／ResourceDemand。自動放置是容量可行性策略，
優先獨立記憶體以減少共享 RAM 壓力，不是依型號猜測最快的效能推薦。
GPU Layers 可自動或手動降低，不能超過目前安全估算；上下文不能超過已知 GGUF 宣告。
DeviceExecution 每個已准入工作建立自己的選定 Adapter，保留 RAM／VRAM／CPU／共享頻寬預算、
互斥鎖及 recommendation receipt。未知設備映射不會憑空合併記憶體。

明確設備派送不悄悄換 CPU；原有 auto 模式在 GPU 啟動失敗且 RAM 可行時會顯示 CPU fallback。
生成統計可保存取樣過的硬體欄位，未知使用率／記憶體保持 unknown。Benchmark 保存 Windows peak RAM；
本輪沒有完成 RTX 使用率、功耗或 NPU 實體量測。

真實原始資料：[CPU／Vulkan smoke](evidence/v080/runtime-cpu-vulkan.json)、
[經 Worker 排程的 Benchmark](evidence/v080/scheduled-benchmark.json)。

裝置名稱與編號對照已由 [真實 Runtime 探測](evidence/v080/runtime-device-probe.json) 保存；
UI 直接列出 Runtime 的名稱／Vulkan 編號與偵測時容量，區分共享／待實體映射，
不把名稱對照當成完整算子／硬體 LUID 的驗證。容量文字明示為偵測時快照，不是當下可無限制配置的 VRAM。
