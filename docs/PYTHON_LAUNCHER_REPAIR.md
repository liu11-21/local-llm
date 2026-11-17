# 0.9.0 Python Launcher Repair

日期：2026-11-17（Asia/Taipei）。版本不變，僅 `dev/web-workspace`。

## 根因

**PASS：原始碼確認。** Start／Stop／Diagnose／Update／Rollback／Optional 六個 CMD 都直接執行 `py -3.12`。
Launcher 找不到登錄版本時，沒有再檢查其他可用 Python；所以使用者已能用絕對路徑執行 3.12.10，工作台仍可能無法啟動。
維護者目標主機的 Python Launcher 為何缺失登錄／回報 No installed Python，**NOT TESTED**：本機無該 QA 環境，沒有擅改 Registry 修補它。
修復直接讓啟動器可安全找到既有相容版本，不依賴使用者修理 PATH 或重裝 Python。

## 修正

六個薄 CMD wrapper → `Run-Web-Workspace.cmd` → `Find-Web-Python.cmd`。
selector 使用 Windows 內建 PowerShell 的固定 inline 指令；不載入 profile、不使用 ExecutionPolicy Bypass、不變更任何政策、不安裝任何程式。
Probe 的子程序環境強制 `PYTHON_MANAGER_AUTOMATIC_INSTALL=false` 並移除 `PYLAUNCHER_ALLOW_INSTALL`，
避免使用者環境允許 Launcher 自行安裝版本；不修改全域環境設定。[Python 官方 Windows 說明](https://docs.python.org/3/using/windows.html)。
stdout 只輸出已驗證的絕對 Python 路徑；來源／拒絕原因放 stderr。

順序：

1. PATH 中的 Python Launcher：`py -3.12`。
2. PATH 中的 python.exe／python3.exe／python3.12.exe。
3. HKCU／HKLM 的 Software\Python，64／32 位 registry views、PEP 514 Company／Tag／InstallPath，ExecutablePath 或預設安裝資料夾。
4. 使用者 Programs\Python、Program Files、Program Files (x86)、系統磁碟根目錄的 Python* 安裝資料夾。

每個候選用無 shell 的 Process argv 實跑 `-I -S -B -c`，讀取 JSON 的 `sys.executable`、版本及 pointer bits；
需要 Python 3.12.10+、低於 3.13、64-bit。找到後再以回報的絕對 interpreter 路徑執行一次相同驗證；CMD 最後才以該路徑執行 web_launcher。
零位元組 WindowsApps placeholder 不當作 interpreter，失敗／逾時／錯版本繼續下一個候選。單次 probe 最長 8 秒，異常清理該 probe。
Registry 讀不到時保留診斷並繼續其他來源，沒有讀寫安裝登錄。
正式啟動仍保留原 `official_python()` 的 Python Software Foundation Authenticode 驗證，不以版本輸出取代簽署者信任。

路徑與參數分開處理，CMD 關閉 delayed expansion；含空格的安裝路徑有單元案例，實際 Start／Stop 使用含空格資料目錄。
發行 ZIP 也包含兩個共用 helper，不需額外下載。CMD 保留失敗退出碼，`LOCALLLM_NO_PAUSE` 只控制測試是否等待按鍵，不影響任何驗證。

## 回歸

| 項目 | 狀態 |
|---|---|
| py 正常、py 失敗轉 PATH、僅 Registry、多版本、錯版本、32-bit、安裝路徑空格、完全不存在 | **PASS**：`test_python_launcher.py`，Mock 候選及版本，負例不執行假 EXE |
| 實際 finder | **PASS**：本機官方 3.12.10 x64，stdout 為可實跑的絕對路徑 |
| 自動安裝旗標 | **PASS**：父程序刻意允許自動安裝，實際 probe 子程序仍回報 allow-install 不存在、automatic-install=false |
| PATH 備援 | **PASS**：僅改測試子程序環境，移除 Launcher 搜尋目錄，實際找到 PATH Python |
| Registry 備援 | **PASS**：測試子程序 PATH 不含 py／Python，實際從 Registry 找到 3.12.10；未修改系統／使用者 PATH |
| 真 CMD Start／Stop／重啟 | **PASS**：官方 Python 3.12.10、重複啟動防護、程序退出及連接埠釋放 |
| 既有資料保留 | **PASS**：獨立合成 SQLite／模型庫標記／聊天／Agent／Team／作品／已保存 Runtime 設定逐項 hash，不重跑 Runtime CLI |
| 指定 RTX 桌機的 Launcher | **BLOCKED**：該 QA 目錄不在此主機；沒有宣稱已在另一台測過 |

真實結果：[PYTHON_LAUNCHER_TESTS.json](evidence/session-recovery/PYTHON_LAUNCHER_TESTS.json)。
腳本／PowerShell／Python 本身仍可能受裝置政策阻擋；遇到時保留政策並查看拒絕診斷，不假設改成腳本便能通過 SAC。

[PEP 514 官方登錄格式](https://peps.python.org/pep-0514/)；[最終 CI／ZIP／SHA](V090_DESKTOP_RETEST.md)。
