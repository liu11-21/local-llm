# CI notice evidence — Run 43409624156

來源 12869bc64cedea0a7a8d562da30384223ed2e531；[成功 Run](https://github.com/liu11-21/local-llm/actions/runs/43409624156)、[來源證明](https://github.com/liu11-21/local-llm/attestations/67126895)。本目錄保留實際 CI-SBOM.spdx.json、CI-NOTICE-INDEX.json、BUILD／hash、72 PE 清單、NSIS smoke 與原始 Sigstore bundle。沒有保存私人認證或下載用 signed URL。

CI-NOTICE-INDEX 中 notice_files.file 是 artifact 的 notices/ 目錄相對路徑。原始檔以 SHA-256 basename 保存：優先查 docs/sbom/license-texts/，CI 新增的一份放在本目錄 ci-extra-license-texts/。兩處合計 325 份未改寫原文，可依 index 重建並以 license_audit.py validate 驗證；不把 CI 目錄的 payload-relative path 誤當本目錄相對路徑。ci-extra-license-texts 是第三方原始聲明，維持各自授權，不能套專案 MIT 候選。

CI 共有 641 個元件紀錄，涵蓋 199 npm、404 Cargo、10 Python 封裝 pin、6 審查工具 pin 及其他 Runtime／模型。74 個紀錄未取到獨立原始 Notice，12 個 raw 宣告為 NOASSERTION；包含未安裝的可選平台／Runtime、抽象模型／工具鏈項目，不能解讀成全部 74 都在 Windows payload，也不能把這些缺口當 PASS。原始碼本機快照另外保存已校驗 OpenVINO wheel 證據，因此與乾淨 CI 的 unknown／Notice 數量不同。

安裝後 72 PE 中 67 Valid、5 NotSigned；未簽者為 Rust shell、NSIS uninstaller、Python Worker、cffi backend 與 cryptography Rust binding。67 個有效簽章是保留的上游簽章，未以本專案身分重簽。installer 也為 NotSigned。Python DLL 3.12.10、OpenSSL DLL 3.0.16；shell／uninstaller 版本 0.7.0，Worker PE 無 FileVersion，其嵌入 build identity／IPC 版本驗證為 0.7.0 Development。若日後將 Worker 納入簽章，需要補齊或取得 metadata 規則確認。

GitHub CLI 2.104.0 已從 API 獨立驗證 installer 的 SLSA provenance v1，強制 repo、signer workflow、來源 digest／ref 及拒絕 self-hosted Runner。詳 candidate-verification.json。這只證明此 artifact 對應平台建置來源，不證明權利合法、程式安全或 SignPath 資格，也不代表 Windows Authenticode。

可重建驗證：把 CI-NOTICE-INDEX.json 另存為暫存目錄 DEPENDENCY_LICENSES.json、CI-SBOM.spdx.json 另存 workspace.spdx.json、複製 docs/sbom/spdx-schema.json，再依 SHA basename 從上述兩個原文目錄複製成 license-texts/，執行 python license_audit.py validate --output <暫存目錄>。來源證明驗證命令及 artifact／installer hashes 在 candidate-verification.json。

補充 literal-credential-screen.json 使用與 source_audit.py 相同 Git cat-file walk、報告內的 regex，檢查 1,292 個 reachable 文字 blob 的固定 credential-field 指派，零候選。它沒有進行實際認證、圖片語意或任意命名的秘密偵測；不能取代人工隱私複核。
