# Code signing policy — candidate

現況：0.7.0 Development **unsigned**；SignPath **NOT APPLIED / NOT APPROVED**。不宣稱憑證、發行者身分或 Foundation 贊助。未核准前不使用其簽章服務致謝聲明。

擬定 Authors／Reviewers／Approvers 三種責任，實際名單與全員 GitHub／SignPath MFA 尚待維護者確認。每次正式簽章須人工核准。公開 Foundation 條款對 Reviewers 的明文要求是審查非 committer 的提案；沒有據此推定所有本人提交都強制另一人審查。對建置、權限及簽章變更取得獨立審查是本專案較嚴的建議，不能寫成 Foundation 已宣布的通用最低人數。

單人候選方案：由維護者承擔 Author、審核外部提案及 Approver 的責任，透過固定來源、MFA、手動檢查 candidate／Notices／provenance、每次人工核准及稽核紀錄控制風險；是否可兼任／自批需 Foundation 書面確認。另一方案是維護者任 Author，另邀獨立 Reviewer／Approver。都尚未被指派或核准；AI 工具不是被指定的人類審查者／簽章核准者。未安排第二人時不要設定無法履行、之後再繞過的自我 PR 核准流程。

申請簽章的候選範圍僅為自有軟體建置產物。Rust shell 含 upstream 靜態碼、PyInstaller Worker 含 bootloader、NSIS installer／uninstaller 含生成碼，均需明確核准 artifact configuration。其他 Python／crypto／llama／Microsoft DLL、第三方 EXE／PYD 及模型不列為自有簽章對象。保留上游簽章及原 Notice。

舊版 build_windows.py 的本機憑證選項限明確 LocalLLM.exe wrapper，禁止遞迴重簽 payload。本輪未執行該選項；這個修正不代表 Foundation 已接受 wrapper 或 Inno 簽章範圍。

每次候選須保留 commit、Actions Run、來源證明、鎖檔、SBOM、所有 PE 來源／hash／簽章狀態、版本及 installer／uninstaller 驗證。簽章只能在審查後對已上傳的對應 artifact 處理；不接受 PR、任意 URL 或未綁定來源的檔案作正式輸入。

撤銷／事故流程依 SECURITY.md：停止發行、保全證據、評估受影響來源／Token／產物，必要時向服務方請求撤銷。尚未建立服務權限或私人 Token；不會關閉系統安全防護。

## 維護者自行操作的帳號／規則步驟（未執行）

1. GitHub 個人 Settings → Password and authentication 啟用 2FA，採 TOTP／passkey／security key 等官方支援方式；保留離線 recovery codes，不提交到 Git。之後加入 SignPath 的每位成員也需 MFA，保存不含秘密的啟用證據。
2. 在 Repository Settings → Branches／Rules 對預定發行來源建立保護，限制 force push／刪除、要求適用狀態檢查；若有獨立審查者，再設定相應 PR 核准與最新變更重新審查。先核對單人方案與 Foundation 要求，不把管理員 bypass 當成已履行審查。
3. 之後正式接入時，建立受保護發行環境、指定已核准 Approver、設定來源／workflow／GitHub-hosted 限制；一般 PR／開發提交不得取得正式簽章權限。單人環境保護／self-review 設定須遵守獲准方案，不先假定可自批。
4. 保存角色、規則、MFA 及一次人工核准流程的非敏感證據，再更新同一 14 項資格表。本輪只提供步驟，沒有改帳號、分支或環境設定。

依據：[Foundation 條件](https://signpath.org/terms.html)、[SignPath approval configuration](https://docs.signpath.io/projects#approval-process)、[GitHub 2FA](https://docs.github.com/en/authentication/securing-your-account-with-two-factor-authentication-2fa/configuring-two-factor-authentication)、[分支保護](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)。
