# Candidate and release process

目前僅準備 0.7.0 Development unsigned review candidate。不得因文件／小修正快速增加版本號。main、既有 Stable Release 及資料格式保持既有流程。

1. 從完整來源 SHA 建置；核對 Python／Node／Rust 版本及 npm、Cargo、Python 鎖檔。執行 Python、TypeScript／Vite、Chromium、Cargo／Tauri 與安裝升級測試。
2. 產生 SBOM、原始 Notices、來源權利清單；驗證 SPDX 官方 schema、檔案 SHA、版本及授權聲明。未知元件不能被掃描工具自動批准。
3. 在 GitHub-hosted Windows Runner 建置未簽章 NSIS；保存 BUILD.json、SHA256SUMS.txt、安裝後所有 PE 清單（含 uninstaller）、Notices 及 GitHub Sigstore provenance。BUILD.json 是自述資料，須搭配平台來源證明；這不是 Windows Authenticode。
4. 下載該次 artifact，核對完整 Commit／Actions Run／installer SHA-256／NotSigned。以 gh attestation verify <installer> --repo liu11-21/local-llm 驗證 GitHub 來源證明。程式可用、來源一致及權利合法為不同驗收項目。
5. 維護者完成權利、MFA、審查角色、相同形式公開發行、第三方義務及 SignPath 書面澄清後，另行核准正式 MIT 採用、申請及發行。此輪不建立 Release／Tag，不提出簽章請求。
6. 未來簽章只走獨立受保護流程，每次人工核准、對既有 unsigned artifact 驗證來源後處理，不重建替換 payload。簽後重新做 SHA／版本／Authenticode／安裝驗證。上游 DLL 保留原始簽章與授權，不以專案憑證批次重簽。

Actions artifact 需登入且只保留 14 天。申請前建議有持久、公開、相同 Tauri NSIS 形式的 unsigned Workspace 發行；官方條款未限定一定要 GitHub Release，應先書面確認 Actions artifact 是否足夠。舊 Tk／Inno v0.6.2 不能直接當作 Workspace 對應形式的證據。
