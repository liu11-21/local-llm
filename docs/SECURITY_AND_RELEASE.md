# Windows 安全與發行

## v0.6.1 稽核

公開 [v0.6.1](https://github.com/liu11-21/local-llm/releases/tag/v0.6.1) 的 x64 EXE 為 54,519,100 bytes，SHA-256 `67eaf5c6b44a8ad7fce784ac55a0e2449399d10eed9ec08357d350b322705f7e`，重新下載與 GitHub 資產一致。Authenticode 為 `NotSigned`。未執行此舊檔。靜態 PyInstaller CArchive 可列出 `python312.dll`、`base_library.zip`、Tk 元件、llama.cpp 和授權。嵌入引擎的 25 個二進位或其他授權檔與固定的 b11810 官方 ZIP 一致；改名後的 MIT 授權與同版官方來源相同。

v0.6.1 標籤使用 `--onefile --windowed`，未顯式禁用 UPX，未留 PyInstaller 版本鎖。EXE 外層 PE 無典型 UPX 區段；這不足以證明所有嵌入檔均未壓縮。onefile 於啟動時會將內部依賴解壓至暫存目錄，再由程式按需啟動模型引擎。來源檢視涵蓋本專案的 subprocess、模型／更新／ComfyUI 下載與打包設定。未發現嵌入引擎遭替換的證據；未做全檔動態鑑識或各防毒廠商鑑定，不能據此宣告無感染或誤判。使用者提供的 `Custody` 未附可識別的產品偵測名稱。

| 打包 | 行為 | 狀態 |
|---|---|---|
| v0.6.1 PyInstaller onefile | 單檔、啟動時解壓，內附 Python、Tk 及引擎 | 已稽核，不建議做主要安裝渠道 |
| v0.6.2 PyInstaller onedir + Inno Setup | 每使用者安裝，有捷徑；啟動讀取安裝目錄；仍內附引擎 | 既有備援 |
| Tauri / NSIS + Python onedir | 每使用者安裝，外殼與 Worker 分離，Worker 無 UPX，主包不含引擎、模型或 ComfyUI | 開發方案，完整安裝尚待驗收 |

llama.cpp 以 [b11810 官方資產](https://github.com/ggml-org/llama.cpp/releases/tag/b11810) 固定長度、SHA-256 和兩份授權，先在資料目錄內暫存，驗證成功才安裝。既有 ComfyUI 下載驗證固定的官方 SHA-256。Hugging Face GGUF 使用版本化連結、大小／格式檢查及 HTTP Range，任意 GGUF 尚無統一的獨立可信雜湊；本機引擎探測也可能使用已有的引擎。舊版更新驗證 GitHub 官方資產 SHA-256。

## 建置與三種驗證

GitHub Actions 對開發分支只產生 Artifact：固定工具鏈、Actions commit、npm／Cargo lock、Windows packager 版本，跑測試，產生安裝 EXE、`BUILD.json` 和 `SHA256SUMS.txt`。暫時不啟用自動更新或簽章。安裝程式和 Worker 都沒有可信 Authenticode。

1. **Windows Authenticode**：正式憑證／服務可用後，在可信的 CI job 簽主 EXE、Worker 自有 PE、安裝程式與卸載程式，使用時間戳；原封保留第三方已有簽章。簽完逐一跑 `signtool verify /pa /all /v`，對安裝器及安裝後檔案檢查發行者。Tauri 用 Windows [簽章設定](https://v2.tauri.app/distribute/sign/windows/) 或核准服務；私鑰不進 Git 或開發 Artifact。簽章不保證不被防毒攔截。
2. **Tauri 更新簽章**：待正式通道驗收後加入 [Updater](https://v2.tauri.app/plugin/updater/) 公鑰、HTTPS manifest 與版本遞增規則，隔離私鑰並測試錯誤簽章、降版、失敗復原、資料保留。不能替代 Windows 發行者驗證。
3. **SHA-256**：依最後簽完的檔案重算公開 checksum，核對下載完整性；本身不證明發行者身份。

[SignPath Foundation](https://signpath.org/terms.html) 可評估，但目前庫無明確根授權，不能確認資格。先由維護者決定開源授權、確認第三方授權與申請資格，再接入受保護的自動建置。Microsoft Store 是另一選項：[Store 對 MSIX 與 EXE/MSI 的要求不同](https://learn.microsoft.com/en-us/windows/apps/publish/faq/get-started-with-the-microsoft-store)；獨立 EXE 不能依賴 Store 代簽。

## 隔離事件處理

記錄精確資產名、版本、來源、SHA-256、簽章、Windows 版本、安全產品與定義版本、偵測名稱與事件時間。保留可重現步驟與不含個資的記錄。先核對官方產物，交叉比對來源／CI／依賴，記錄複現與各產品結果；可疑變更先停止公開發行。經核准才向 [Microsoft Defender](https://www.microsoft.com/wdsi/filesubmission)、[Norton](https://support.norton.com/sp/en/us/home/current/solutions/kb20090410134005EN)、[Avast](https://www.avast.com/false-positive-file-form.php) 或 [AVG](https://www.avg.com/en-ww/report-false-positive) 提報公開樣本與偵測 ID。本次未提交樣本，也未變更防毒設定。
