# Local LLM Workspace 0.8.0 Development — delivery

2026-11-14；dev/desktop-workspace；main／Stable v0.6.2 保持不變，未建立 Release／Tag。

## 階段提交

- 3d0c67e：架構檢查、第一方版本統一 0.8.0 Development。
- 85686e7：llama.app／Trust／Runtime Registry、模型與排程接口整合。
- ce055bb：Runtime UI、Thinking、資料升級／測試與 Windows CI 整合；第一輪 Windows 20 steps 成功。
- c671373：具名 GPU 與實際程序樹元件檢查。
- e523cfe：切換 Adapter 時隔離受檢映像的信任狀態。
- fbfbc96：等待 UI route handlers 完成再關閉瀏覽器，修正 CI teardown 競態；不忽略測試錯誤。
- 3e4dc13：新上游授權固定 LF，避免 Windows 檢出轉換破壞來源 hash。
- 1a4503d：官方 signer 的 CN／Organization 精確比對，拒絕僅含相似字串的其他 publisher。

## 已完成

正式支援獨立 `llama.exe serve` Adapter，舊 `llama-server.exe` 保留。既有安裝偵測及手動切換、
固定 b12360 下載／雙 hash／有效 Hugging Face 簽章，不執行遠端安裝腳本。
Worker 代理 loopback + 隨機 Key + 限制 CORS；原生 llama agent 工具未啟用。
共用 TaskManager／DeviceExecution、模型下載／續傳／校驗、Agent／Team 授權、Remote、Benchmark 與 SQLite。
Thinking 依模型 template 能力，預設關閉；正確的 reasoning_budget_tokens 保留正式回答空間，空正式回答失敗。
模型 context／architecture metadata、確認刪除、磁碟空間、Token／速度與硬體取樣，以及新手／進階 Runtime UI。
Worker 新增與 App 一致的 Windows PE product/file version 資源；實際安裝的 shell／Worker／uninstaller 均已核對為 0.8.0。

主要檔案：engine.py、llama_app_engine.py、runtime_manager.py、runtime_trust.py、llama-app-runtime.json、
desktop_worker.py、device_execution.py、device_recommendation.py、benchmark_adapters.py／benchmark_service.py、
gguf_metadata.py／registries.py、build_desktop_worker.py、workspace_storage.py／upgrade_probe.py、
desktop/src/LlamaRuntimePanel.tsx／ChatWorkspace.tsx／ModelLibrary.tsx／RuntimeWorkspace.tsx、Windows workflow／smoke。

## 真實證據與範圍

- [CPU／Intel Vulkan 推理、安全 API 與程序清理](evidence/v080/runtime-cpu-vulkan.json)。
- [Qwen3-0.6B Thinking 開關](evidence/v080/qwen-thinking.json)；正規內容與思考分離，不保證小量化模型品質或繁體服從。
- [真正應用內固定 Runtime 安裝](evidence/v080/managed-runtime-install.json)。
- [程序樹 54 個載入元件的獨立檢查](evidence/v080/loaded-component-inspection.json)，本次全部 Valid；仍非 SAC 保證。
- [真實 Worker 聊天／原生 Agent／不同 GGUF Team／切換保留](evidence/v080/worker-workflows.json)。
- [真實串流取消與清理](evidence/v080/worker-cancellation.json)。
- [具名裝置探測](evidence/v080/runtime-device-probe.json)。
- [經 Worker 排程的 CPU／Intel Vulkan Benchmark](evidence/v080/scheduled-benchmark.json)，含 cold/warm、工作量、context、layers、Token 與 peak RAM。

這台主機是 Intel Iris Xe，非 RTX 5070 Ti。維護者的 4B / Vulkan Prompt 160.92、Generation 215.09
只作來源明確的另一主機基準，不能拿本輪不同模型／context／Token 數的數字直接比高低。
下載套件的基礎 CPU preset 也與維護者原 EXE 不同；完整 SHA／來源／限制見 [RUNTIME_TRUST](RUNTIME_TRUST.md)。
主 EXE Valid 不等於全部 helper／DLL 或 SAC 已通過；應用安裝包本身仍 unsigned，SignPath 未核准。

## 驗收與下載

最終 [Windows CI Run 43567386614](https://github.com/liu11-21/local-llm/actions/runs/43567386614) **SUCCESS，20 steps**。
安裝包功能來源 `1a4503dddeb6388b70da813b5c2b5e8788237f7d`；最後文件／證據同步提交不改變這個二進位來源。

| 驗收 | 結果與界線 |
|---|---|
| Python | 乾淨 Windows 221 項：220 通過、1 個封裝 Worker 案例建置前 skipped；Worker 建置後該案例單獨實跑通過。7 個本機 Norton/TLS 限制案例在 CI 實跑。另本地授權完整性 6 項通過。 |
| 前端 | TypeScript／Vite PASS；既有 bundle-size 警告保留。完整 Chromium PASS：1280×900、1024×768、800×600、650×720，深淺色；涵蓋 Agent／Team、影音／Remote、Benchmark、推薦、版本混用及新 Runtime 信任介面。UI fixture 不冒充真實推理。 |
| Rust／封裝 | `cargo test --locked` 編譯及測試 harness 通過，現有 Rust 原生 shell **0 個單元案例**；另以安裝／WebView／Worker 的端到端測試驗證行為。Python 3.12.10、Node 24.22.1、Rust 1.99.1。 |
| 真正升級 | 固定 e2ba347 的 0.7.0 安裝包 → 0.8.0 原地升級、SQLite 表／檔案指紋、校驗備份、桌面／開始選單捷徑、WebView／Worker、程序清理及卸載保留資料 PASS。 |
| 版本／元件 | App／Worker／NSIS／BUILD 均 0.8.0 Development；實際安裝 74 個 PE：67 Valid、7 NotSigned。此表與另外下載的 Runtime 54 個載入元件檢查為不同範圍。 |
| Notices／SBOM | 本次 SPDX 共 643 packages（第一方 1＋第三方 642 個唯一身分）；Notice index 有 643 筆依賴情境記錄，packaging 同版本分建置／選用 Runtime 兩筆。CI 原始清單完整凍結；目前 SBOM 保留先前 641 筆記錄與 MIT 核准紀錄，只增 zstandard／llama.app 兩筆，原有授權文字保留。SPDX 2.3 schema／references／notice hash PASS，不代表法律或 SignPath 核准。 |
| 來源證明 | 下載 ZIP 與 GitHub artifact digest、EXE 與 BUILD／SHA256SUMS 全部一致；官方 `gh attestation verify` 對固定 repo／workflow／source ref／commit，拒絕 self-hosted runner，退出碼 0 且驗證結果非空。GitHub 來源證明不是 Windows 程式碼簽章。 |

[下載 Windows x64 0.8.0 Development 安裝包](https://github.com/liu11-21/local-llm/actions/runs/43567386614/artifacts/14103485329)。
下載 Actions artifact 後解壓，執行 **`Local LLM Workspace_0.8.0_x64-setup.exe`**（13,807,219 bytes）。
這是可安裝 EXE；GitHub 的 Source code ZIP 是原始碼。Artifact 保留 14 天，下載可能需要登入 GitHub。
安裝包 **NotSigned**，可能受裝置安全政策阻擋；本輪不更改政策，不保證防毒放行。

EXE SHA-256：`d79f480bd1c35595b75ce5755e902f635a10a7e5e5fb35fef83cc3b1b25d4354`

ZIP SHA-256：`0fb81f4568fab9a390ea9c3c3748bd9c7b6cd20b4e2ffb011d4d3df4f7bfb1e8`

證據：[CI 原始測試節錄／步驟](evidence/v080/windows-validation.json) · [BUILD](evidence/v080/BUILD.json) ·
[下載／雜湊核對](evidence/v080/candidate-verification.json) · [GitHub attestation](evidence/v080/provenance.sigstore.json) ·
[安裝／捷徑／程序](evidence/v080/installer-smoke.json) · [升級資料](evidence/v080/upgrade-verification.json) ·
[卸載後資料](evidence/v080/upgrade-after-uninstall.json) · [安裝 PE 清單](evidence/v080/installed-pe-inventory.json) ·
[封裝 Worker 量測](evidence/v080/performance-packaged-worker.json) · [本次 CI SBOM](evidence/v080/CI-SBOM.spdx.json) ·
[本次 CI Notice index](evidence/v080/CI-NOTICE-INDEX.json)。
[文件／JSON／來源證明／原授權文字保留的最後核對](evidence/v080/documentation-validation.json) 全部 PASS。
安裝後三次 process-cold 啟動 1293.2824／663.5662／659.097 ms；未清 OS cache，不能當硬碟冷啟動或宣稱整體加速百分比。

CI 的自動蒐集 metadata 可能因本機已安裝 metadata／原始來源取得方式不同，而與既有人工確認的 license／review status 不同。
因此 [目前清單](sbom/DEPENDENCY_LICENSES.json) 保留既有審查證據，未以本次自動蒐集結果覆寫舊結論；
`CI-NOTICE-INDEX.json`／`CI-SBOM.spdx.json` 則保持安裝包隨附內容。這是來源與版本同步，沒有重啟完整授權審查。

先前 ce055bb 的完整 20 steps 已成功；e523cfe 全 UI 斷言通過後出現 teardown route.fetch 競態，
由 fbfbc96 等待 in-flight handlers 解決。被新提交取代的中間 CI 已取消，不把它們算作最終成功。
本次沒有放寬斷言、忽略 Promise 錯誤或跳過 Windows 安裝驗收。

## 保留的限制

NEEDS HARDWARE：RTX 5070 Ti／Qwen3-4B 本輪重測、CUDA、其他 GPU、NPU、雙實體 Remote 主機、
GPU 使用率／功耗及 SAC 啟用下全依賴鏈。NEEDS AUTH：未授權付費雲端。
App 仍是開發版，無正式 Release／Tag；模型／Runtime 各自條款及 MIT 排除資產、第三方發行／SignPath 待辦不因本輪消失。
