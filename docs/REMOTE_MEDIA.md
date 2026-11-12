# 用已配對電腦生成圖片、影片與音樂

## 0.7.0 硬體驗收入口

遠端媒體繼續共用 E4 契約與傳輸；0.7.0 增加真正可重跑的 workspace_acceptance.py。預設診斷且不下載，execute 才生成，Client 額外 consent；已配對主機須先核對指紋。保存實際 Task／Job、能力、模型 revision、資源取樣、媒體雜湊；recover 僅下載原 Job，不重跑推理。

本環境是 Iris Xe，未取得 RTX 5070 Ti／雙實體主機／完整 Wan 與 ACE 權重。協定與播放器 PASS 不等於真實生成；實機維持 NEEDS GPU／NEEDS REMOTE HOST。[可重跑步驟](HARDWARE_ACCEPTANCE_070.md) · [本輪證據](V070_DELIVERY.md)。

目前支援 SD 1.5、Wan 2.1 T2V 1.3B 與 ACE-Step v1 的受管理 Workflow。遠端協定、傳輸、作品保存與播放器已完成；真實 Wan／ACE-Step GPU 生成及雙實體 Host 驗收仍待完整模型和相容硬體。[完整驗收](E4_E5_DELIVERY.md)。

## Host 準備

在相應創作頁選本機環境，查看模型、授權、完整權重及磁碟摘要，下載／驗證後啟動受管理 ComfyUI。影片需要 UNET、文字編碼器及 VAE 三份權重；單有 VAE 不表示已就緒。音樂固定 ACE-Step v1 3.5B，沒有混入 1.5 節點。

到「運算環境 → 連接另一台電腦」分享算力並配對。主機在線、文字引擎健康、各媒體 Workflow 就緒分開顯示。影片／音樂必須完整 SHA-256、節點與服務通過，開始時再次確認。[權重／授權](evidence/media/weight-source-audit.json)、[節點契約](evidence/media/workflow-source-audit.json)。

## Client 使用

1. 選圖片／影片／音樂與模型流程。
2. 選已配對 Host；本機未準備且有相容 Host 時，頁面提供捷徑。
3. 輸入提示詞、適用歌詞及參數，開始生成。
4. 核對目的地及傳送內容，按「同意並送出」。
5. 追蹤任務，完成後自動下載、驗證 SHA-256 並保存作品。
6. 預覽／播放，查看參數或一鍵重用。

Wan 提供寬高、影格、FPS、Steps、CFG、Negative、Seed；ACE-Step v1 提供秒數、Steps、CFG、Seed、Lyrics。Host 重新驗證範圍，影片總像素量另受限制；任意節點圖、檔案路徑、程式及命令均拒絕。

## 恢復與保存

斷線保留 Host／Job ID，在運算環境查詢原任務；已完成結果可下載／續傳，無須重新生成。Client 保存原 Prompt／Lyrics／設定；Host 重啟中斷未完工作，不自動標成功或重跑。每 Client 同時最多兩項、Host 合計四項，計算仍受資源鎖及預算限制。

PNG 32 MiB、VP9 WebM 2 GiB、FLAC 512 MiB；Host 結果配額 8 GiB，Client 片段 4 GiB。新 Host 結果保留 7 天，已下載的 Client 作品保留。遠端輸出、片段及縮圖有各自清理政策，不刪模型與 Client 原作品。[傳輸契約](MEDIA_TRANSPORT.md)、[隱私保存](PRIVACY_STORAGE.md)。

作品庫支援網格／清單、類型／模型／來源、日期排序與搜尋，24 筆分頁；只預覽選中的原始媒體。有界縮圖在生成預覽或首次開啟時建立。[合法測試媒體的播放器紀錄](evidence/media/ui-playback-controlled.json) 不表示模型生成成功。
