# 遠端媒體傳輸契約

媒體 schema 2 擴充既有 TLS 協定 1；Runtime schema 1 繼續使用。產品 music 映射 audio，v1 PNG 相容。fetch_image／await_image 舊名稱保留，內部共用三種媒體。

| 類型 | 白名單 | MIME / 格式 | 單檔上限 |
|---|---|---|---:|
| image | sd15、sd15-preview | image/png | 32 MiB |
| video | wan21 | video/webm，VP9 | 2 GiB |
| audio | ace-step（v1） | audio/flac | 512 MiB |

Descriptor 含 schema、id／media_id、job_id、owner_client_id、host_id／runtime_id、model_id／model_version／model_revision、workflow、mime／extension、bytes／sha256、options、created／updated／completed、status、download_status、retention。ID 不接受路徑；下載端確認 Host ID／Job ID 及固定類型。Host 每次請求重新驗證 Bearer Token 與任務擁有者，Token 僅在 Header，不放 URL。

輸入只接受提示詞、適用歌詞、Workflow、受限參數和 Request ID；Host 驗證版本、型別、範圍、影片總像素量及白名單，排隊後開始前再確認影音權重完整性。音樂沒有 v1.5 Adapter 混用。相同 Owner／Request 的相同內容冪等，不同內容 409；其他 Owner 無法查詢或讀取作品。

完整下載 200、續傳 206；驗證 Content-Length、Content-Range、ETag、MIME、SHA-256 及有界內容格式。每次最多兩筆 Host 傳輸，使用固定 256 KiB 區塊，下載到受管理片段再原子發布。v2 PNG 檢查 CRC，WebM 檢查容器及影像軌，FLAC 檢查 STREAMINFO。PNG／WebM 尺寸最多 4096×4096，音訊最多 600 秒／192 kHz、影片最多 7200 秒；實際生成仍受更小的 Workflow 參數上限約束。完整解碼另由播放器負責；合法 VP9／FLAC 已實際播放。

Client 暫存 4 GiB，跨 Host 配額鎖避免並行超配；Host 結果 8 GiB，含排隊工作最大輸出保留；磁碟另外留 256 MiB。磁碟／配額不足拒絕，取消不發布，斷線續傳，錯誤 SHA 片段刪除後可重下載，不重新生成。大檔不放 SQLite。

Host 媒體工作含排隊上限 7200 秒，ComfyUI 單次等待上限 3600 秒；Client 等候 7200 秒後保留 Job ID。沒有可靠 ETA 時只顯示狀態，重連不無條件重跑。Host 啟動中斷未完紀錄，Client SQLite 14 保存 Prompt／Lyrics／參數與下載狀態。

新 Host 結果保留 7 天，啟動、提交與每 5 分鐘清理過期受管理結果及孤立檔；任務中繼資料仍保留。舊 v1 沒有期限的作品保留。Client 清理其他超過 7 天的片段，當次要求續傳的片段保留。已保存 Client 作品不自動刪除。[隱私](PRIVACY_STORAGE.md)。

[原始測試](evidence/media/protocol-tests.json)、[合法媒體與播放器](evidence/media/ui-playback-controlled.json)。受控推理／合法測試檔的 PASS 不表示 Wan／ACE-Step GPU 已生成成功；雙實體主機、完整權重及長時間模型驗收仍需外部硬體。
