# 安裝 ComfyUI 創作模型

1. 在桌面工作台選擇「圖片生成」、「影片生成」或「音樂生成」。
2. 在「安裝或檢查本機模型」選擇適合的 Windows 便攜版。首次使用可在此下載 ComfyUI。
3. 核對來源、授權、權重與所需空間，勾選同意後按「一鍵安裝模型」。安裝進度、取消與重試也可以從任務中心操作。
4. 權重驗證後啟動該便攜版。工作台會向 ComfyUI 重新查詢內建節點和權重。也可手動「重新檢查」。

安裝清單固定到 Hugging Face Git revision，並包含模型的 LFS SHA-256。圖片需要一個檢查點，影片需要 diffusion model、文字編碼器和 VAE，音樂需要一個整合檢查點。 [Stable Diffusion 1.5](https://huggingface.co/Comfy-Org/stable-diffusion-v1-5-archive/tree/9cfd069101959ca3828bf9c04a4419870832b74f) · [Wan 2.1](https://huggingface.co/Comfy-Org/Wan-2.1/tree/123acf1cc74bccbb9bfff8ac1ee72edc08c2341d) · [ACE-Step](https://huggingface.co/Comfy-Org/ACE-Step/tree/ea4f3d349e84d5c098cc8e8b904a30fde59fc99a)

網路中斷時可重試同一組安裝，下載器會重新校驗已完成的區段。重開工作台後也可從創作頁再次選擇同一組模型及便攜版。取消會清除該次的暫存下載，已驗證並完成安裝的其他權重仍保留。同名大小衝突要由使用者自行處理。同大小的現有權重先顯示「已偵測」，可使用「驗證權重」重新計算 SHA-256。檔案變更時，舊校驗結果失效。ComfyUI 預檢只代表能辨識權重及必要節點。

下載只寫入所選受管便攜版的標準模型目錄，不安裝自訂節點或執行上游安裝腳本。若使用自行配置的 ComfyUI，請在原安裝中放置權重，再回創作頁確認節點和權重。RAM／VRAM 門檻會隨解析度、影格、秒數、硬體及 ComfyUI 設定而變動，介面把尚未實測的門檻顯示為未知。
