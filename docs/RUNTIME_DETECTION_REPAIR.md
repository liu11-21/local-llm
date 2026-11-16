# 0.9.0 Runtime 偵測與選取修復

日期：2026-11-16。分支 `dev/web-workspace`；檢查基準 `76b5d21`。版本維持 0.9.0 Development。
本輪不下載 Runtime／模型、不執行模型推理、不改安全政策、使用者 PATH 或資料庫格式。

## 已確認的缺口

以下是可由原始碼直接重現的缺口；沒有取得維護者 RTX 5070 Ti 主機的原始 API 回覆，不能認定其中一項就是該主機唯一根因。

| 層級 | 修復前的證據與行為 | 修復後 |
|---|---|---|
| 按鈕 | `desktop/src/LlamaRuntimePanel.tsx` 的偵測按鈕只呼叫 `load()` → `runtime-status` | 明確呼叫 `runtime-discover`，讀取掃描進度與每個候選的驗證結果 |
| PATH | `runtime_trust.discover()` 使用 `shutil.which`，只取得服務繼承的 PATH 首個匹配，加兩個 LOCALAPPDATA 位置 | `runtime_discovery.inventory()` 同時讀取 process PATH、當前 HKCU 使用者 PATH、HKLM 系統 PATH 與實際使用者 Local AppData；枚舉多個版本，保留每個位置的結果 |
| 版本／簽章 | 僅選取時才進行驗證，偵測沒有完整候選資料 | 每個候選先解析真實檔案，再檢查 SHA／Authenticode，最後才執行版本與安全參數探測 |
| 契約 | 回傳 `discovered: string[]`，不帶候選驗證狀態 | schema 2 新增 `candidates` 與 `scan`；保留 `discovered` 供舊介面相容 |
| 渲染 | 路徑只放進折疊進階區內的 `<datalist>`；沒有可見候選清單 | 常駐的「已安裝的 Runtime」清單，成功、失敗、拒絕原因均顯示；已驗證但未選取有獨立按鈕 |
| 選取 | 共用手動欄位可能保留舊路徑 | 每列以該候選路徑選取；後端再次完整驗證，然後才持久保存 |

上述缺口讓「掃到路徑」與「清單可見且能選取」脫節。沒有以假資料或單純前端勾選取代信任檢查。

## 完整偵測鏈與診斷欄位

1. React 偵測按鈕 → `rpc('runtime-discover')`。
2. `WebHTTPAdapter` → 同源 `POST /api/rpc`，JSON `{op,data}`；保留 Session、CSRF、Origin、Host 驗證。Desktop 仍透過既有 IPC 呼叫同一核心。
3. `workspace_web.WebWorkspace` → `WorkspaceApplication.response` → `Desktop.rpc` → 共用 `RuntimeManager.start_discovery`。
4. 背景掃描在 `scan.attempts[]` 保留 `input_path/sources/exists/is_file/is_link/reason`；`scan.errors` 保留登錄檔讀取失敗。忽略空白、相對與 UNC PATH 項目，避免隱性搜尋目前目錄或網路分享。
5. `resolve_runtime` 要求入口及實際目標均為 `llama.exe`；拒絕 `llama-server.exe`。WindowsApps 可能是正常 EXE，也可能是 AppExecLink；後者以唯讀 Win32 reparse API 解析實際目標，不執行別名字串。
6. `RuntimeTrust.inspect` 計算實際內容 SHA，使用 OS Authenticode。僅接受 `Valid` 且 subject CN、O 精確為 Hugging Face。無簽章、錯誤簽署者及無法驗證均不進入 CLI 探測。
7. 已通過簽章才以安全 argv、無 shell 執行 `version`、`serve --help`、`serve --list-devices`。不給模型路徑或 `-hf`，不啟動推理服務。必要安全參數不支援時標為 `unsupported`；裝置列表失敗保留紀錄，不把 CPU Runtime 假裝成 GPU 可用。
8. 每次 CLI 最長 15 秒，輸出最多 256 KiB，Windows Job Object 關閉清理探測程序樹。每輪最多 12 個候選，90 秒預算在候選之間檢查；正在驗證的候選仍有各探測／簽章逾時，因此不是 90 秒硬中止。截斷及未完成候選有明確診斷。
9. CLI 後再次比對 SHA，避免檢查中變動。`candidates[].trace` 記錄 resolve／authenticode／cli，`probes[]` 記錄 argv、退出碼、timeout、cleanup、截斷的文字；錯誤有 `reason.code/message`。
10. React 每 700ms 輪詢掃描狀態，顯示候選與拒絕原因；「完整掃描診斷」可看到實際搜尋位置。只有 `verified=true` 才出現選取按鈕。

候選狀態：`found` 已找到、`verifying` 驗證中、`verified` 已驗證未選取、`unsupported` 不受支援、`failed` 驗證失敗、`selected` 已選取、`running` 實際引擎執行中；掃描初始為 `not_detected`。執行中會檢查主引擎及 DeviceExecution 的實際本機 scope，不拿排隊／雲端任務推定本機已啟動。

`runtime-select` 再驗證並原子寫入原本的 `llama-runtime.json`，保存 resolved path、內容 SHA、版本、設備與驗證來源；保留 SQLite、模型、聊天。載入後重新掃描已保存路徑。Chat、Agent、Team、Benchmark、Remote Host 均沿用既有 `RuntimeManager.executable/factory`，沒有增加另一份 Runtime 設定。沒有 GGUF 只表示模型待準備，不會隱藏已驗證 Runtime。

## 手動既有檔案與安全邊界

「選擇既有 llama.exe 檔案」呼叫 `runtime-pick`，必須明確 `confirmed=true`。官方 Python 開啟 Windows 原生 GetOpenFileNameW；120 秒未完成會清理選擇器。它只回傳本機路徑，不上傳、複製、下載或執行選中的檔案。選完走同一 `verify_candidate` 閘門，仍需明確按「選取此 Runtime」。取消不改選取。也保留進階完整路徑欄位。

此功能不新增 Tk、瀏覽器原生橋接 EXE 或原生 Python wheel。Native picker 需要互動 Windows 桌面；本輪開窗成功，但操作工具逾時，完整點選流程保持 **NOT VERIFIED**。無互動桌面可使用手動路徑欄位；不是要求修改 PATH。Desktop frozen Worker 維持路徑輸入方式。

簽章有效、CLI 通過、裝置辨識、模型服務運行、GPU 推理、SAC 放行是不同證據。新狀態不會讓後者自動通過。詳細路徑與驗證輸出只提供已認證的本機工作階段，分享診斷前請遮蔽帳號／私人目錄。

## 驗證範圍

| 項目 | 證據／結果 |
|---|---|
| 自動測試的 PATH／WindowsApps／多版本 | `test_runtime_discovery.py`，不依賴本機安裝 Runtime；含 stale process PATH、使用者／系統 PATH、一般 WindowsApps EXE、AppExecLink、壞別名、錯檔名 |
| 信任負例／程序 | 同檔：無簽章、錯簽署者、檔案不存在、CLI 退出碼／逾時、不支援參數；負例不執行測試 EXE。真逾時只執行官方 Python sleep 子程序並確認清理 |
| HTTP 契約 | `test_workspace_web.py`：缺檔錯誤候選完整通過真 ASGI/RPC 回應；picker 需確認、取消不選取；原 Session／CSRF／DNS rebinding 測試保留 |
| 清單、選取、重新載入、缺模型 | `desktop/tests/runtime-detection-ui.mjs` 控制 API fixture；已驗證未選取、拒絕未簽署候選、選取保存、四尺寸／雙主題；不當成真硬體驗收 |
| 共用核心 | Python 測試確認儲存恢復、相同引擎 factory、Host 設定、缺模型拒絕；完整既有 Agent／Team／Benchmark／遠端回歸仍執行 |
| 開發主機實際安裝偵測 | **BLOCKED（目標驗收）**：本機 PATH、HKCU／HKLM 與 WindowsApps 沒有使用者所述的安裝檔；查不到是正確回覆，不以空清單通過目標驗收 |
| 手動既有 QA SDK | 選用 `desktop/tests/runtime-detection-real.mjs` 只讀既有 SDK；真 Authenticode／CLI／HTTP／瀏覽器、reload、後端重啟及零模型驗收，與已安裝 PATH 驗收分開記錄 |
| RTX 5070 Ti＋Intel Graphics＋SAC | **BLOCKED / NEEDS HARDWARE**：不是本開發主機，未做 Workspace 推理，不使用既有其他版本的推理紀錄代替 |

本機完整 Python 的未略過原始執行遇到遠端 TLS 憑證驗證錯誤；此主機已有安全軟體攔截 loopback TLS 的紀錄。保留失敗 log；使用既有 `LOCALLLM_TEST_TLS_INTERCEPTED=1` 只略過對應 7 項測試，沒有修改 TLS 或安全政策。乾淨 Windows CI 必須不設定此旗標並通過。另一個略過為非本輪所需的 Desktop 封裝 EXE smoke。

最新 Commit、CI、Artifact、SHA 與逐項結果見本文件末尾；早期 0.9.0 交付中的推理成功紀錄不算本輪驗收。

## 使用者目標主機的最後驗收

1. 停止舊服務，以新 Web ZIP 啟動並保留原資料目錄。
2. 進「運算環境」按偵測；應出現官方簽章、版本／build、真實路徑與「已驗證 · 尚未選取」。已選取者顯示已選取。
3. 按「選取此 Runtime」，重新載入頁面，確認仍是同一路徑／版本。
4. 到聊天：QA 資料夾無模型時應提示模型待準備，不自動下載，也不因缺模型丟失 Runtime。
5. 核對 Runtime 回報的 RTX 5070 Ti 與 Intel Graphics；硬體監控卡片不足以代替 Runtime `serve --list-devices`。
6. 若失敗，展開候選驗證記錄與完整掃描診斷，記錄拒絕碼、輸入／resolved 路徑、退出碼及簽章。可用原生選擇器指定同一既有檔案，仍走完整驗證。不需改 PATH、不需重裝 Runtime。

以上目標主機步驟未取得實際結果前，保持 BLOCKED。

## 官方技術依據

- [上游 Windows 安裝腳本](https://llama.app/install.ps1)：目前把實體 llama.exe 移入 Microsoft WindowsApps，不能假設該資料夾內全部都是 alias；本輪只讀取指引，沒有執行腳本。
- [Microsoft reparse 操作](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-point-operations)、[FSCTL_GET_REPARSE_POINT](https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ni-winioctl-fsctl_get_reparse_point)；AppExecLink 第三字串目標亦對照 [libuv 上游實作](https://github.com/libuv/libuv/blob/v1.x/src/win/fs.c)。以獨立 ctypes 程式呼叫 OS API，沒有移入 libuv 程式碼。
- [Windows GetOpenFileNameW](https://learn.microsoft.com/en-us/windows/win32/api/commdlg/nf-commdlg-getopenfilenamew)。

## 本輪交付紀錄

本機結果：252 Python tests，244 通過、8 略過（上述 TLS 7 項與 Desktop 封裝 smoke 1 項）；未略過執行的 TLS 失敗另保存，不視為遠端實測通過。
TypeScript／Vite Web 建置、完整 Chromium layout 回歸通過；包含既有 Agent／Team／Benchmark／遠端流程與新增偵測案例。
聊天頁直接顯示已選 Runtime／缺 GGUF 的提示，無須展開設定才能區分兩者。

首輪 Windows CI `43889488137` 找到既有測試仍以輸入字串比對 Runtime 路徑；runner 的 TEMP 是 `RUNNER~1`，
修復後的 canonical resolved path 是 `runneradmin`。調整為 resolved path 加 samefile 比對，保留內容變動拒絕測試，沒有放寬產品驗證。

真實手動 SDK 驗收：`build/v080-upstream/llama.exe` 是既有檔案，非本輪下載，也不在已安裝 PATH。
Authenticode、版本／安全 CLI、Web 選取與 reload、後端重啟後保存、聊天讀取同一設定及零模型送出停用通過；
本機安裝候選數為 0。完整已遮蔽工作目錄的結果見 [手動既有 SDK 證據](evidence/runtime-detection/manual-sdk.json)。
不宣稱原生互動檔案選擇器、目標 RTX／SAC 或推理已通過。

待修復 Commit 的 Windows CI 完成後填入最終 Artifact 與雜湊；此段不是目標實機通過聲明。
