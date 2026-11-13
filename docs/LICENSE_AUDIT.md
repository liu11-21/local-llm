# License and ownership audit — 2026-11-13

結論：**尚不具備正式 MIT 採用條件**。維護者已指定候選署名「劉仲軒」，並明確表示其餘權利待確認。提交作者、AI 產碼、公開庫或沒有 LICENSE 都不能證明可重新授權。根 LICENSE 僅記錄狀態；候選全文位於 legal/LICENSE-MIT.candidate.txt，package.json／Cargo.toml 未宣告 MIT。

起始來源 adbe209a50286eb1ff1321c770dd8927c45d3e1d，dev/desktop-workspace，0.7.0 Development；當時 337 tracked files、119 reachable commits，提交名稱為 Codex／liu11-21。這只是歷史觀察，不把提交名稱當著作權人。最終工具與新文件納入後的來源快照見 evidence/open-source/source-ownership.json，其 head 是審查範圍，不冒充後續文件提交。

逐檔記錄：hash、分類、觀察到的提交作者、首次提交、來源、宣告、可否 MIT、是否保留原授權、是否需同意及未知點。Python、React／TS、Rust、網頁、建置、Logo／圖示／截圖／媒體 fixture 都列入。現有 third_party/llama.cpp-b11810-LICENSE 保持原文；其餘檔案在缺少證明時一律不做權利推定。尚未對所有歷史程式做外部來源相似度比對；Logo 與媒體的生成／引用紀錄也需維護者提供。

依賴掃描以 npm／Cargo 鎖檔全部項目、Python 封裝與審查工具固定版本、可選 OpenVINO wheel、Runtime／模型 manifest 為範圍。docs/sbom/DEPENDENCY_LICENSES.json 保留原始 label；SPDX 接受清單內名稱，Cargo 舊 slash 表記依官方慣例正規化為 OR；無法正規化時 NOASSERTION，不生成虛假的自訂授權全文。licenseConcluded 均不代替法律決定。

原始 license 文本以 SHA 命名去重並索引。crate 封裝以 Cargo.lock checksum 驗證，僅提取授權文件；沒有 LICENSE 的上游封裝仍列 REVIEW REQUIRED，不擅自拿泛用 MIT 範本充當原著作權 Notice。完整鎖檔包含其他平台／建置依賴，實際 Windows 編入範圍仍需 graph／linker review；CI 同時採集來源目錄與已安裝 PE。

本機快照包含 641 個元件紀錄、324 份去重原始 Notice（199 npm、404 Cargo、10 Python 封裝 pin、6 審查工具 pin，另含 Runtime／模型／schema）。目前缺原始 Notice 的 Cargo 封裝包括 libappindicator-sys 0.9.0、r-efi 5.3.0／6.0.0、selectors 0.38.0、winapi-i686-pc-windows-gnu／winapi-x86_64-pc-windows-gnu 0.4.0。缺口有其他平台／工具鏈範圍，不能全部直接當作 Windows payload，也不能忽略。CI 的 resolved source 會另外採集。

9 個 raw 宣告為 NOASSERTION，SPDX 另有模型限制及 Microsoft 自訂條款不做臆測，因此 SPDX NOASSERTION 數可能更多。包含 pyinstaller-hooks-contrib 多段授權、OpenVINO／NumPy wheel 多行文字、embedded Python 及概括性 runtime／模型項目。原文已收錄時仍不能隨意改寫成單一 SPDX MIT；完整原文、來源提供及適用性須再審查。

必須人工處理：MPL 對應來源提供；PyInstaller 例外適用範圍；Python／OpenSSL／libffi／SQLite 及工具鏈嵌入元件；Microsoft 再散布來源／條款；Comfy portable 的 transitive CUDA／Torch／FFmpeg；OpenVINO wheel 子元件；各模型權重及轉換條款；網頁 CDN 完整依賴。這些未知不等於已發現違法，也不等於批准散布。

秘密審查使用 source_audit.py，僅輸出位置／類型／hash fingerprint，不輸出值、不測試認證。起始歷史 917 個文字 blob 沒有命中已設定的 Token／provider-key／private-key 規則；兩個 user-path 命中位於歷史 evidence/v070/upgrade-worker-local.json。這是個人路徑 metadata，沒有確認為憑證事件。二進位、截圖、模型檔、自由格式對話及未匹配憑證仍需人工檢查；不能把模式未命中寫成「無秘密」。未改寫 Git 歷史。

MIT 採用前需確認各作者／素材權利，處理第三方引用與 Notice／相容性後，以獨立可審查提交將候選正文正式放入 LICENSE，同步 README／metadata／SBOM。確認署名不等於批准這一步。本輪無正式授權變更。

來源：[OSI MIT 官方模板](https://opensource.org/license/mit)。第三方版本證據及義務見 THIRD_PARTY_LICENSES.md；其原始文件不因本候選而改變。
