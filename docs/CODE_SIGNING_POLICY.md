# Code signing policy — candidate

現況：0.7.0 Development **unsigned**；SignPath **NOT APPLIED / NOT APPROVED**。不宣稱憑證、發行者身分或 Foundation 贊助。未核准前不使用其簽章服務致謝聲明。

擬定 Authors／Reviewers／Approvers 三角色，姓名均待指定；全員 GitHub／SignPath MFA 尚待驗證。正式簽章應由受保護發行環境、非作者審查與每次人工核准控制。分支及環境設定不是僅寫文件即可生效，目前不宣稱已受保護。

申請簽章的候選範圍僅為自有軟體建置產物。Rust shell 含 upstream 靜態碼、PyInstaller Worker 含 bootloader、NSIS installer／uninstaller 含生成碼，均需明確核准 artifact configuration。其他 Python／crypto／llama／Microsoft DLL、第三方 EXE／PYD 及模型不列為自有簽章對象。保留上游簽章及原 Notice。

舊版 build_windows.py 的本機憑證選項限明確 LocalLLM.exe wrapper，禁止遞迴重簽 payload。本輪未執行該選項；這個修正不代表 Foundation 已接受 wrapper 或 Inno 簽章範圍。

每次候選須保留 commit、Actions Run、來源證明、鎖檔、SBOM、所有 PE 來源／hash／簽章狀態、版本及 installer／uninstaller 驗證。簽章只能在審查後對已上傳的對應 artifact 處理；不接受 PR、任意 URL 或未綁定來源的檔案作正式輸入。

撤銷／事故流程依 SECURITY.md：停止發行、保全證據、評估受影響來源／Token／產物，必要時向服務方請求撤銷。尚未建立服務權限或私人 Token；不會關閉系統安全防護。
