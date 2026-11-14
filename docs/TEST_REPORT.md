# 0.8.0 Development 驗收追蹤

2026-11-14；最終功能來源 1a4503d。下列新結果與後面的 0.7.0 歷史分開。

| 類別 | 本輪結果 |
|---|---|
| Python | 最終乾淨 CI 221 項：220 通過、1 個 Worker 封裝案例建置前 skipped；建置後該案例單獨通過。本機曾有的 7 個 Norton/TLS skip 在 CI 均實跑；另本機授權完整性 6 項通過。 |
| TypeScript／Vite | PASS；既有 bundle-size 建議警告，非失敗 |
| Chromium | PASS；1280／1024／800／650，深淺色；Agent／Team、原生 SSE tool protocol、取消／部分失敗、遠端影音、Benchmark、推薦、作品、版本混用拒絕 |
| 真實 Runtime | 固定官方 b12360 / 2d8a32502、有效 Hugging Face 簽章、CPU／Intel Iris Xe Vulkan0 推理通過；未認證 401、外部 Origin 無 CORS 授權、health 與停止通過 |
| 真實模型／安裝 | Qwen3-0.6B 四執行緒下載／固定 revision／SHA；Runtime 解壓／雙 hash／簽章交易通過，不自動切換 |
| 真實 Benchmark | TaskManager 排程 CPU／Intel Vulkan 同一 session completed；32 Token／2048 context／warmup 1／measured 2，JSON／CSV 成功 |
| Windows CI | [Run 43567386614](https://github.com/liu11-21/local-llm/actions/runs/43567386614) SUCCESS／20 steps；Rust `cargo test --locked` 編譯及 harness 通過（0 個 Rust 單元案例）；NSIS／WebView／Worker 端到端、真正 0.7→0.8 升級、SQLite／備份、捷徑、程序清理、卸載保留資料 PASS。 |
| 安裝包 | 0.8.0 Development、EXE／ZIP hash／GitHub attestation PASS；仍 NotSigned。實際安裝 74 個 PE：67 Valid／7 NotSigned；App／Worker／uninstaller FileVersion 均 0.8.0。SBOM 共 643 packages（含第一方），Notices schema／hash PASS；既有審查紀錄保留。 |
| 真實功能鏈 | Worker 繁體輸出、已核准 models 工具的 native Agent、Qwen3／SmolLM2 混合 Team 四節點、Runtime 切換／歷史保留、串流取消均 completed／PASS |
| 元件信任 | 實際主／子程序與 54 個載入元件逐一檢查，本次全部 Valid；SAC 仍 NOT VERIFIED |
| 其他硬體 | RTX 5070 Ti 4B、CUDA、NPU、其他 GPU、兩台實體遠端仍 NEEDS HARDWARE；付費雲端 NEEDS AUTH |

公開實測：[Runtime](evidence/v080/runtime-cpu-vulkan.json)、[Thinking](evidence/v080/qwen-thinking.json)、
[安裝](evidence/v080/managed-runtime-install.json)、[排程 Benchmark](evidence/v080/scheduled-benchmark.json)。
受控 UI／協定 fixture 與上述真實推理嚴格區分；SAC 模式及完整 Runtime 依賴鏈仍未獨立驗證。
最新安裝包與 SHA 最後記錄於 [V080_DELIVERY](V080_DELIVERY.md)。
[最終 CI 步驟與原始測試節錄](evidence/v080/windows-validation.json)；後續文件提交不改變安裝包來源 1a4503d。

---

## 以下為保留的先前驗收歷史

# 桌面工作台測試紀錄

## Workspace 0.7.0 Development（2026-11-12）

基準 dcab454，V dbdd817、A 04faf59、B 6d673b6、C 626b678、D 0e6bb9f、E e0b1b3a，整合／安裝／UI 修正 d6a5a97、db32081、e794108、4bdeb54、診斷文字 80ce6b5、桌面 CSP 90b1023。版本已提升 0.7.0 Development，第一方 npm／Cargo／Tauri／Worker／UI 一致，main Stable v0.6.2 保留。[完整交付](V070_DELIVERY.md)。

| 狀態 | 驗收 |
|---|---|
| PASS | 本機完整 Python 201 項、194 通過、7 項 Norton 回環 TLS 明確跳過；新增完整 schema 安裝等待測試另通過。乾淨 CI 必須實跑 TLS 及封裝 Worker。 |
| PASS | TypeScript／Vite、Actionlint、完整 Chromium，四尺寸／深淺色／鍵盤／Reduced Motion、Agent／Team、Benchmark、新手流程與遠端媒體回歸。保留約 721 kB 主 bundle 提醒。 |
| PASS | App／Worker 0.7.0 Development 識別、建置 UI、混搭拒絕；有效較新 Workspace 更新可辨識，舊版／等版／不可信發行不提供更新。[來源版本](evidence/v070/version-consistency.json) · [實際 UI](evidence/v070/ui-stability.json)。 |
| PASS | 真實 OpenVINO CPU 推理及採用推薦證據鏈，既有有效 CPU／Intel GPU Benchmark 參與同條件比較，沒有自動重測。[原生紀錄](evidence/v070/recommendation-native-real.json)。 |
| PASS | 現有 Qwen2.5-Coder 0.5B IR 真實 CPU 指定文字生成三次；另三次 GenAI loaded 事件中位 2367.017 ms，含 Runtime／pipeline／tokenizer 初始化。算子放置與量化未完整驗證，無 GPU／NPU 冒稱。[原始基線](evidence/v070/text-cpu-load-baseline.json)。 |
| PASS | 五次 Worker／IPC 基線、2000 對話／500 小 PNG、50 筆聊天分頁與搜尋、有界作品 metadata 查詢；三次真實 React 首頁／受控來源切換。不宣稱整體或推理加速百分比。 |
| PASS | 舊 0.6.2 原始 Worker → 0.7.0 資料庫移轉，18 表及檔案指紋、原檔與備份完整；WAL、空間、損毀、未支援 schema／reader、失敗恢復測試。[資料證據](evidence/v070/upgrade-worker-local.json)。 |
| PASS | 影音協定與合法 VP9／FLAC 的播放、保存及重用；這是受控 Host，非 Wan／ACE-Step 真實生成。 |
| NEEDS GPU | RTX 5070 Ti 不可存取；完整影音模型／GPU 推理、ComfyUI 真實獨顯＋CPU 並行待實機。[診斷](evidence/v070/hardware-diagnosis.json)。 |
| NEEDS NPU | 本機沒有已確認 NPU，沒有 CPU fallback 冒充。 |
| NEEDS REMOTE HOST | 雙實體 Host／Client 長時生成、LAN／VPN 斷線／重啟恢復；已交付 opt-in 驗收工具。 |
| NEEDS CLOUD AUTH | 真實付費 API／Colab 授權，未啟用。 |
| NOT RUN | llama.cpp 探測 0xc0e90002、實際大模型 >8 GiB 載入、llama.cpp 文字模型載入效能、HETERO、正式簽章／Release。 |

Windows 最終 **PASS**：[Run 43238370438](https://github.com/liu11-21/local-llm/actions/runs/43238370438)，來源 `90b10231ff07c9e0cbbcb2c9f95f1326f886cb46`。Python 202 項初跑 201 通過、1 項封裝測試待建置，Worker 建置後該項通過；乾淨 runner 的 TLS 案例均實跑。TypeScript／Vite、Rust／Cargo、Chromium、版本／BUILD／NSIS FileVersion、真正 0.6.2 → 0.7.0 升級、桌面及開始選單捷徑、WebView／Worker、程序收尾、三次啟動與卸載保留資料全部通過。

[下載 Windows x64 0.7.0 Development](https://github.com/liu11-21/local-llm/actions/runs/43238370438/artifacts/13952854621)（Actions 保留 14 天，可能需登入）。解壓後執行 `Local LLM Workspace_0.7.0_x64-setup.exe`，13,237,183 bytes；其餘 JSON／SHA256SUMS 為建置及驗收記錄，不是原始碼下載。未簽章，不是正式 Release。

EXE SHA-256：`be685798f25ce5721b5938d6aa16f068b29c0fd8a161ee78775a4a7377be645c`。

ZIP SHA-256：`2d294a7176904b34d87b3126ad18dd35e99a880e3f2c384ede7912a096401d3e`。已核對官方 artifact digest、BUILD 來源／版本、EXE hash、SHA256SUMS 及實際安裝的 Worker 版本。[建置](evidence/v070/windows-build.json) · [CI／雜湊核對](evidence/v070/windows-verification.json) · [真正舊 Worker](evidence/v070/windows-baseline-worker.json) · [升級 18 表](evidence/v070/windows-upgrade-verification.json) · [卸載後](evidence/v070/windows-upgrade-after-uninstall.json) · [捷徑與啟動](evidence/v070/windows-installer-smoke.json) · [封裝 Worker 基線](evidence/v070/windows-performance-packaged-worker.json) · [原始測試節錄](evidence/v070/windows-test-excerpt.log)。

最終文件／證據提交不更改安裝包應用程式；其 HEAD 見 Git 紀錄及對話交付報告。以下 0.6.2 安裝包均為歷史紀錄，不是本輪下載。

## E3-F、E4–E5 完整整合（2026-11-12）

基準 db6f6f8，版本 0.6.2。F 44a9931、A 50dd40c、B ad15eb2、C 45fb36e、E4-D df213ee、E5 8decf9a、資源識別修正 25c3edd、媒體收尾 4354605。[完整交付與限制](E4_E5_DELIVERY.md)。

| 狀態 | 驗收 |
|---|---|
| PASS | 本機 Python 189 項，182 通過，7 項 Norton 回環 TLS 案例交乾淨 Windows CI。TypeScript／Vite、完整 Chromium 通過，保留 bundle 大小提醒。 |
| PASS | 真實 OpenVINO CPU／Intel GPU 新 Benchmark 共 28 列，正確輸出。舊 GPU LUID 不符先被排除，驗收明確啟動短量測；推薦器未自動執行 Benchmark。 |
| PASS | 同次 UI 排序、採用、推薦 ID／Benchmark ID／Dispatch ID、TaskManager 與真實推理對應，輸出正確。[原始證據](evidence/media/recommendation-native-real.json) 與 [原始量測](evidence/media/benchmark-native-current.json)。 |
| PASS | 動態容量、使用者上限、未知需求、RAM／VRAM／UMA、ComfyUI 閒置與保守回退、取消／清理；>8 GiB 是受控容量測試，不是大型模型載入。 |
| PASS | 圖片／影片／音訊共享協定與資料保存；白名單、參數、來源／Owner 隔離、冪等、續傳、SHA、MIME／內容、34 MiB 串流、取消、空間、排隊配額與保留清理。[協定測試](evidence/media/protocol-tests.json)。 |
| PASS | 真實合法 VP9／FLAC 的 Chromium 解碼、作品保存、歌詞／參數／重用；四尺寸、深淺色、Reduced Motion、鍵盤、精簡聊天與大量作品分頁。[播放器與流程](evidence/media/ui-playback-controlled.json)。此項不是模型推理。 |
| NOT RUN | llama.cpp 本輪原生重測受 Windows 應用程式控制阻擋；沒有降低安全設定。原有功能回歸通過。[環境限制](evidence/media/native-limitations.json)。 |
| NEEDS GPU | Wan 2.1／ACE-Step v1 真實模型生成、其他 GPU、多 GPU及 ComfyUI 獨顯／CPU 實機並行。權重／版本／授權已核對，完整模型及相容 GPU 尚未取得。 |
| NEEDS NPU | 實體 NPU 推理與並行，未將 CPU fallback 或受控狀態當成功。 |
| NEEDS REMOTE HOST | 雙實體 Windows 的長時生成、LAN／VPN 與斷線恢復。協定／TLS 與合法媒體傳輸另外驗證。 |
| NEEDS CLOUD AUTH | 未呼叫付費 API 或外傳真實提示詞。 |
| NOT RUN | >8 GiB 大模型實際載入、單模型 HETERO、main／正式 Release／簽章變更。 |

Windows CI **PASS**：[Run 43200374886](https://github.com/liu11-21/local-llm/actions/runs/43200374886)，安裝包來源 `4354605004c7d8db1f88bca8e3cc1ef38b135b55`。乾淨 Windows：Python 189 項初跑 188 通過、1 項封裝測試待建置，Worker 建置後該項單獨通過；7 項本機 Norton TLS 限制案例在 CI 均實際執行。Chromium（含 E4/E5）、TypeScript／Vite、Rust／NSIS、實際安裝／桌面及開始選單捷徑／WebView 與 Worker 啟動／程序收尾／卸載保留資料皆通過。

[下載 Windows x64 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/43200374886/artifacts/13934754399)（GitHub Actions artifact，保留 14 天，下載可能需登入）。解壓後執行 `Local LLM Workspace_0.6.2_x64-setup.exe`，13,226,426 bytes。它是可安裝的 EXE，壓縮檔同時含 BUILD.json 與 SHA256SUMS.txt；版本維持 0.6.2，未簽章、未建立正式 Release。

安裝 EXE SHA-256：`885a9d3723c5eecd8c2db9277b2f1122648e665d8af2b92e952b2d5faae2d8a3`。

下載 ZIP SHA-256：`b38f8dfcb2fa21011ece176839ac265d526632b00ae8710815c238b13bee075b`。已對照 GitHub artifact digest、BUILD.json 的來源／版本／EXE 雜湊及 SHA256SUMS.txt，全部一致。[建置記錄](evidence/media/windows-build.json)、[驗證及 CI 步驟](evidence/media/windows-verification.json)、[原始測試節錄](evidence/media/windows-test-excerpt.log)。

此後的最終提交只增加文件、截圖與證據，不改動安裝包內程式碼。文件 HEAD 以本交付文件的 Git 提交及對話交付報告為準；下方 E3 安裝包均屬歷史紀錄。

## E3-D1–D5 智慧運算完整交付

基準 40ea060，版本 0.6.2。D1 9559ef8、D2 1f24df4、D3 b75dd5f、D4 14493a9，D5 `a4343f5` 為原生驗收、回歸修正及文件；`1d0da88` 修正公平排程，`4bd3f17` 修正 ComfyUI 消費者預留，`ceba11e` 隔離 Agent 測試，最終安裝包來源亦為 `ceba11e`。規則見 [DEVICE_RECOMMENDATION](DEVICE_RECOMMENDATION.md)，資料見 [原生驗收](evidence/device/acceptance-real.json)、[完整推薦](evidence/device/recommendation-real.json)、[實際執行](evidence/device/dispatch-runs-real.json)。

| 狀態 | 具體驗收與界線 |
|---|---|
| PASS | Freshness／Comparability 分開；權重、Backend／binary、Driver、裝置、量化、精度、Batch／採樣／EOS、工作量、時間、缺列、Partial、未知放置、CPU Fallback 與 NPU 未實測均有測試。時間只是更新建議，未自動重跑。 |
| PASS | 同模型／條件群組才比較 Warm、TTFT、Decode 或模型啟動；缺失不當零。偏好與隱私、未知費用、離線、UMA／獨立 VRAM、過期取樣、NPU 不相容及總容量檢查有受控案例。啟動成本可改變 Warm 延遲的選擇。 |
| PASS | 同一 TaskManager 測試 CPU／GPU、不同 GPU、CPU／受控 NPU、RAM／VRAM 不足、共用頻寬、同 Engine／Provider、未知 GPU 全域鎖、ComfyUI 預留、取消、逾時、關閉及恢復。受控並行不是實體 NPU 加速。 |
| PASS | Team child Task 的獨立模型／輸入、並行草稿、依賴整合、父取消傳遞、未授權遠端成員不執行。Agent 外部工具資料須計畫層級同意，金鑰遮蔽與一次核准仍生效。排隊後模型變更拒絕。 |
| PASS | 正式 Worker OS 檔案鎖測試，第二個 Worker 無法重置活躍資料，第一個仍可服務，關閉後鎖可重新取得。SQLite 12 保留舊對話、Agent、Team、Benchmark、作品及遠端資料。 |
| PASS | 原生流程 A：既有真實 SmolLM2 同條件 Benchmark → 使用者確認 Vulkan → TaskManager → 新隔離程序 → 非空回答及執行證據。此推薦限固定 32 Token 參考，Vulkan 配置層數不是完整算子分配。 |
| PASS | 原生流程 B：CPU llama.cpp 與 Intel GPU OpenVINO 同時有兩個存活 PID，含觀察時間；兩工作完成，FP32 MatMul 參考輸出相符，GPU.0 推理證據保存。不是只看 queued／running 標籤。 |
| PASS | 原生流程 C：無 NPU 且 Qwen 文字模型 npu_candidate=false，強制要求 NPU 被拒絕，沒有新增 CPU Fallback 工作或下載替代模型。 |
| PASS | 真實 OpenVINO CPU Agent 核准計畫後完成；CPU／Vulkan Team 獨立節點與最後整合完成。小型模型的語意品質不由此執行驗收評分。 |
| PASS | 真實取消後程序與 Scope 清理，後續 GPU 工作成功；應用關閉中止原生程序，任務為 interrupted，沒有殘留 Scope。 |
| PASS | 本機 GPU blob 重用缺陷已定位及修正。兩個新快取皆成功、兩次跨程序重用皆 0xC0000005，8 GiB 上限下峰值約 0.78 GB。現採私有 session cache，重啟／恢復成功，不刪舊快取。[原始故障重現](evidence/device/gpu-cache-diagnostic.json) 的 FAIL 是修正前診斷，非目前正常流程驗收結果。 |
| PASS | TypeScript／Vite 建置與完整 Chromium 回歸，保留既有 bundle 大小提醒。共用 Picker 四尺寸、深淺色、長名稱、缺失／過期／未知證據、離線、手動覆寫、無自動派送、鍵盤及 Reduced Motion。既有 Agent／Team、Onboarding、遠端圖片、作品與 Benchmark 流程通過。 |
| PASS | 真實 React 共用推薦→採用 Vulkan→聊天→此次新 Dispatch ID→非空畫面回答→任務證據；深色、650px 淺色與實際證據畫面位於 ui-preview/device。 |
| NEEDS NPU | Intel NPU 實體推理／多設備並行、AMD／Qualcomm Adapter 尚無實體驗收，不以模擬或列舉代替。 |
| NEEDS GPU | 其他廠牌 GPU、多 GPU 實機；未知 Vulkan 映射仍保守互斥，沒有以受控裝置測試代替實體驗收。 |
| NOT RUN | HETERO 單模型分割仍拒絕。CPU／頻寬屬規劃預算，未宣稱 OS 級百分比隔離；可靠程序 VRAM／功耗／溫度不足時未知。 |
| NEEDS REMOTE HOST | 雙實體 Windows 的 GPU 文字／圖片與 LAN／VPN 驗收未取得硬體。既有回環 TLS、配對與來源同意回歸保留。 |
| NEEDS CLOUD AUTH | 只有受控文字 Provider／同意測試，未啟用付費雲端或自動外傳。 |
| NOT RUN | 正式 Release、Authenticode、防毒申訴與 main 變更，本輪僅開發分支安裝包。 |

本機最終 Python 共 173 項，167 項通過；6 項受 Norton 回環 TLS 憑證替換影響的案例交由乾淨 Windows CI 執行。修正並測試了長 CPU 等待不阻擋無衝突 GPU，以及 ComfyUI 常駐保留可供本地／Host 圖片序列使用，其他引擎／Benchmark 仍維持互斥。

首輪 Windows CI 的遠端圖片回歸發現 ComfyUI 消費者被自身常駐預留阻擋，故障已由 `4bd3f17` 修正。舊 run 43048074372 失敗，43048930495 已取消，均不作通過證據。`43051388362` 已通過全部回環 TLS／遠端圖片案例，但 10 項舊 Agent 測試依賴開發機已有引擎而失敗；`ceba11e` 補上隔離引擎資料及缺少引擎的拒絕案例，另外以只允許暫存目錄引擎的查詢執行 21 項 Agent／對話案例通過，正式預檢未放寬。

**Windows CI PASS**：[工作流程 43052048060](https://github.com/liu11-21/local-llm/actions/runs/43052048060)，固定應用程式來源 `ceba11ef0a3d6e398ea444197353b274388f3641`。173 項先通過 172 項，僅尚未建置的 PackagedWorker 略過，封裝後該項另外通過；本機略過的 6 項 TLS 案例在此實際執行通過。TypeScript／Vite、完整 Chromium、Tauri Windows x64、安裝／桌面與開始功能表捷徑／WebView Worker 啟動／程序清理／卸載保留資料均 PASS。

[本輪 Windows 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/43052048060/artifacts/13869791964) 保留 14 天。解壓後執行 `Local LLM Workspace_0.6.2_x64-setup.exe`，13,192,187 bytes。版本維持 0.6.2，未簽章，未建立正式 Release。EXE SHA-256：`23957b5a5c082e7fdfcdcde4a57ce8bd500903643da6b122af507a7bb4b1c78f`。

已下載核對 GitHub Artifact Digest、BUILD.json 提交／版本／EXE 雜湊，以及 SHA256SUMS.txt。見 [BUILD](evidence/device/windows-build.json) 與 [下載驗證](evidence/device/windows-verification.json)。最後文件提交不改變安裝包程式碼；來源以此固定 SHA 為準。

## E3-C1–C3 Benchmark

基準 7ed3a75，版本維持 0.6.2。Core 33917d9、真實推理及證據 62d8c23，介面接續獨立提交。E3-D1／D2、E4／E5 未交付。[方法與完整統計](HARDWARE_BENCHMARK.md) · [原始資料](evidence/benchmark/)。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | 本機 Python 共 131 項，125 通過，6 項 Norton 回環 TLS 替換案例略過並交由 Windows CI 執行。新增統計、範圍、確認、資源預檢、取消／逾時區分、逐筆保存、中斷恢復、隱私、匯出、比較、完整性與排隊取消測試。 |
| PASS | TypeScript／Vite 正式建置，保留既有 bundle 大小提醒。完整 Chromium 回歸涵蓋既有聊天、Agent／Team、遠端圖片、首次使用、OpenVINO 與新增 Benchmark。 |
| PASS | Benchmark 受控資料測試四種尺寸、深淺色、鍵盤與 Reduced Motion、長名稱、無 GPU／NPU、無紀錄、進行中、未知指標、失敗、非等價比較、確認與取消。數字不作為真實硬體證據。 |
| PASS | 真實 React → IPC → TaskManager → OpenVINO CPU Benchmark，0 Warmup + 2 measured × 2 工作量，寫入 6 列。另驗證 SQLite 真實歷史、比較、JSON／CSV 檔案匯出與四尺寸雙主題，畫面位於 ui-preview/benchmark。 |
| PASS | 正式原生量測每組 first 1 + warmup 3 + measured 10，OpenVINO FP32 MatMul CPU／Iris Xe GPU 共 56 列並全部通過參考輸出；Qwen CPU 文字 28 列；SmolLM2 llama.cpp CPU／Vulkan 共 56 列。OpenVINO 文字精確輸出 32 Token、原生 TTFT／TPOT；llama.cpp 保存原生 usage／timings。 |
| PASS | OpenVINO GPU EXECUTION_DEVICES=GPU.0，LUID 精確對應 00000000_0001298d、驅動 31.0.101.5590。文字 GenAI 與 llama.cpp 完整算子放置仍 unknown，未誇大 verified_inference。 |
| PASS | 真實子程序取消保留 1 列、15 秒逾時保留 6 列，程序清理完成後重測成功。Windows Job Object 限制 committed memory，RAM 峰值為工作集，沒有宣稱硬性 VRAM 限制。 |
| NEEDS NPU | 本機只回報 CPU／GPU，沒有實體 NPU 推理驗收。AMD／Qualcomm Adapter 與多設備 HETERO 未實作。 |
| NOT RUN | 其他 GPU、多 GPU、跨硬體效能驗收、可靠程序 VRAM／功耗／溫度。Benchmark 驅動推薦、新鮮度與異質並行調度待 E3-D。 |
| NEEDS REMOTE HOST | 遠端 Benchmark 契約目前 unsupported，實體雙機未測。 |
| NOT RUN | 正式 Release、簽章、防毒申訴與付費雲端。本次只產出開發分支安裝包。 |

**Windows CI PASS**，[工作流程 43025479340](https://github.com/liu11-21/local-llm/actions/runs/43025479340) 對應應用程式提交 `79e5415ff1db2028934ccd84dc848de39ed715b4`。131 項測試先通過 130 項，僅尚未建置的 PackagedWorker 略過；建置後該項另外通過。本機略過的 TLS 案例均在乾淨 runner 執行。Worker 封裝、完整 Chromium 回歸、Tauri Windows x64 安裝包、安裝／啟動／卸載 Smoke 均通過。

[開發安裝包 Artifact](https://github.com/liu11-21/local-llm/actions/runs/43025479340/artifacts/13857685529) 保留 14 天，解壓後執行 `Local LLM Workspace_0.6.2_x64-setup.exe`。13,131,795 bytes，未簽章，沒有建立正式 Release。EXE SHA-256 為 `2be2225c39f7fcb53a7206d3e8d8c824f6a7b01e9c9bb8da1f6045fbc16b576c`。

已下載核對 GitHub Artifact Digest、BUILD.json 的提交／版本／EXE 雜湊與 SHA256SUMS.txt。證據見 [BUILD](evidence/benchmark/windows-build.json) 與 [下載驗證](evidence/benchmark/windows-verification.json)。本輪最後的文件／截圖提交不改變安裝包程式碼，安裝包來源以此處固定 SHA 為準。

## E3-A、E3-B 的資源與 OpenVINO Adapter

基準 `14a8fff`，版本 `0.6.2`。資源契約提交 `02709de`，Adapter `6f7975f`，路徑隔離 `f6e9f6a`，Windows 匯入修正及 UI／TLS 測試 `354a712`，顯存證據修正 `7fd3b42`，本機狀態與診斷 `b00e37d`，獨立驗收資料及保存等待 `52f69ca`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | 本機最後全套 Python 共 120 項，114 項通過，6 項受 Norton 回環 TLS 替換影響的案例交由 Windows CI 執行。TypeScript／Vite 建置通過，保留既有 bundle 大小提醒。 |
| PASS | 資源測試區分 NVIDIA／AMD／Intel 受控裝置、獨立／統一記憶體、無 GPU、多 GPU、共享上限、過期與未知值、驅動矛盾數值。推薦採用同一量測契約，容量達到估計仍須後端載入驗證。 |
| PASS | 真實 Windows 空白資料夾完成 84,376,901 bytes 的固定官方套件下載及 SHA-256 驗證，獨立 Python 安裝 OpenVINO，Core 回報 CPU、GPU。測試期間修正進度 callback 及 Windows 系統 TLS 傳輸相容性。 |
| PASS | 真實 OpenVINO CPU、Intel Iris Xe GPU 執行固定 IR 張量模型，輸出符合 `[2,4,6,8]`，後端分別回報 CPU、GPU，保存 profiling 與模型雜湊。這是單次功能測試，未做效能等價比較。 |
| PASS | `52f69ca` 的實際驗收紀錄保存在文件中。CPU 單次推理 0.252 ms，GPU 1.077 ms，皆未包含編譯與載入。資料是功能核對證據，不構成冷／暖、精度或吞吐量 Benchmark。NPU 未由 Core 回報，明列 NEEDS NPU。 [CPU 原始結果](evidence/e3/openvino-cpu.json) · [GPU 原始結果](evidence/e3/openvino-gpu.json) · [NPU 狀態](evidence/e3/openvino-npu.json) |
| PASS | 真實 React → IPC → TaskManager → 隔離 OpenVINO GenAI 的 CPU 文字生成與對話保存。測試模型為官方 OpenVINO/Qwen2.5-Coder-0.5B-Instruct-int4-ov，revision `339876973306da551969e2d88991b7053be2029c`。以 LFS SHA-256／Git blob 身分核對下載，保留原始碼來源。模型為 INT4 asymmetric，因此未列入本輪 NPU 文字候選。 [模型來源](https://huggingface.co/OpenVINO/Qwen2.5-Coder-0.5B-Instruct-int4-ov/tree/339876973306da551969e2d88991b7053be2029c) |
| PASS | 受控測試涵蓋安裝失敗與重試、缺少 Provider、格式錯誤、模型變動、NPU 量化條件、CPU fallback 證據、程序 IPC、取消、失敗後再次執行、移除保留模型、私有提示詞不進例外及推理紀錄清理。 |
| PASS | Chromium 四種尺寸與深淺色的既有 Agent／Team／遠端圖片回歸。新增受控 OpenVINO 選擇、compute 排程、本機隱私政策及聊天保存，另執行真實 CPU 聊天並截圖。 [畫面與前後比較](UI_DESIGN.md) |
| PASS | `52f69ca` 通過 Windows Server 2022 x64 的 Python、HTTPS 與系統 TLS 憑證拒絕、封裝 Worker、Chromium、NSIS、每使用者安裝、捷徑啟動和卸載。已下載並核對 GitHub ZIP digest、建置提交、0.6.2 版本及 EXE SHA-256 `e95ee52f3f226dfb229747ae756aa147bcfa81171ca10afbd8d7780a598590bc`。 [Windows CI](https://github.com/liu11-21/local-llm/actions/runs/42961488684) · [Windows 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42961488684/artifacts/13830205244) |
| FAIL | 首輪 Windows CI 的暫存資料夾具有上層別名，匯入來源未正規化父層，五項模型測試失敗。修正只正規化父層，保留來源資料夾與檔案的連結拒絕。 [失敗紀錄](https://github.com/liu11-21/local-llm/actions/runs/42959478650) |
| FAIL | 本機狀態文字修正後，舊的瀏覽器定位器同時匹配回答來源和頁尾，觸發 strict mode。`52f69ca` 將等待條件限制在已保存訊息的來源區域，並核對送出按鈕重新出現。 [失敗紀錄](https://github.com/liu11-21/local-llm/actions/runs/42960896968) |
| NEEDS NPU | 本機未回報 NPU。Intel NPU 的真實 IR／文字推理和驅動條件待硬體驗收，提供 `openvino_acceptance.py` 重跑。 |
| NEEDS GPU | NVIDIA／AMD 實體資源監控，其他 Intel GPU 型號及真實 NPU 的記憶體行為。 |
| NEEDS REMOTE HOST | 雙實體電腦的 LAN／VPN、文字／圖片 GPU 生成仍待原有驗收。 |
| NOT RUN | E3-C 正式 Benchmark、E3-D 智慧分工／推薦／HETERO、E4 遠端影片及音樂、E5 情境首頁／引導完成提示／作品網格。AMD／Qualcomm 保留契約，尚無推理 Adapter。 |

GenAI 的文字生成契約已通過，實際逐算子裝置分配維持未驗證。任何 CPU 生成或 Provider 列舉均未記為 NPU 成功。

## Batch 4E＋NPU 的 E1、E2

基準 `38f7406`，程式版本 `0.6.2`。E1 提交 `ef5ae88`，E2 提交 `60810ca`，關閉清理及硬體驗收腳本 `e2e9c76`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | 本機 Python 共 103 項測試，98 項通過，5 項 HTTPS 回環案例由 Windows CI 執行。TypeScript／Vite 建置與差異格式檢查通過，保留既有的前端 bundle 大小提醒。 |
| PASS | 任務健康分離、圖片可用而文字引擎失敗、能力過期和隱私限制的回歸。Client 重啟後恢復私人提示詞、排除提示詞、種子、Host／Job 來源和提交時間，並保存作品狀態。第 8 版資料庫升級到第 9 版保留既有對話與作品。 |
| PASS | 受控硬體測試涵蓋 Intel／AMD／Qualcomm NPU、驅動錯誤、無 NPU、清單未知、Provider 缺失及初始化失敗、多 GPU 計數器歸屬、專用與共享記憶體分離、未知數值、快取、查詢失敗和關閉清理。 |
| PASS | Chromium 已驗證 1280×900、1024×768、800×600、650×720 的深淺色、長名稱、鍵盤、reduced motion、NPU 已偵測／未知，以及先前 Agent／Team／作品庫功能。新手引導可直接選遠端圖片，並在外傳確認後取回校驗結果與作品來源。模型與遠端傳輸採受控資料。 [實際截圖與比較](UI_DESIGN.md) |
| PASS | 本機真實 Intel Iris Xe，驅動 `31.0.101.5590`。DXGI 回報專用顯存 134,217,728 bytes，共享上限 8,390,934,528 bytes。三次驗收最後一次 GPU 3.5%，專用顯存已用 0 bytes，共享已用 547,319,808 bytes。取樣耗時中位數 2.20 ms，不含背景裝置清單查詢。 [監控畫面](ui-preview/batch4e/hardware-runtime-real.png) |
| PASS | 本機 PnP 未偵測到 NPU。既有工作程序環境未安裝 OpenVINO／ONNX Runtime，明確顯示缺失。可用 `hardware_acceptance.py` 在其他電腦保存偵測證據。 |
| PASS | `e2e9c76` 通過 Windows Server 2022 x64 CI 的 Python、受控 HTTPS、封裝 Worker、Chromium、NSIS、每使用者安裝、捷徑啟動與卸載。下載後核對 GitHub ZIP digest、建置提交、0.6.2 版本及 EXE SHA-256 `efe244d49340ab780134158a80ca968396e1cf9d14d33d5f4ec7375a6b0f9588`。 [Windows CI](https://github.com/liu11-21/local-llm/actions/runs/42949339821) · [開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42949339821/artifacts/13824596508) |
| NEEDS GPU | NVIDIA／AMD 的實體 GPU 監控與多實體 GPU，尚待硬體驗收。 |
| NEEDS NPU | Intel／AMD／Qualcomm 實體 NPU 的裝置及 Provider 查詢，尚待硬體驗收。 |
| NEEDS REMOTE HOST | 雙實體電腦的 LAN／VPN 與真實 GPU 生成，沿用既有待驗收項目。 |
| NOT RUN | E3 的 NPU Engine Adapter、模型載入與推理、CPU／GPU／NPU 及異質效能 Benchmark，E4 遠端影片／音樂，E5 情境首頁、引導操作列與作品網格。現有 GPU 取樣耗時只反映監控成本。 |

Windows 本機的 Norton TLS 替換問題仍適用，5 項 HTTPS 回環案例交由乾淨的 Windows CI 執行。新套件仍保留版本 0.6.2，安裝產物以建置提交識別。

## Batch 4E-1／4E-2／4D-1–3

程式基準 `1b47887`，版本 `0.6.2`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | Windows 本機 Python 測試共 91 項，86 項通過，5 項 HTTPS 回環協定測試由 CI 執行。本機案例涵蓋推薦與隱私、任務所有權、重啟與冪等、客戶端任務 ID 持久化、排隊上限、流程白名單、續傳及 SHA-256 驗證。 |
| PASS | Chromium 驗證重新開啟引導、下載失敗後重試、第一次文字回答保存。另驗證選擇遠端圖片主機、核對目的地、取回校驗檔案、作品庫來源，以及先前四種尺寸與兩種主題。模型與傳輸測試採用受控資料。 [實際 UI](UI_DESIGN.md#首次使用與遠端圖片) |
| PASS | 本機 Windows 用真實 ComfyUI 和 SD 1.5 CPU 生成 256×256 PNG。經 Host 的圖片工作程式建立 129,063 bytes 結果與 SHA-256。此案例驗證生成端，HTTPS 則另有受控測試。 |
| PASS | `1209427` 通過 Windows Server 2022 x64 CI，包括 Python、受控 ComfyUI 的真實 HTTPS 回環與跨裝置權限測試、Chromium、NSIS 打包、每使用者安裝、捷徑啟動與卸載。已下載 ZIP，核對 GitHub 公布的 SHA-256、`BUILD.json` 的提交與版本，以及 EXE SHA-256 `884af1f3dc8d5f21d784b6cc4ab807ba20ed6de5e95141276eee9d93eb84569b`。 [Windows CI](https://github.com/liu11-21/local-llm/actions/runs/42834205770) · [Windows 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42834205770/artifacts/13773116908) |
| NEEDS WINDOWS | 這台 Windows 嘗試啟動真實 llama.cpp 時被應用程式控制原則封鎖，錯誤 `WinError 4551`。首次引導已走到受控回答保存。實際新裝文字推理需要允許執行的 Windows 電腦。 |
| NEEDS REMOTE HOST | 兩台實體電腦跨 LAN 或 VPN 傳送圖片仍待驗收。 |
| NEEDS GPU | 真實遠端 GPU 生成和即時 GPU／VRAM 資源監控仍待實作或驗收。 |
| NOT RUN | 遠端影片及音樂、GPU／VRAM 即時採樣及情境化首頁尚未交付。 |

## Batch 4A–4C

基準 `a2d0bdb`，版本 `0.6.2`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | Windows 本機 83 項 Python 測試中 79 項通過，4 項 TLS 網路回環案例由 Windows CI 執行。新案例涵蓋引擎和模型缺少、離線、外部政策、未知費用、ComfyUI 預檢、私人位址、受保護私鑰、憑證重用及更新撤銷。 |
| PASS | Chromium 在 1280×900、1024×768、800×600、650×720 驗證深淺模式、長名稱、錯誤、鍵盤焦點、reduced motion、側欄收合、即時資源、Host 自動 TLS、同意對話框及既有 Agent／Team／作品庫。確認 Esc 未送出，核准只提交一次並保存一則回答。 [實際畫面](UI_DESIGN.md#batch-4a4c-工作台與任務準備) |
| PASS | 自動產生的憑證與 DPAPI 保護密碼通過本機 TLS 記憶體握手。瀏覽器同時驗證 Host 建立邀請及顯示指紋。 |
| PASS | `9f0c31d` 通過 Windows CI 的 Python、Worker 封裝、Chromium、NSIS 建置、安裝及卸載。已下載並核對 GitHub ZIP SHA-256、建置提交與安裝 EXE。EXE SHA-256 為 `d9af8ccb9028ab4ec0212f167b92b10b192a50147eb594a5836624c1b8e5cc7e`。 [Windows CI](https://github.com/liu11-21/local-llm/actions/runs/42822400834) · [開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42822400834/artifacts/13767404197) |
| NEEDS REMOTE HOST | 兩台實體電腦之間的自動 TLS、私人網路與斷線行為仍待驗收。 |
| NEEDS GPU | 實體遠端 GPU 推理與即時 GPU／VRAM 用量的驗收。 |
| NOT RUN | 4D 遠端媒體與持久任務、4E 完整新手引導及進一步跨 Runtime 整合。 |

## 第三階段 Batch 3D–3E

程式基準 `678d04b`，版本 `0.6.2`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | Windows 本機 Python 共 77 項測試，73 項通過，4 項 TLS 回環案例移至乾淨的 CI 環境。本機 DPAPI、記憶體 TLS 正確與錯誤 IP 身分、SSE 重連不重複輸出、推薦政策及權重驗證失效均通過。 |
| PASS | Windows CI 的受控 Host／Client 測試涵蓋 TLS、無授權拒絕、協定版本、配對、撤銷、配對持久化、同一任務重送、任務所有權和取消。推理使用受控的模型回應。 [第一輪 Host／Client CI](https://github.com/liu11-21/local-llm/actions/runs/42771568190) |
| PASS | Chromium 深淺模式，1280×900、1024×768、800×600、650×720。測試啟用與停止 Host、長主機名稱、建立邀請、無效邀請、能力比較，以及既有 Agent、Team 與創作。 [實際 UI](UI_DESIGN.md#batch-3d3e-私人遠端運算) |
| PASS | `1704f45` 通過 Windows Server 2022 x64 CI，包括受控 HTTPS 配對後從桌面聊天提交、儲存回答來源、封裝與安裝／卸載。 [Windows CI](https://github.com/liu11-21/local-llm/actions/runs/42817141781) |
| PASS | 已下載 ZIP，核對 GitHub 的 ZIP SHA-256、`BUILD.json` 提交和安裝 EXE。EXE SHA-256 為 `17454342b4f122c662132efe04be130395f1b437fe6f073b2fc0bed411b0db6a`。 [Windows 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42817141781/artifacts/13764692723) |
| NEEDS REMOTE HOST | 兩台實體 Windows 電腦之間的 LAN／VPN、防火牆、TLS、長時間斷線和重連驗收。 |
| NEEDS GPU | 遠端實體 GPU 上的 llama.cpp 載入、生成效能及 CPU 回退需要另行驗收。 |
| NEEDS CLOUD AUTH | 推薦只讀取能力，Colab Enterprise 及雲端推理的付費路徑沿用既有契約，這次沒有提交測試推理。 |

本機 Norton Web/Mail Shield 替換了回環服務的測試 TLS 憑證，預期的身分驗證因此拒絕連線。CI 使用未經替換的測試憑證執行實際 HTTPS 協定測試。

## 第三階段 Batch 3A–3C

基準為 `d39afbf`，開發安裝包版本為 `0.6.2`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | 64 項 Python 測試。涵蓋 Team 交付與審查狀態、必要依賴、工具參數及核准、權限、逾時後的執行槽、ComfyUI 權重清單、SHA-256、磁碟不足、取消、續傳、同名保護、節點預檢、舊作品、作品篩選、安全原檔路徑及媒體中繼資料。 |
| PASS | TypeScript／Vite 建置及 Chromium UI 測試。涵蓋四種尺寸及深淺模式、Team 部分交付、創作安裝摘要、作品庫搜尋、排序、類型與模型篩選、參數與種子回填。Team 回應由可控 SSE 測試端點提供。 [實際介面截圖](UI_DESIGN.md#batch-3-創作與作品庫) |
| PASS | 真實 Windows CPU。重新計算既有 SD 1.5 權重的 SHA-256，檢查 ComfyUI 節點，從桌面 Worker RPC 提交並透過 TaskManager 完成 256×256 PNG。SQLite 作品庫可查到尺寸、種子及真實 ComfyUI 任務 ID。 |
| PASS | 真實 Hugging Face 安裝下載。Wan 2.1 VAE 以四個執行緒下載，實際大小 253,815,318 bytes，通過固定 revision 的 SHA-256。 [Wan 2.1 權重](https://huggingface.co/Comfy-Org/Wan-2.1/tree/123acf1cc74bccbb9bfff8ac1ee72edc08c2341d/split_files/vae) |
| PASS | `eb5cba2` 通過 Windows Server 2022 x64 CI，含 Worker 封裝、Chromium、Tauri NSIS、靜默安裝、桌面及開始功能表捷徑、WebView2 啟動、關閉和卸載保留資料。 [Windows CI](https://github.com/liu11-21/local-llm/actions/runs/42765375251) |
| PASS | 已下載開發安裝包，核對 GitHub 的 ZIP SHA-256、`BUILD.json` 提交與安裝 EXE SHA-256。EXE 校驗值為 `182b61cd0e7f9b78d5fb5be306c55922d27045611bd79dd6d68e909f4cafba6c`。 [Windows 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42765375251/artifacts/13739622530) |
| NEEDS GPU | Wan 2.1 實際影片生成及 ACE-Step 實際音樂生成仍待支援的 GPU 環境驗收。 |
| NOT RUN | Wan 2.1 其餘兩個權重及 ACE-Step 完整下載、新版簽章、正式 Release、付費請求。3D 遠端 Host／Client 及 3E 能力契約尚未實作。 |

## 第三階段 Batch 2

開發基準為 `c83dfca`，工作台版本為 `0.6.2`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | 51 項本機 Python 測試。新增契約、重複工具、輸入與輸出 Schema、未授權拒絕、逾時和取消。計畫測試確認多份計畫互不覆蓋、版本與契約變更使舊計畫失效、過期及重開後不重播。 |
| PASS | Agent 測試確認等待核准時其他本機工作可執行，且只有原請求 ID 可核准。拒絕與取消不讀取工具。偽造的 PowerShell 請求、額外路徑參數和不合法 JSON 均被拒絕。達上限會保留先前事實。 |
| PASS | Team 測試驗證三種模式各自的上下文和依賴輸入、循環與缺少依賴拒絕、審查失敗保留初稿、共用運算槽、取消、設定讀寫及外部授權拒絕。 |
| PASS | TypeScript／Vite 建置。Chromium 保留 1280×900、1024×768、800×600、650×720 的深淺版面測試，另經真實 Worker 及可控的本機 HTTP／SSE 端點驗證 Agent 計畫、逐次核准、兩種工具協定、時間軸、錯誤和取消，以及 Team 角色、依賴、審查、部分失敗和取消。 [實際介面截圖](UI_DESIGN.md#batch-2-工作流程) |
| PASS | `3417b39` 通過 Windows Server 2022 x64 CI。Python、Worker 封裝、Chromium 版面及工作流程、Rust／Tauri 建置、桌面和開始功能表捷徑、WebView2 啟動與關閉 Worker、卸載保留使用者資料均通過。 [Windows CI](https://github.com/liu11-21/local-llm/actions/runs/42616269570) |
| PASS | 已下載並核對開發安裝包 ZIP SHA-256、`BUILD.json` 提交與 EXE SHA-256。EXE 校驗值為 `013833d63e2ed4c9100055d0605f4b42570a0a08da8389f67b14dee4a41fca14`。 [Windows 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42616269570/artifacts/13673231196) |
| NEEDS WINDOWS TEST | 這台 Windows 的真實 llama.cpp 啟動在推理前失敗，Worker 收到程序退出代碼 `3236495362`。原生工具能力、結構化輸出的實際品質及不同本機模型的協作效果需另行驗收。 |
| NEEDS CLOUD AUTH | 外部 Team 端點的授權拒絕已有回歸測試。實際遠端 SSE、服務額度及資料傳送需在授權環境驗收。 |
| NOT RUN | 付費請求、雲端 Agent、任意第三方工具、正式簽章和正式 Release。 |

`npm run test:layout` 在 Chromium 使用隔離資料目錄和可控的本機協定端點。它測試正式的 Worker 任務、權限與儲存路徑。模型回答是固定測試回應。

## 第三階段 Batch 1

基準為 `da4ee33`，工作台版本維持 `0.6.2`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | 33 項本機 Python 測試。使用可控制的 HTTP 回應，在 Windows 子程序中實際強制退出，驗證重開後保留已完成區段且不重抓、取消不發布、上游校驗不符、同名鎖、清理範圍、來源紀錄隨檔案變更而失效，以及引擎健康狀態和媒體預檢。 |
| PASS | 實際同時下載公開的 `stories260K.gguf` 和 `SmolLM2-135M-Instruct-Q4_K_M.gguf`，兩者皆核對固定版本 LFS SHA-256。SmolLM2 模型卡顯示 Apache-2.0，stories260K 的模型卡授權未取得。 |
| PASS | 真實 Hugging Face 傳輸寫入 16,777,216 位元組後，強制終止隔離的下載程序。重開工作台後辨識中斷下載，從 16 MiB 接續並驗證完整 SmolLM2 檔案。 |
| PASS | TypeScript、Vite build 與 `npm run test:layout`。Chromium 測試 1280×900、1024×768、800×600 和 650×720 的深色、淺色。測試資料包含長模型名、長錯誤、模擬的團隊執行中狀態。幾何檢查確認標題維持水平、選擇器在容器內、頁面無水平溢出並有鍵盤焦點。 |
| PASS | Chromium 以實際本機 Worker 和 ComfyUI CPU 版驗證影片權重缺失、圖片工作執行中、Stable Diffusion 1.5 生成 384×384 PNG，以及在創作原頁載入圖片。代理人頁以先前實機保存的報告驗證事實區與模型回答區。 [實際畫面](UI_DESIGN.md#第三階段精修) |
| PASS | 由桌面 Worker 管理的 ComfyUI CPU 版實測啟動、再次探測 API、程序異常退出、手動重啟與停止。 |
| PASS | `6da7d2a` 通過 Windows Server 2022 x64 CI。Python、Worker 封裝、Chromium 版面回歸、Rust／Tauri 建置、靜默安裝、桌面與開始功能表捷徑、WebView2 啟動 Worker、關閉及卸載保留資料均通過。 [Windows CI](https://github.com/liu11-21/local-llm/actions/runs/42556268695) |
| PASS | 已下載並核對開發安裝包的 ZIP SHA-256、`BUILD.json` 提交及 EXE SHA-256。EXE 校驗值為 `a180311af672f85b027d512753a10923cf29dc9c5bce7e5671672748b5de4eb2`。 [Windows x64 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42556268695/artifacts/13648135425) |
| FAIL | 本機 Windows 仍以 WinError 4551 封鎖 llama.cpp。新版正確顯示 `ENGINE_POLICY_BLOCKED`。真實聊天與新代理人推理需在允許引擎的環境驗證。 |
| FAIL | 首輪 Windows CI 將系統暫存路徑的別名視為不安全，四項下載測試因此失敗。修正將上層路徑正規化，並保留下載目錄本身的連結檢查；本機回歸通過。 [首輪 CI](https://github.com/liu11-21/local-llm/actions/runs/42555585807) |
| FAIL | 第二輪 Windows CI 通過 Python 測試及打包 Worker IPC，Chromium 回歸等待 Vite 就緒時逾時。測試改由 Vite API 啟動並等待服務，取代讀取 CLI 終端輸出。 [第二輪 CI](https://github.com/liu11-21/local-llm/actions/runs/42555964797) |
| NEEDS WINDOWS | 一般 Windows 10／11 的原生互動、下載中關閉原生安裝版，以及各防毒套件的行為。 |
| NEEDS GPU | 影片、音樂、不同 GPU 後端及資源預估的實機驗收。 |
| NEEDS CLOUD AUTH | 遠端桌機、雲端服務及 Colab Enterprise 的實際請求、作業和費用。 |
| NOT RUN | 新 Agent 工具協議、Team 協作模式及後續批次；正式簽章、誤判申訴與正式 Release。 |

要重跑本機回歸，在倉庫根目錄執行 `python -m unittest -v`。在 `desktop` 執行 `npm ci`、`npm run test:layout` 和 `npm run build`。版面測試會啟動隔離的本機工作台，使用已安裝的 Chrome；可用 `LOCALLLM_BROWSER` 指定瀏覽器執行檔。

## 第二階段基礎

基準為開發分支 `fa81a2c`。維持工作台版本 `0.6.2`。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | 23 項 Python 測試，含兩筆下載與聊天重疊、第二筆本機推理排隊、目的地去重、排隊取消、失敗重試、歷史寫入暫時失敗、重開復原、聊天重新生成及工作流程參數驗證。並行回歸測試用同步事件驗證排程。 |
| PASS | TypeScript 型別檢查及 Vite production build。Chromium 開發預覽連接實際 Worker，以先前本機生成的對話與代理人報告驗證複製、改名、刪除確認、代理人計畫預覽、深淺主題、鍵盤焦點及 650 px 導覽。 |
| PASS | 抽測聊天內容、輸入區標示、模型選擇器、側欄選取項和主要按鈕的靜態文字對比。深色最低 7.71:1，淺色最低 6.24:1。 |
| PASS | 官方 ComfyUI CPU 版實際執行 `sd15-preview`，以種子 42、4 步生成 384×384 PNG。工作台保存 189,967 位元組的作品，作品索引可讀回流程 ID、種子與步數。 |
| PASS | 新版桌面任務 RPC 實際同時下載 Hugging Face 的 `stories260K.gguf`（1,185,376 bytes）和 `SmolLM2-135M-Instruct-Q4_K_M.gguf`（105,454,432 bytes）。每筆使用四個區段執行緒，完成後確認 GGUF 標頭和檔案長度。 |
| PASS | `c01f33c` 於 GitHub Actions 的 Windows Server 2022 x64 完成 Worker 打包、Rust／Tauri 建置、安裝程式與校驗檔產出。靜默安裝、桌面和開始功能表捷徑、WebView2 啟動 Worker、關閉程序，以及卸載保留使用者資料均通過。[CI 紀錄](https://github.com/liu11-21/local-llm/actions/runs/42552053727) · [開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42552053727/artifacts/13645398237) |
| PASS | 從 GitHub 下載的 ZIP 符合 Actions 的 SHA-256。內含 `Local LLM Workspace_0.6.2_x64-setup.exe`，已核對 `BUILD.json` 的提交與 EXE SHA-256 `df4998796d31e14ddc16ac95569d42040f47ee9cf5f272421ebf45fdb3d4b8ff`。 |
| FAIL | 並行測試中另兩個候選檔案發生來源連線重設。工作台顯示失敗且未發布成 GGUF。另一次測試在仍有下載時退出程序，留下隱藏的暫存檔，強制退出後的暫存清理待補。 |
| FAIL | 本機 Windows 的應用程式控制原則封鎖 llama.cpp。新版送出與重新生成的實機推理需在允許執行的 Windows 環境重跑，重新生成的資料庫行為已通過回歸測試。 |
| NEEDS GPU | CUDA／其他 Vulkan 裝置、實際影片與音樂生成及不同硬體的資源估算。 |
| NEEDS CLOUD AUTH | 付費端點與實際 Colab Notebook 作業、額度和結果匯入。 |
| NEEDS WINDOWS TEST | 一般 Windows 10／11 的原生互動和多款防毒軟體。 |
| NOT RUN | 正式簽章、誤判申訴和正式 Release。 |

## 前輪測試

基準：GitHub `main` `8447047496691d34d5c6b24cb846c81d6bcce07f`，正式下載 v0.6.2；新增工作留在 `dev/desktop-workspace`。基準為 6 個 Python 單元測試全數通過。已知問題：舊版未簽署、舊 onefile 需解壓、網頁的原生功能依賴本機橋接，並非 GitHub Pages 可獨立執行。

| 狀態 | 範圍與證據 |
|---|---|
| PASS | 18 個 Python 測試，涵蓋既有更新與團隊回歸、路由同意、HTTPS 驗證、金鑰省略、Colab 提交核准、SSE 串流與取消、SQLite、區段續傳、授權檔完整性及打包 Worker UTF-8 IPC。 |
| PASS | Windows 11 上用 llama.cpp 與 SmolLM2 GGUF：CPU 啟動、聊天回應、對話保存、引擎停止。 |
| PASS | npm/TypeScript/Vite 正式資源建置；Chromium 開發預覽使用真實 Worker，驗證首頁、模型估算、聊天、淺色模式和 650 px 導覽。 |
| PASS | PyInstaller 6.22.3 / Python 3.12.10 onedir 已建置。隔離的全新資料目錄中，由 Worker EXE 下載並驗證官方引擎、以四執行緒下載 105,454,432 位元組的 SmolLM2 GGUF，完成 CPU 聊天、歷史保存、引擎停止、兩成員依序執行及主模型整合。 |
| PASS | v0.6.1 公開 EXE 的 SHA-256、PE、封裝與官方 llama.cpp 位元組比對；固定官方引擎下載與解壓。 |
| PASS | Hugging Face 搜尋、固定版本檔案清單、四執行緒下載 1,185,376 位元組的官方 tinyllamas 測試資產。模擬區段斷線後續傳的位元組比對亦通過。先前連線重設的案例在本輪重跑成功。 |
| PASS | 原生 Tauri NSIS 已在 GitHub Actions 的 Windows Server 2022 x64 runner 建置並驗收。靜默安裝、桌面與開始功能表捷徑、WebView2 啟動 Worker、關閉 Worker、卸載及保留 SQLite 與資料全部通過。[CI 執行紀錄](https://github.com/liu11-21/local-llm/actions/runs/42482360729) |
| PASS | 已下載 CI 產物，ZIP 符合 GitHub Actions 公布的 SHA-256，安裝 EXE 符合 `BUILD.json` 的 SHA-256 `21f64c053624187b1774a717ec2a09634a45c58815a57146f34db21b74eed969`。建置提交為 `ba504ee`。[Windows 開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42482360729/artifacts/13618575102) |
| PASS | 含代理人、Colab 與更新功能的 `ca30587` 通過 Windows CI 安裝驗收。已再次下載並核對 ZIP 與安裝 EXE，EXE 的 SHA-256 為 `72a6eb22a2f351fc8824458a8690d4c0e46c9bf7e5ccaccde04fb253402c9446`。[新版開發安裝包](https://github.com/liu11-21/local-llm/actions/runs/42488732138/artifacts/13621130867) |
| BLOCKED | 此 Windows 11 電腦的應用程式控制原則擋下未簽章開發安裝程式，原生互動驗收未執行。 |
| NEEDS WINDOWS TEST | 以 Defender、Norton、Avast、AVG 的最新定義掃描乾淨安裝與運行；記錄產品版本、事件與 SHA-256。這次未確認 `Custody` 原因。 |
| PASS | Windows 11 Intel Iris Xe 實際執行 llama.cpp Vulkan 分層，SmolLM2 30 層分配給 GPU，完成代理人工作並保存報告。 |
| PASS | 本機開發預覽驗證代理人計畫、核准、報告和原始資料查閱，以及更新頁與 Colab 表單。 |
| PASS | 工作台實際讀取官方 GitHub 版本清單，已能排除舊桌面通道；新版選擇、下載校驗及中止行為以測試資產驗證。 |
| PASS | 官方 ComfyUI CPU 版可啟動，三種工作流程所需的輸出節點存在。回環 HTTP 測試端點驗證三種圖譜提交、輸出下載與格式檢查，以及工作 ID 專屬的取消。 |
| PASS | Windows 11 的官方 CPU 版 ComfyUI 以 SHA-256 已核對的 Stable Diffusion 1.5 權重，跑完預設 512×512、24 步圖片生成。工作台下載並保存 387,306 位元組的 PNG，尺寸和檔案格式符合預期。 |
| FAIL | 此機的 Intel ComfyUI 套件在 PyTorch XPU 裝置探測發生存取違例，可使用已驗證的 CPU 套件。 |
| NEEDS GPU TEST | 其他 GPU 分層與估算偏差、影片與音樂的真實權重推理、作品預覽與 GPU 資源釋放。 |
| NEEDS CLOUD AUTHORIZATION | Colab Enterprise 已接入既有範本、工作提交與狀態查詢，合約測試通過。OpenAI-compatible SSE 及送出前同意有自動測試。回環 TLS 測試未通過憑證校驗，真正的 Notebook、外部 HTTPS 服務與額度須在授權環境驗收。 |
| NOT RUN | Tauri 更新簽章、正式 Authenticode、簽章後驗證。正式發行未進行。 |

Windows 驗收順序：對照 Actions 的 `BUILD.json` 和 `SHA256SUMS.txt` → 非管理員安裝 → 從捷徑啟動 → 安裝引擎 → 下載小 GGUF → 聊天、中止、重新開啟查歷史 → 切換服務與關閉，檢查子程序 → 解除安裝後重裝，確認模型／作品／對話仍在。GPU 與付費端點需獨立驗收，這些通過前不標記可公開發行。
