# 桌面工作台架構

## E3-A、E3-B 的資源與 OpenVINO 執行

- `resource_contract.py` 與 `hardware_contract.py` 為數值保存單位、時間、來源、狀態和證據。DXGI／D3D12 的 UMA 訊號區分統一記憶體與獨立顯存。舊紀錄缺少類型、時間或映射時保留未知。
- `vram_available` 表示專用總量減去已用量的估計餘量。Runtime 推薦只接受單張、已識別且取樣新鮮的獨立顯存池，仍由後端確認模型是否可分配。統一記憶體、共享上限及多 GPU 不合併。llama.cpp 回報的池容量另列。
- `openvino_adapter.py` 在應用程式資料夾管理可選 Runtime、固定套件快取、IR 模型及編譯快取。八個檔案固定版本和 SHA-256，Windows 系統 TLS 負責 HTTPS，傳輸沿用既有多線程、續傳和校驗。
- `openvino_runner.py` 在獨立 Python 3.12.10 程序載入 OpenVINO 2025.4.1，提供裝置查詢、張量推理和 GenAI 文字串流。父程序套用 8 GiB 程序記憶體上限、180 秒執行時限與取消，工作結束釋放原生模型和程序。
- OpenVINO 聊天使用現有對話保存、IPC、任務中心和本機 compute 槽。SQLite 第 10 版增加 `engine_runs`，記錄模型雜湊、指定及實際回報裝置、算子資訊和結果狀態。GenAI 未提供足夠分配證據時維持未驗證。 [操作與限制](NPU_SUPPORT.md) · [儲存政策](PRIVACY_STORAGE.md)

## Batch 4E＋NPU 的 E1、E2

- Runtime 契約增加可選 `task_health`。推薦與文字預檢優先使用對應任務的狀態，離線仍會阻擋傳送。舊 Host 可沿用整體健康或既有圖片就緒資料。
- SQLite 第 9 版的 `client_media_jobs` 在提交前保存 Client 私人提示詞、排除提示詞、Workflow、模型、Host／Job ID、參數和時間。取回作品時還原資料，作品登錄與保存狀態在同一交易寫入。Host 的任務索引維持原有資料政策。
- `hardware_monitor.py` 在背景讀取 Windows CIM 裝置及驅動，以 DXGI 識別實體 GPU 與記憶體池，再按 LUID 配對 PDH 計數器。裝置清單最多每 60 秒更新，量測快取至少 3 秒。關閉時取消清單查詢並釋放 PDH。監控失敗不阻擋推理。
- `hardware_contract.py` 驗證版本、數值、來源、時間與數量上限，整合到本機 Registry 和 Runtime 契約，也可由已配對 Host 回報。每張 GPU 的專用與共享記憶體分開。NPU 無獨立記憶體或使用率介面時保留未知或未支援。
- E1、E2 的 `hardware_providers.py` 以有時限的獨立程序列出主 Worker 環境的既有 Provider。E3 新增的受管理 OpenVINO Runtime 使用獨立裝置查詢，避免把兩個 Python 環境的套件狀態混為一談。 [能力範圍](NPU_SUPPORT.md)

## 首次使用與遠端圖片

- `onboarding.py` 從現有 Registry、硬體資料與已配對能力挑選候選。React 引導連續提交既有文字引擎安裝及 GGUF 下載，失敗時重新盤點已完成項目。
- `remote_jobs.py` 建立 SQLite 第 8 版遠端任務索引，將 TaskManager 狀態與擁有者、請求雜湊及結果關聯。Host 獨占其資料設定檔後恢復舊紀錄。未完成的工作標為中斷。成功回答與作品描述可在重新分享後查詢。
- `remote_media.py` 與 Host 共用圖片白名單、結果大小和完整性規則。Host 透過受管 ComfyUI 在本地推理槽執行。Client 對照已驗證 TLS 端點取得圖片，可續傳暫存，驗證後發布到作品庫。 [遠端圖片操作與限制](REMOTE_MEDIA.md)

## Batch 4A–4C

- `desktop/src/TaskSelection.tsx` 將 Registry 的 Runtime 能力與模型顯示統一，原有 Agent、Team、聊天和媒體仍透過各自的參數契約工作。
- `desktop_worker.py` 的 `task-preflight` 重用 Runtime 能力與推薦，判斷缺少的模型、引擎和連線。媒體分支沿用 ComfyUI 預檢。前端用共用對話框取得外部傳送同意，實際任務仍由原有 TaskManager 與服務端驗證。
- `hardware.ResourceMonitor` 從 Windows API 讀取 CPU 時間及 RAM，首頁可見才以 3.5 秒間隔取樣。GPU 使用率和 VRAM 用量目前無即時來源。
- `remote_tls.py` 在本機管理自簽、含 IPv4 SAN 的伺服器憑證。第 7 版 SQLite 新增自動 TLS 資料。私鑰使用加密 PKCS#8，密碼由 Windows 使用者範圍 DPAPI 保護。自動模式只在明確同意後啟動，更新後撤銷舊配對。Client 沿用嚴格 TLS 與憑證固定驗證。

## Batch 3D–3E

- `runtime_contract.py` 驗證版本化的能力紀錄，明確表示資源來源、未知資料、連線及健康狀態。現有 Registry 和 IPC 仍可供舊頁面使用。比較流程只使用本機快照與使用者已查詢的外部能力。 [能力契約](RUNTIME_CAPABILITY.md)
- `remote_host.py` 提供受限的 HTTPS 介面，由使用者指定私人位址後才啟動。Host 啟停、建立邀請及撤銷其他裝置由本機 IPC 管理。Host 重用同一 TaskManager 和 llama.cpp 佔用槽。
- `remote_client.py` 驗證 Host 憑證及身分，使用 Windows DPAPI 保護配對憑證。任務 ID 支援有限時間的斷線恢復。SQLite 第 5 版新增配對和每則回答的實際來源資料，保留原有對話表。 [遠端使用指南](REMOTE_RUNTIME.md)
- SQLite 第 6 版新增創作權重驗證索引。只有固定 revision 的 SHA-256 與檔案指紋相符才顯示已驗證。ComfyUI 能辨識檔案、是否通過校驗與硬體能否完成生成分開顯示。

## Batch 3A–3C

- `team_workflow.py` 依交付節點及相依成果計算 `outcome`。任務中心仍使用原有狀態機。固定工具的參數先由 `tool_registry.py` 驗證，之後隨預覽核准，並和工具結果一同存入執行紀錄。同步工具呼叫逾時後，底層執行若仍在進行，就繼續占用原本的執行槽。關閉工作台時會通知取消並短暫等待。仍需強制停止時，應由個別的子程序隔離方案提供。
- `media_install.py` 定義 ComfyUI 固定 revision、授權、位元組長度、SHA-256、必要節點與權重安裝位置。安裝經過同一 TaskManager，由共享下載器先暫存及校驗，再發布到受管便攜版。CPU 和 NVIDIA CUDA 12.6 共用 bundle，安裝任務依 bundle 去重。確認摘要才會下載權重。使用者已放置的同名檔案只讀取與比對。
- `creations.details` 沿用 SQLite 表，新增 JSON `schema: 1`、工作流程、Runtime、ComfyUI 任務與來源檔名。舊資料仍可讀，無需更動資料庫表。新作品記錄媒體標頭中的尺寸或時長，舊作品在查詢時補讀。作品庫只列舉安全輸出檔名，沿用 Tauri 本機 asset protocol，並在開啟原檔前再次驗證路徑。

目前以 Windows x64 為目標；舊 Tkinter 和 GitHub Pages 仍走各自原本的入口。

| 層 | 實作 | 職責 |
|---|---|---|
| 呈現 | `desktop/src` · React / TypeScript / Tailwind | 導覽、對話、工作進度、模型與環境設定 |
| 桌面宿主 | `desktop/src-tauri` · Tauri 2 / Rust | 單一工作台命令、大小限制、資源路徑和工作程序生命週期 |
| Python 工作程序 | `desktop_worker.py` | JSON Lines、本機聊天、SQLite 和既有功能的轉接 |
| 任務排程 | `task_manager.py` | 任務生命週期、獨立佇列、去重、取消及下載重試 |
| 下載恢復 | `downloads.py`、`download_recovery.py`、`catalog.py` | 固定版本來源、跨程序檔案鎖、已完成區段的校驗點和發布前驗證 |
| 引擎健康 | `engine_health.py`、`engine.py`、`comfy_runtime.py` | 啟停、程序退出與 loopback API 探測，提供錯誤碼及恢復方式 |
| 能力登錄 | `registries.py`、`media.py` | 提供 Model、Engine、Runtime 及 Workflow 描述，供頁面選擇與表單渲染 |
| 運算供應商 | `runtime_provider.py`、`colab_runtime.py` | 路由同意規則、HTTPS OpenAI-compatible、Colab Enterprise 的既有範本和 Notebook 作業 |
| 現有能力 | `downloads.py` / `load_plan.py` / `engine.py` / `model_team.py` / `media.py` / `comfy_runtime.py` | 下載、資源估算、llama.cpp、團隊及媒體 |

正式宿主把 JSON 寫入工作程序的 stdin，從 stdout 讀取回應，工作台 IPC 不開 HTTP 埠。Windows Job Object 讓宿主持有整棵工作程序樹；關閉行為仍需實際安裝驗收。llama.cpp 使用帶臨時金鑰的本機回環服務。既有 ComfyUI 為回環服務；使用外部啟動的 ComfyUI 時，程式不會停止該服務。只有瀏覽器開發預覽會使用 Vite 同來源代理；正式 bundle 不含代理。

- Model：GGUF 檔、外部模型 ID 或 ComfyUI 工作流程需要的權重。
- Engine：llama.cpp、ComfyUI 或 OpenAI-compatible 服務。
- Runtime：本機 CPU／GPU、使用者配置的 HTTPS 遠端或雲端。外部推理須手動選擇並確認本次傳送；一律不自動改用付費端點。
- Task：本機推理共用一個槽位，兩個背景下載和兩個遠端文字請求有獨立槽位。同一對話與下載目的檔案各自去重。團隊執行時佔用本機槽位，團隊內部沿用 RAM／VRAM 預算。已啟動的本機 ComfyUI 與文字引擎仍依現有互斥規則切換。
- 任務從排隊轉為執行，再進入完成、失敗、取消或中斷。取消執行中工作時保留槽位，等工作結束才交給下一筆。關閉後重開會把上次的進行中紀錄標為中斷。工作參數和串流回覆保留在本次程序，不寫入任務歷史。下載重試在本次程序建立新工作，付費或推理工作由使用者回原頁重新提交。
- Workflow：由 Python 宣告預設值、範圍、必要權重、引擎和輸出格式。工作程序驗證參數後組成 ComfyUI 圖譜，作品資料庫記錄實際參數及種子。四個內建選項共用同一個創作表單。

`%LOCALAPPDATA%\LocalLLM` 沿用模型、作品和 ComfyUI 資料。`desktop.sqlite3` 新增本機對話與任務索引；外部金鑰不進資料庫，關閉即清除。介面偏好存在本機 WebView。模型和媒體仍由檔案系統管理，沒有自動刪除或遷移。要備份請關閉工作台，再複製整個資料目錄。

## 第三階段相容性與恢復

- 桌面 GGUF 下載使用固定的 Hugging Face 提交網址。模型目錄下的 `.localllm-downloads` 依目的檔名隔離，作業系統鎖避免兩個 Worker 同時寫同名模型。程式先寫入校驗點再恢復。續傳時比對網址、大小及強 ETag 或上游 SHA-256，並重讀每個已完成區段。取消會移除可辨識的暫存，網路中斷會保留已完成區段。完整檔案通過 GGUF 標頭、大小及可取得的上游 SHA-256 後才發布。
- 重開時清除工作台可辨識且無法續傳的暫存。先前版本未附歸屬資料的 `.model-*.part` 和其他未知檔案會保留。無法續傳的模型可從模型中心重新下載。中斷後的續傳由使用者選擇。
- SQLite 第 2 版新增 `model_sources`。來源紀錄包含倉庫、revision、上游提供的模型卡授權、下載時間和實際 SHA-256。上游提供 LFS SHA-256 且比對成功時，介面標為下載時已驗證。紀錄綁定檔案指紋，辨識一般的檔案替換或修改。讀取清單時不重新雜湊整個模型。來源及校驗結果不代表模型安全或授權商用。 [Hugging Face 模型 API](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api) · [模型卡欄位](https://huggingface.co/docs/hub/model-cards)
- 啟動成功須通過實際 API 檢查。閒置的受管引擎約每五秒允許一次背景探測，避免健康檢查佔住 IPC。程序退出、API 無回應與手動停止各有狀態。現有 Vulkan 啟動失敗時至多回退一次 CPU。引擎錯誤細節留在任務中心，ComfyUI 保留啟動日誌。
- 創作的權重預檢使用指定的本機 ComfyUI，查詢節點是否能選到需要的權重。開發預覽的圖片檔只從明確指定的隔離資料目錄提供。Tauri 使用既有的媒體檔案範圍。

SQLite 遷移保留舊表與原本資料。回滾可在備份資料目錄後建置 `da4ee33`，舊版仍可讀取原有對話、模型與作品。新版下載校驗點和來源紀錄由第三階段版本管理。

## Batch 2 代理人與團隊

| 元件 | 介面及責任 |
|---|---|
| `tool_registry.py` | 登錄內建工具的來源、版本、輸入與輸出 JSON Schema、權限、逾時和錯誤碼。Executor 只執行受信任的本機唯讀工具，驗證輸入和輸出，並限制同時執行數。 |
| `agent_plans.py` | SQLite 保存多份計畫、版本、Task ID、授權、時間軸、工具事實和回答。TaskManager 在同一筆寫入內綁定任務和核准。修改版本或工具契約會要求重新預覽及核准。 |
| `agent_runtime.py`、`desktop_agent.py` | 保留簡易固定流程。多步驟可用嚴格 JSON 或本機 llama.cpp 的原生工具串流。模型回應只會進入資料解析及權限驗證。 |
| `team_workflow.py` | 角色、可編輯範本和有向無環圖。提交前驗證成員、節點、依賴與預算。每個節點使用獨立聊天上下文，保存輸出和工具事實。 |
| `task_manager.py`、`desktop_worker.py` | Agent、Team 與本機生成共用運算佇列。Agent 等候逐次核准時釋放槽位，核准後以原 Task ID 排回佇列。 |

- 代理人先建立草稿，再等待計畫核准。核准後可執行、暫停、繼續或進入終止狀態。每次調用都驗證目前允許清單。逐次核准會固定當次工具、參數及請求 ID；拒絕也會寫入稽核。應用程式重開將執行中、已核准待執行和暫停的工作標為中斷。
- Agent 限制包含步驟、調用次數、總時間、工具逾時、格式重試和累計輸出 Token 配額。每次模型呼叫先保留上限，輸入另以本機引擎的 Token 計數檢查上下文。工具計畫與事實保留在本機 SQLite。
- 原生工具模式以 `--jinja` 啟動本機模型，從 SSE 接收工具片段。能否可靠使用取決於模型與範本，介面以「未驗證」顯示。 [llama.cpp 原生工具調用](https://github.com/ggml-org/llama.cpp/blob/master/docs/function-calling.md)
- 角色工作流程的獨立研究節點各自產生草稿；分工先由協調者規劃，再傳給相依角色；交叉審查保存初稿、審查、修正版與最終交付。可依節點設定使用部分成功的依賴。現有多模型整合仍保留原本的資源估算與執行模式。
- 外部團隊節點需要手動運算政策與當次資料傳送同意。只要流程包含外部端點，就停用本機工具，避免工具資料透過草稿傳送。設定保存端點識別碼，金鑰仍只在工作程序記憶體。重開後可能需重新連線及指派端點。
- SQLite 第 4 版新增 `agent_plans`、`team_configs` 和 `team_runs`，保留既有報告、對話、下載來源及作品。回滾可在備份資料目錄後建置 `c83dfca`。
