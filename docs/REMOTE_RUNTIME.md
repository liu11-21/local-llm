# 使用另一台 Windows 電腦運算

Host 只提供文字聊天。兩台電腦需能透過 LAN 或受信任的私人 VPN 連線。請在 Host 安裝 llama.cpp 和 GGUF，並先用本機聊天驗證模型。Host 在本機 Windows 帳戶中執行，關閉工作台即停止分享。

## 在桌機啟用

1. 開啟「運算環境 → 連接另一台電腦 → 將此電腦設為運算主機」。
2. 選擇兩台電腦共用的私人網路，按「分享此電腦算力」並確認。工作台會建立或重用專用 TLS 憑證，並顯示一次性邀請。預設 HTTPS 埠是 9443。若 Windows 防火牆需要新增規則，請僅允許受信任的私人網路和客戶端，並避免把該埠轉發到公網。
3. 用已信任的管道交付邀請。請從主機展開「核對主機指紋」，透過另一個可信管道核對 SHA-256。邀請五分鐘內有效，每次只能使用一次。

自動模式將加密 PKCS#8 與由 Windows DPAPI 保護的密碼分別保存。位址改變、憑證將到期，或使用者勾選更新時，需確認後才會更新憑證並撤銷舊配對。 [PyCA 憑證 API](https://cryptography.io/en/stable/x509/tutorial/)

進階手動模式可指定私人位址、連接埠、公開 PEM 憑證及對應 PEM 私鑰。憑證須在有效期內，且 SAN 必須包含該 IPv4。

若團隊已有私有 CA，請使用針對這台主機 IPv4 發出的伺服器憑證。自行管理的單台 Host 也可使用由管理者產生的單一自簽 TLS 憑證，並透過一次性邀請將公用憑證帶到筆電。私鑰應放在只有 Host 帳戶可存取的資料夾。更換憑證後請重配對。 [Python TLS 驗證](https://docs.python.org/3/library/ssl.html)

<details>
<summary>在桌機以 PowerShell 7 建立專用憑證</summary>

以下程式會在目前 Windows 帳戶的本機資料夾產生 PEM，保留既有檔案。把印出的兩條路徑填進 Host 的 TLS 設定。

```powershell
$address = [Net.IPAddress]::Parse((Read-Host '輸入桌機的私人 IPv4 位址'))
$folder = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'LocalLLM\remote-tls'
$certFile = Join-Path $folder 'host-cert.pem'
$keyFile = Join-Path $folder 'host-key.pem'
if ((Test-Path -LiteralPath $certFile) -or (Test-Path -LiteralPath $keyFile)) {
    throw '已有 PEM 檔案。請使用既有憑證，或選用新的資料夾。'
}
$null = New-Item -ItemType Directory -Path $folder -Force
$rsa = [Security.Cryptography.RSA]::Create(3072)
try {
    $request = [Security.Cryptography.X509Certificates.CertificateRequest]::new(
        'CN=Local LLM Private Host', $rsa, [Security.Cryptography.HashAlgorithmName]::SHA256,
        [Security.Cryptography.RSASignaturePadding]::Pkcs1)
    $san = [Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
    $san.AddIpAddress($address)
    $request.CertificateExtensions.Add($san.Build())
    $request.CertificateExtensions.Add(
        [Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($false, $false, 0, $true))
    $now = [DateTimeOffset]::UtcNow
    $cert = $request.CreateSelfSigned($now.AddMinutes(-10), $now.AddDays(180))
    try {
        [IO.File]::WriteAllText($certFile, $cert.ExportCertificatePem())
        [IO.File]::WriteAllText($keyFile, $rsa.ExportPkcs8PrivateKeyPem())
    } finally { $cert.Dispose() }
} finally { $rsa.Dispose() }
$certFile
$keyFile
```

</details>

## 在筆電連線

貼上完整邀請。核對視窗中的私人位址和 SHA-256 指紋與主機一致後才確認。配對後先確認模型清單，再點「開始聊天」。每次送出提示詞和相關對話時，工作台都會顯示目的地並請求同意。選擇隱私優先或僅本機會阻擋傳送。重新開啟工作台後，按「重新連線」可使用保存的配對。裝置失去信任時，請在 Host 的「已配對裝置」撤銷。

| 畫面 | 原因與處理 |
|---|---|
| 無法連線 | 確認 Host 仍開啟、私人網路位址和防火牆規則正確。 |
| TLS 驗證失敗 | 確認憑證有效、SAN 符合位址及網路沒有替換憑證。修正後向原主機取得新邀請。 |
| 認證失敗 | 邀請逾時、已用過或裝置被撤銷。請由 Host 建立新邀請。 |
| 主機在線但不能推理 | 檢查 llama.cpp、GGUF、可用 RAM 或既有 ComfyUI 工作。是否能使用 GPU 要以 Host 實際載入為準。 |

## 安全與任務界線

- Client 透過 TLS 1.2 以上驗證邀請內的憑證、IP SAN 和對端憑證身分。只有驗證完成後才傳送邀請或配對 Token。
- Host 只保存 Token 的 SHA-256。Client 的連線資料與 Windows DPAPI 保護的 Token 分表儲存。遠端 API 只允許配對、能力查詢、文字任務、狀態、串流、取消及撤銷自己。Host 啟停和管理其他裝置只能從本機 IPC 操作。 [Windows DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)
- 文字工作沿用本機運算槽與引擎分層。Host 同時最多收四筆尚未結束的遠端任務，並對請求大小、HTTP 連線數和任務時間設限。遠端使用者僅能選擇 Host 已列出的 GGUF。
- 任務與配對裝置綁定。SSE 斷線時會以同一任務 ID 重連，避免重複生成。仍無法連線時可複製錯誤中的任務 ID 到「查詢中斷的遠端任務」。Host 只在記憶體保留近期結果，最長十分鐘，停止或重啟後無法查詢該結果。若 Client 送出取消時已離線，Host 仍按自身時間上限停止等待。

Windows CI 的 TLS、配對、SSE 與撤銷測試使用隔離回環服務和受控模型輸出。跨兩台實體 Windows 電腦的 GPU 推理需要另行驗收。
