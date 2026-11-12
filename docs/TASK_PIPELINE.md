# 共用任務準備

## 0.7.0 整合

初始 RPC 先驗證 App／Worker 識別，不一致時不送出產品操作；Worker 意外退出後由使用者重新連線並查原任務，不自動重送。同步錯誤與 TaskManager 失敗共用結構化恢復資訊，詳細錯誤仍保留供 Agent／Team 及進階紀錄；保留原有取消／中斷／依賴語意與權限代碼。

Remote Host 在線不等於影音就緒，影音候選必須有 Media v2、固定 Workflow 與完整權重驗證；Colab 仍僅 notebook、雲端依現有 chat 能力，不擴張為任意任務。OpenVINO 刷新模型清單走本機 Adapter。[整合與硬體驗收](V070_DELIVERY.md)。

## E3-F／E4／E5 任務流程

推薦查詢不執行工作；採用附本機 Recommendation ID，TaskManager 開始前重新驗證模型／環境／Benchmark，dispatch_runs 保存完整鏈。未知或失效時拒絕舊憑證，手動改設備可重新確認。模型 Job Object 使用與資源預留一致的動態記憶體額度。

遠端媒體使用原 media／remote-host-media／remote-fetch-work 動作。Client 提交前保存提示詞、歌詞、參數及 Host／Job ID；Host 重新檢查白名單、配額及完整權重，長工作查詢／取消／續傳共用現有任務系統。重啟中斷、不自動重跑；失敗的下載不重新生成。TaskCenter 保留結果入口與進階證據。[詳細狀態與界線](E4_E5_DELIVERY.md)。

## E3-D 的推薦與確認

DeviceChoice 讀取相同推薦 RPC，不傳送 Prompt，也不啟動 Benchmark。使用者可看條件、替代來源與完整證據，手動選擇設備後仍須開始任務。外部來源沿用 TaskPreparation 的目的地、內容與費用確認，未知費用不視為免費。

TaskManager 原子檢查 ResourceDemand，先全部取得裝置／Provider／Engine 鎖、RAM／VRAM 與規劃預算，再啟動隔離的既有引擎。暫時不足會排隊，可取消；模型或引擎在排隊後改變時拒絕。Benchmark 與既有單工作流程仍全域排他，ComfyUI 保留持續預留。停止服務可解除預留，不被隊頭公平性阻塞。

Team 父任務不持有模型資源，依賴就緒的節點成為 child Task，由同一佇列執行。每節點保存獨立輸入、結果及工具證據，再供主模型整合。父取消會傳到子任務。Agent 的計畫版本與逐次工具核准保持，等待核准時釋放程序，恢復時重新准入。

SQLite 12 增加 dispatch_runs，保存已確認權重與引擎雜湊、指定與回報設備、Job 記憶體限制／峰值及狀態。取消、失敗、逾時與關閉都清理原生程序後才釋放資源；重開只標 interrupted，不自動重送。[完整資源契約](DEVICE_RECOMMENDATION.md)。

## E3-C Benchmark 工作

確認模型、裝置、固定工作量、次數、時間與程序記憶體上限後，先建立 queued Session，再交給現有 TaskManager 的 compute lane。排隊取消仍留下可追蹤紀錄；執行時逐列保存。Benchmark 與聊天／Agent／Team 依序執行，沒有為測試強制中斷其他工作。取得 lane 後可釋放閒置文字模型，ComfyUI 服務尚在運行時拒絕測試，讓使用者自行停止。

Benchmark 不列為自動重試工作。取消、逾時或 Backend 失敗保留已完成的列，重開標為 interrupted。引擎缺失及不支援裝置不自動改用 CPU。Remote Benchmark 仍 unsupported；E3-D 多任務調度已實作，但 Benchmark 本身不與其他本機推理並行。

OpenVINO 透過現有 TaskManager 執行安裝、裝置查詢、模型匯入及推理。安裝需確認固定版本套件和空間，模型由使用者從既有 IR 資料夾匯入。聊天只列出含完整 Tokenizer 的模型，使用本機政策，不增加外部傳送確認。OpenVINO 與 llama.cpp／ComfyUI 共用單一 compute 槽，獨立安裝走原 network 槽。

指定裝置使用 CPU、GPU／GPU.n、NPU／NPU.n，不提供 AUTO／HETERO。NPU 文字模型須符合可辨識的對稱 INT4、group size 和 ratio 條件，實際算子相容性由後端載入檢查。格式檢查、後端存在、估計容量、實際推理證據及 Benchmark 各自呈現。E3-C／D Benchmark 與智慧派送已整合，沿用原有核准與資料同意。

首頁的首次使用引導使用同一套模型及 Runtime 資料。文字引擎和 GGUF 各自走原有任務，使用者只需要按一次準備。切換 Runtime 時更新模型清單並重驗證選取項目，保留提示詞。 [首次使用](ONBOARDING.md)

圖片只有在已配對 Host 宣告圖片工作流程時才顯示該選項。流程、權重、節點及外部同意通過後才提交。Host 的文字和圖片健康分開判斷。 [遠端圖片](REMOTE_MEDIA.md)

E1 的 `task_health` 讓推薦及文字預檢採用對應任務狀態，仍會檢查能力是否過期、連線、模型、隱私與費用。圖片引導優先列出已配對、資料新鮮且流程就緒的主機，選擇後直接帶入創作頁。沒有可用遠端或目前政策限制外傳時，仍可選本機準備。

E2 的監控只提供能力與證據，沒有因偵測到 NPU 而新增可派送的推理目的地。既有 CPU／Vulkan 路徑和 TaskManager 排程照常使用。Provider 初始化在獨立程序執行，逾時或失敗只更新硬體診斷狀態。

聊天與代理人的文字引擎和推薦模型可以在原頁安裝。安裝動作提交給既有 TaskManager，在準備區顯示進度及取消，失敗可由任務中心重試。創作的權重檢查和安裝沿用 ComfyUI 工作流程。

`task-preflight` 接受任務種類、最多六組 Runtime／模型及運算政策。文字工作回傳阻擋原因、相容性、風險、未知資源及外部傳送清單。媒體工作回傳 ComfyUI 健康、缺少權重及缺少節點的現有結果。預檢會讀取本機與已保存的 Runtime 能力，對外傳送內容由正式提交開始。

有效的模型清單確認模型不存在時，缺少且不能安裝的模型判為不相容。若本機可從內建目錄下載，顯示需要設定。遠端清單過期或離線時，會說明需要重新連線，並保留未知資料。可用記憶體和推理估計分開顯示。

聊天與團隊共用傳送對話框，逐一列出目的地、模型、費用資訊和傳送內容類別。只有同意才能提交。代理人的本機工具核准與團隊工具核准仍為獨立步驟。TaskManager 照常檢查權限、佇列及任務取消。
