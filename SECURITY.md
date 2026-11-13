# Security policy — draft reporting arrangements

0.7.0 Development 是未簽章開發版；尚未提供長期安全支援承諾。不要關閉 Defender、SmartScreen 或使用假憑證。校驗 SHA-256 與來源證明有助核對來源，不能保證軟體無漏洞。

私人漏洞回報管道與負責人尚未設定；GitHub Private vulnerability reporting 是否啟用也未驗證。請勿在公開 Issue 貼出漏洞利用細節、Token、模型憑證、遠端配對資料或私人日誌。可先以不含敏感內容的 Issue 請維護者提供私人管道。

發現真實憑證外洩時：停止公開候選發行，撤銷並輪替憑證，保存受限證據，評估存取記錄及受影響版本，再決定歷史清理與通知。不得只刪除目前檔案就宣稱已修復；歷史重寫須另行核准。

Agent 工具需核准；遠端／雲端任務應明確選擇目的地。第三方 Runtime 是可執行程式，模型與自訂節點也可能引入風險。固定來源與 SHA-256 不是上游安全背書。詳見 PRIVACY.md 與 docs/OPEN_SOURCE_BLOCKERS.md。
