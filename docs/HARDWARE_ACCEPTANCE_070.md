# 0.7.0 實體 Host／Client 驗收

工具 `workspace_acceptance.py` 預設只偵測、不下載、不啟動模型。先關閉使用同一資料夾的 Workspace；工具持有相同 OS 鎖，結束前收尾程序。請用相同 Windows 帳號執行，配對金鑰仍由 DPAPI 保護，不把 Token 或邀請寫入報告。

預定 RTX 5070 Ti Host／Iris Xe Client 不代表目前可存取。先各自診斷；缺少目標 GPU 標 NEEDS GPU，NPU 缺少標 NEEDS NPU。PyTorch 以便攜版自己的 Python 查版本、CUDA、裝置、編譯架構並真正執行小型 CUDA 矩陣；不能只看 NVIDIA 驅動存在就判定相容。

```powershell
# Host：只診斷已安裝環境，不下載
python workspace_acceptance.py --data "$env:LOCALAPPDATA/LocalLLM" --output host-diagnosis.json
# 檢查報告中 needed、free、每份固定版本權重與 SHA-256。
# 缺少 Runtime／權重時，須另由使用者在 App 確認下載與磁碟需求，再準備。
# NVIDIA GPU profile 對應固定官方便攜包；不任意更新 PyTorch 或自訂節點。

# 完整權重已存在後，明確執行真實模型測試。缺檔會拒絕，不補下載。
python workspace_acceptance.py --data "$env:LOCALAPPDATA/LocalLLM" --output host-wan.json --execute --kind video
python workspace_acceptance.py --data "$env:LOCALAPPDATA/LocalLLM" --output host-ace.json --execute --kind music --prompt "instrumental ambient piano"
# 取消測試，必須等後端確認取消及關閉程序後才結束
python workspace_acceptance.py --data "$env:LOCALAPPDATA/LocalLLM" --output host-cancel.json --execute --kind video --cancel-after 15
```

Host 報告保存實際 GPU／驅動、PyTorch／CUDA、各權重清單、版本／revision、Task ID、Job 事件、輸出雜湊與媒體 metadata。每秒保存系統 RAM／各 GPU 的 nvidia-smi 取樣，包含其他程序的使用量，未當作單一模型的專屬佔用；取樣最大值是觀察峰值，不宣稱硬體真峰值。ComfyUI 原始日誌位於該便攜版目錄 `local-llm-comfyui.log`，連同報告與輸出媒體保留。結束時關閉工具所啟動的 ComfyUI，保存收尾狀態。工具不會停別台 Host 的服務。

## 私人網路雙機

1. Host 開啟 Workspace 分享，只選可信私人 LAN／VPN 位址；Client 在 App 配對並核對兩端 SHA-256 憑證指紋。
2. 保持 Host App 運行；關閉 Client App 後，以 Client 資料夾執行工具。先診斷能力與指紋，不能以文字引擎健康推定影音可用。
3. 每種任務另行執行並確認傳送；下列為有意傳送的測試提示。不得將真實私密資料放入公開報告。

```powershell
python workspace_acceptance.py --mode client --runtime HOST_ID --data "$env:LOCALAPPDATA/LocalLLM" --output client-diagnosis.json
python workspace_acceptance.py --mode client --runtime HOST_ID --data "$env:LOCALAPPDATA/LocalLLM" --output client-video.json --execute --consent --kind video
python workspace_acceptance.py --mode client --runtime HOST_ID --data "$env:LOCALAPPDATA/LocalLLM" --output client-music.json --execute --consent --kind music
python workspace_acceptance.py --mode client --runtime HOST_ID --data "$env:LOCALAPPDATA/LocalLLM" --output client-image.json --execute --consent --kind image
# 原遠端工作已完成：只抓原 Job，絕不重新提交推理
python workspace_acceptance.py --mode client --runtime HOST_ID --data "$env:LOCALAPPDATA/LocalLLM" --output recovered.json --recover JOB_ID --consent --kind video
```

4. 核對 Client 報告的 Host ID、憑證指紋、能力、原遠端 Job ID、Host 原始日誌及檔案 SHA-256；App 作品庫播放並重用設定。Client 報告中的推理依 Host 回報，需與 Host 原生生成報告及日誌合併，才能作為雙機真實模型證據。
5. 大檔生成／下載中手動斷開 Client 網路，記下原 Job，恢復網路後先查原 Job，再以 recover 下載；記錄 .part 與 Range 回應，對照原始檔 SHA-256。不要以工具的小型 9 影格測試冒稱大型／長時間驗收。
6. 另一案例在工作中正常關閉／重啟 Host，原未完任務須 interrupted，不得自動成功或重跑。再次手動生成須新 Request ID。對照兩端資料庫與原始日誌。
7. 重複同一 Request／不同 Client、憑證錯誤、Owner 權限、Range／SHA／取消／配額的協定自動測試見 `test_remote_*.py`；雙實體機仍另標 NEEDS REMOTE HOST。

Wan 使用完整 UNET＋文字編碼器＋VAE，ACE-Step 僅 v1 3.5B。不得用合法固定媒體或受控端點代替 GPU 推理證據；沒有設備時工具輸出 NOT RUN／NEEDS GPU，保留其他測試進度。大型模型 >8 GiB 程序載入需另外確認實際 RAM、OS 餘量與使用者上限，不以工具數值計算宣稱已載入成功。
