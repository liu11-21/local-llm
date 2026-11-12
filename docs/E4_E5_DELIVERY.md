# E3-F、E4–E5 交付與驗收

基準 `db6f6f8`，分支 `dev/desktop-workspace`，版本維持 **0.6.2**。本輪不修改 main、不建立正式 Release、不處理簽章。

## 提交組

| 組別 | Commit | 內容 |
|---|---|---|
| F | 44a9931 | 推薦憑證、動態 RAM、ComfyUI 保留基礎 |
| A | 50dd40c | Media v2、相容 PNG、續傳與配額 |
| B | ad15eb2 | 受管理 Wan 2.1 遠端影片 |
| C | 45fb36e | ACE-Step v1 遠端音樂、歌詞保存 |
| E4-D | df213ee | 合法媒體、大檔、TLS、完整性與保留測試 |
| D / E5 | 8decf9a | 聊天、首頁、任務、作品庫、新手流程及資源安全收尾 |
| E 收尾 | 25c3edd | 修正動態 RAM 的裝置 ID 型別、舊紀錄安全呈現與實機回歸 |
| E 媒體收尾 | 4354605 | 重用保留 Host／歌詞、音樂引導映射與解碼界線 |
| E | 本文件及 evidence/media | 原生證據、完整回歸、Windows 建置與最終報告 |

安裝包程式來源 HEAD 為 `4354605004c7d8db1f88bca8e3cc1ef38b135b55`，其後只提交本輪文件／證據；文件提交的 HEAD 見 Git 紀錄與對話交付報告。[Windows 交付與雜湊](TEST_REPORT.md)。

## 已交付

推薦透過本機 SQLite 憑證串聯 Benchmark ID／Run ID、Recommendation ID、Task ID、Dispatch ID。採用時及真正開始時重查；模型、Backend、驅動、裝置、原始有效 Benchmark 或排序改變會拒絕舊憑證。15 分鐘有效期不是硬體效能失效判定。參考 Benchmark 不被稱為本次任意提示詞的等價量測。

RAM 策略保留 max(1 GiB, 實體 RAM 10%)，模型及 Backend 工作空間估計向上取整至 MiB，至少 1 GiB；上限取實體安全容量與使用者上限的較小值。0 表示自動，設定在 SQLite 保存。當前 RAM 不足排隊；總容量、未知需求或使用者上限無法滿足則拒絕。Job Object 的限制與排程預留一致，排隊後再檢查政策。共享 GPU 記憶體包含於 RAM，沒有重複加總。

ComfyUI 由管理程序持有 Job Object。自動模式取安全容量一半並受目前可用容量限制，使用者上限仍受實體容量約束。只有單一可辨識獨顯、容量及取樣可靠、服務閒置、程序記憶體上限已實施時，才將全域保留縮成該 GPU 鎖與完整 committed-memory 上限，讓無衝突 CPU 工作有機會並行。生成、切換、釋放、未知、UMA 或多 GPU 不明時保守互斥；模型名稱未知仍標未知。Benchmark 始終與 ComfyUI 互斥，自身媒體任務沿用同一保留，不會死鎖。

同一 Remote Host／Client／RemoteJobs／TaskManager 支援 image、video、audio，產品頁面的 music 對應契約 audio。外層 TLS 協定及 Runtime schema 維持 1，媒體 schema 2，SQLite 14 只新增欄位並保留舊資料。v1 PNG 仍能查詢及下載。

新契約保存 Job／Media／Owner／Host／Runtime／Workflow／Model ID、版本、固定 revision、MIME、副檔名、長度、SHA-256、生成參數、時間、狀態及保留期。Host 重新驗證參數，影片／音樂開始時也重查完整權重驗證。只接收白名單 ID，沒有任意節點圖、Python 或命令輸入。

媒體共用完整／Range 下載、斷線續傳、進度、取消、SHA-256、內容驗證及原子發布。PNG 32 MiB、WebM 2 GiB、FLAC 512 MiB；Client 暫存 4 GiB，Host 結果 8 GiB，預留 256 MiB 磁碟餘量。Host 排隊任務也先保留最大輸出額度。大檔逐塊傳輸，不寫入 SQLite。

新 PNG 驗證 CRC，WebM 檢查 EBML／WebM 與影像軌，FLAC 檢查 STREAMINFO／取樣率／時長；這些是有界格式檢查，不宣稱完整解碼所有大檔。合法測試媒體另由 Chromium 實際解碼播放。下載失敗保留可恢復狀態，雜湊錯誤移除該下載片段，重試不重新生成。Host 重新啟動把未完工作標 interrupted，不自動重跑。

Host 新結果保留 7 天，每 5 分鐘及啟動／提交時清理；僅處理受管理的遠端輸出與過期孤立檔。已下載 Client 作品及模型不受影響。舊 v1 未宣告保留期的結果不自動刪除。Client 會清理其他超過 7 天的下載片段，使用者正在要求恢復的片段保留。

Wan 使用 2.1 T2V 1.3B，完整三份權重；ACE-Step 使用 v1 3.5B，沒有混用 1.5 節點。ComfyUI 固定 v0.44.0、影片 VP9 WebM、音樂 FLAC。[固定權重與授權核對](evidence/media/weight-source-audit.json)、[已下載節點來源核對](evidence/media/workflow-source-audit.json)。來源：[Wan 固定版本](https://huggingface.co/Comfy-Org/Wan-2.1/tree/123acf1cc74bccbb9bfff8ac1ee72edc08c2341d)、[ACE-Step 固定版本](https://huggingface.co/Comfy-Org/ACE-Step/tree/ea4f3d349e84d5c098cc8e8b904a30fde59fc99a)、[ComfyUI v0.44.0](https://github.com/Comfy-Org/ComfyUI/tree/v0.44.0)。

## UI 與操作

聊天預設只有模型／運算來源／就緒狀態，設定展開後保留原本的選擇、推薦、證據及 Benchmark 入口。650px 預設收合歷史，對話和輸入優先。任務中心呈現模型、來源、狀態、進度、開始時間、取消與結果入口，ID／資源／推薦鏈／完整錯誤放進進階區，不虛構 ETA。

首頁依初次使用、日常與活躍任務調整，提供最近對話／模型／作品及已配對主機。主機在線與文字／媒體推理能力分開；快速入口只預選目的地，不送出資料。新手引導有步驟與固定底部操作區，完成後顯示輕量提示，保留剛產生的結果。

作品庫有 Grid／List、類型／模型／來源／日期／搜尋、24 筆分頁、生成參數與重用。只為選中的作品載入原始媒體。生成結果或首次預覽時建立 PNG 縮圖，最多 320×200、96 KiB／項、16 MiB 磁碟快取；舊作品未預覽時顯示類型圖示。來源檔案變更使縮圖失效，清理只刪衍生快取。

| 流程 | 已準備環境的語意操作數 | 手動技術參數 |
|---|---:|---:|
| 一般本機聊天 | 3：開啟聊天、輸入、送出 | 0，沿用目前模型／來源 |
| 遠端影片到作品頁及播放 | 7：開頁、選 Host、輸入、生成、同意、播放、開作品 | 0，使用預設 Workflow |
| 遠端音樂到作品頁及播放 | 8，另含歌詞輸入 | 0 |
| 首次本機文字引導 | 7 個語意操作（含輸入）：開始、硬體下一步、用途、一鍵準備、開始聊天、輸入、送出；實測中斷案例另有重試操作 | 0 |

這是語意操作，不是滑鼠實體點擊次數；可選的展開／改參數／重用不計入主要流程。全新遠端 GPU Host 的安裝、配對及真實模型生成尚未有雙實體機驗收，不能把已準備的 7／8 次當成全新安裝數字。影片／音樂目前在原頁即可準備本機 ComfyUI 與權重，或選擇已就緒 Host。

| 原有流程 | 本輪變化 |
|---|---|
| 聊天常駐模型、Runtime、設備及推薦卡 | 主要操作列直接聊天，按一次展開完整設定；窄視窗按一次開啟歷史 |
| 遠端影音未有完整可執行流程 | 同一創作頁選 Host、確認、執行與播放；已準備環境的操作數如上 |
| 作品清單逐筆檢視 | Grid／List 與篩選、24 筆分頁；重用一次帶回來源、提示、歌詞及參數 |
| 引導完成後顯示大型完成視窗 | 輕量完成提示，不需另關視窗才能閱讀結果 |

舊版本未重新量測完整流程的語意操作總數，數字比較標為 NOT RUN；上述僅比較已查核的介面行為，不推算節省點擊百分比。

前：[原 E3 常駐推薦卡](ui-preview/device/device-chat-vulkan-real-dark.png)。後：[精簡聊天](ui-preview/e4e5/chat-compact-dark.png)、[650px](ui-preview/e4e5/chat-compact-light-650.png)、[影片播放器](ui-preview/e4e5/remote-video-playback-controlled.png)、[音訊播放器](ui-preview/e4e5/remote-music-playback-controlled.png)、[作品網格](ui-preview/e4e5/works-grid-light-650-controlled.png)、[任務證據](ui-preview/e4e5/tasks-evidence-controlled.png)、[情境首頁](ui-preview/e4e5/home-daily-controlled.png)。均為實際 React 畫面，影音頁使用受控 Host 與合法測試媒體。

## 驗收界線

| 狀態 | 實際結果 |
|---|---|
| PASS | 當前 OpenVINO CPU／Intel GPU：每設備 first 1＋warmup 3＋measured 10，共 28 列；FP32 輸出正確。舊 GPU LUID 不符時先拒絕舊證據，再由驗收程序明確啟動短 Benchmark。推薦器沒有自動量測。 |
| PASS | 同次 UI 排序→採用→推薦憑證→TaskManager→原生推理→正確輸出。Benchmark `31746158980847c1938ef5335a5fd293`、推薦 `0b8ee64449994aefaa4ee8f1f92afb26`、Dispatch `bc849aff4ec141af9f69bd2b6ad88189`，選 CPU；不以張量結果推論文字模型。 |
| PASS | 圖片／影片／音訊契約、白名單、擁有者隔離、冪等性、中斷、續傳、雜湊、MIME／內容、34 MiB 影片串流、取消、空間與排隊配額、保留清理、作品保存。 |
| PASS | 合法 VP9／FLAC 在 Chromium 解碼為 1 秒，影片 160×96；保存設定、歌詞、重用、四尺寸、深淺色、鍵盤、Reduced Motion、大量作品分頁。這不是模型生成。 |
| PASS | 本機 Python 189 項：182 通過，7 項 Norton 回環 TLS 憑證替換案例交由乾淨 Windows CI。TypeScript／Vite、完整 Chromium 通過，保留既有 bundle 大小提醒。 |
| PASS | Windows CI 43200374886：189 項 Python 在封裝前後全數驗證、Chromium、TypeScript／Vite、NSIS 建置及安裝／捷徑／啟動／卸載保留資料。來源 4354605、下載後 SHA-256 已核對。 |
| NOT RUN | 本輪 llama.cpp 原生重測：現有官方工具受 Windows 應用程式控制阻擋，觀察 WinError 4551／server 0xc0e90002；未降低安全設定。既有協定與功能回歸仍通過。 |
| NEEDS GPU | Wan 2.1／ACE-Step v1 真實 GPU 生成、其他 GPU、多 GPU，以及 ComfyUI 獨顯與 CPU 真實並行；缺少完整權重／相容實機。本機 Iris Xe 的 OpenVINO 張量已實測。 |
| NEEDS NPU | 實體 NPU 推理與並行仍未驗證；沒有 CPU fallback 冒充 NPU。 |
| NEEDS REMOTE HOST | 雙實體機 LAN／VPN 長時生成、斷線與恢復；本輪以受控端到端及 Windows CI TLS 驗證協定。 |
| NEEDS CLOUD AUTH | 未啟用付費雲端或傳送實際提示詞。 |
| NOT RUN | 大型模型 >8 GiB 的實體載入、單模型 HETERO、正式簽章與 Release。動態容量計算測試不等於大型模型推理成功。 |

原始資料：[目前原生 Benchmark](evidence/media/benchmark-native-current.json)、[完整採用與派送](evidence/media/recommendation-native-real.json)、[媒體協定測試](evidence/media/protocol-tests.json)、[播放器與操作](evidence/media/ui-playback-controlled.json)。Windows CI／安裝包／SHA-256 以 [TEST_REPORT](TEST_REPORT.md) 本輪段落為準。

後續應先以實體獨顯 Host 完成 Wan／ACE-Step 的固定權重生成與長時間 LAN／VPN 驗收，再擴大 GPU 映射、精細資源量測與 NPU；不以增加 Lane 數或省略鎖提升並行。
