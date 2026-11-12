# 動態資源策略與 ComfyUI 保留

重用 TaskManager，所有鎖與預算一次准入。舊單工作 lane 1、device 上限 4、control 2；上限不代表允許任意並行。實體 GPU 不明時鎖 gpu:*，同一 Provider／Engine／共享加速器限制仍保留。Benchmark 使用全域本機排他。

隔離模型程序保留 max(1 GiB, 10% 實體 RAM)，安全總容量為剩餘實體 RAM。使用者上限 0 為自動，其他 MiB 值與安全容量取較小者。模型與 Backend 工作空間估計至少 1 GiB、向上取整 MiB，GPU 編譯工作空間仍採保守下限。未知需求不當零，超過總容量或使用者上限拒絕，暫時不足排隊。開始時重新檢查政策，Job Object 使用相同額度。

調度從當前可用 RAM 扣 OS 餘量，再保守扣活躍預留，可能低估並行容量。共享／UMA 已含在 RAM，不另加共享顯存上限；各獨顯 VRAM 分池，不加總。CPU／頻寬為規劃預算，執行緒有上限，未宣稱 OS 級百分比隔離或硬性 VRAM 限制。

管理的 ComfyUI 亦有 Job Object。自動模式取安全容量一半及當前可用安全量的較小值；使用者設定可調整，仍受實體安全容量約束。未確認裝置、記憶體或限制已施行時保持全域保留。

背景讀取受管理服務的 /system_stats 與 /queue，不在 TaskManager 鎖內執行 HTTP。單一獨顯名稱／容量唯一相符、取樣新鮮、程序記憶體及 Job Object 可靠且閒置，才縮為該 GPU 鎖與完整 Job Object RAM 額度。此時無衝突 CPU 工作按剩餘預算准入。占用量不等於已知模型名稱，未知仍標未知。

生成／切換／釋放／異常／未知、多 GPU 不明或 UMA 回到全域互斥；取消後依 queue／程序狀態持有保留。同一服務媒體消費者共用原 compute lane，不被自身保留或舊 Benchmark 鎖死。引擎退出移除保留；快取超過 4 秒保守回退。

[推薦鏈原生驗收](evidence/media/recommendation-native-real.json) 已通過。受控測試覆蓋 >8 GiB 容量計算、使用者上限、未知容量、ComfyUI 閒置／忙碌／UMA 回退、排隊、取消及清理。>8 GiB 大型模型載入與真正 ComfyUI 獨顯／CPU 並行仍 NEEDS GPU。

ComfyUI API 來源：[固定 v0.44.0 server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.44.0/server.py)。
