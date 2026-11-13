# License and ownership audit — 2026-11-13

最新結論：**現有證據未識別出阻止第一方程式碼採 MIT 的具體衝突，維護者已於 2026-11-13 另外明確批准 A1–A4，第一方 MIT 已正式採用。** 維護者已補充：「維護者主導需求與產品架構，主要透過 Codex／AI 輔助產生及修改程式碼。」人類主導需求、選擇及整合是已記錄的來源事實，不是每行程式均具完整人類著作權的證明。缺乏逐行人類創作證明，也不直接構成侵權證據。A1–A4 的合約主體／已知輸入／範圍及採用已取得維護者確認；剩餘發行 gate 為 Logo 等排除資產、第三方義務及 SignPath，見 [來源分類](MAINTAINER_PROVENANCE.md) 與 [最終清單](MIT_FINAL_APPROVAL_CHECKLIST.md)。

根 [LICENSE](../LICENSE) 現為標準 MIT，原狀態完整保留於 [LICENSE_STATUS.md](../LICENSE_STATUS.md)。
package／Cargo 及新建置的 Notices 已同步；現行 SBOM 僅修改第一方宣告／採用 overlay。
第三方 641 項與原 Notice 保留，歷史 CI evidence 不改；以下數據是前輪證據，不冒充新掃描。
本輪批准來源基準 d74bb27，既有來源審查基準 84a3af4。範圍見 [LICENSE_SCOPE.md](../LICENSE_SCOPE.md)。

起始來源 adbe209a50286eb1ff1321c770dd8927c45d3e1d，dev/desktop-workspace，0.7.0 Development；當時 337 tracked files、119 reachable commits，提交名稱為 Codex／liu11-21。這只是歷史觀察，不把提交名稱當著作權人。最終工具與新文件納入後的來源快照見 evidence/open-source/source-ownership.json，其 head 是審查範圍，不冒充後續文件提交。

逐檔記錄保留原 head、hash、作者名稱與首次 Commit；人工 review_overlay 更新來源及權利決策分類，不冒充新掃描。第一方程式標為維護者主導 AI 輔助候選；vendor／schema／授權原文保留 upstream；Logo 是 AI 來源陳述、服務及輸入待確認；截圖另處理，合成 fixture 有 generator 可佐證。既有 inventory 只有 Codex／liu11-21 兩個提交名稱，沒有證據把它們認定為兩個獨立人類權利人。現有來源／copyright／SPDX／複製標示的有限檢查，未見明確無權複製或不相容片段；沒有進行全面相似度比對，不能承諾完全不存在第三方內容。

依賴掃描以 npm／Cargo 鎖檔全部項目、Python 封裝與審查工具固定版本、可選 OpenVINO wheel、Runtime／模型 manifest 為範圍。docs/sbom/DEPENDENCY_LICENSES.json 保留原始 label；SPDX 接受清單內名稱，Cargo 舊 slash 表記依官方慣例正規化為 OR；無法正規化時 NOASSERTION，不生成虛假的自訂授權全文。licenseConcluded 均不代替法律決定。

原始 license 文本以 SHA 命名去重並索引。crate 封裝以 Cargo.lock checksum 驗證，僅提取授權文件；沒有 LICENSE 的上游封裝仍列 REVIEW REQUIRED，不擅自拿泛用 MIT 範本充當原著作權 Notice。完整鎖檔包含其他平台／建置依賴，實際 Windows 編入範圍仍需 graph／linker review；CI 同時採集來源目錄與已安裝 PE。

本機快照包含 641 個元件紀錄、324 份去重原始 Notice（199 npm、404 Cargo、10 Python 封裝 pin、6 審查工具 pin，另含 Runtime／模型／schema）。目前缺原始 Notice 的 Cargo 封裝包括 libappindicator-sys 0.9.0、r-efi 5.3.0／6.0.0、selectors 0.38.0、winapi-i686-pc-windows-gnu／winapi-x86_64-pc-windows-gnu 0.4.0。缺口有其他平台／工具鏈範圍，不能全部直接當作 Windows payload，也不能忽略。CI 的 resolved source 會另外採集。

9 個 raw 宣告為 NOASSERTION，SPDX 另有模型限制及 Microsoft 自訂條款不做臆測，因此 SPDX NOASSERTION 數可能更多。包含 pyinstaller-hooks-contrib 多段授權、OpenVINO／NumPy wheel 多行文字、embedded Python 及概括性 runtime／模型項目。原文已收錄時仍不能隨意改寫成單一 SPDX MIT；完整原文、來源提供及適用性須再審查。

必須人工處理：MPL 對應來源提供；PyInstaller 例外適用範圍；Python／OpenSSL／libffi／SQLite 及工具鏈嵌入元件；Microsoft 再散布來源／條款；Comfy portable 的 transitive CUDA／Torch／FFmpeg；OpenVINO wheel 子元件；各模型權重及轉換條款；網頁 CDN 完整依賴。這些未知不等於已發現違法，也不等於批准散布。

Agent 實際檢查：tool_registry.py 的 definition 拒絕非 trusted、非 read-only、network 或 modifies_state 工具；內建只有 hardware／models／engines／tasks／work 五種查詢，沒有任意 shell 或檔案寫入工具。agent_plans.py 保存核准及事件，重啟會中斷舊執行；desktop_agent.py 綁定工具契約及目的地同意。Runtime 安裝會執行另外下載的第三方程式，不能因 Agent 的唯讀 allowlist 就把下載器與所有第三方程式安全視為 PASS。尚無發現用於漏洞利用或繞過執行環境防護的內建 Agent 工具；這不是 Foundation 的資格認定。

秘密審查使用 source_audit.py，僅輸出位置／類型／hash fingerprint，不輸出值、不測試認證。起始歷史 917 個文字 blob 沒有命中已設定的 Token／provider-key／private-key 規則；兩個 user-path 命中位於歷史 evidence/v070/upgrade-worker-local.json。這是個人路徑 metadata，沒有確認為憑證事件。二進位、截圖、模型檔、自由格式對話及未匹配憑證仍需人工檢查；不能把模式未命中寫成「無秘密」。未改寫 Git 歷史。

第一方 MIT 決策與二進位發行放行分開：程式碼採用只涵蓋維護者可授權範圍；Logo、模型、Runtime、第三方來源保留獨立規則。維護者已確認所知事實並明確批准範圍與正式採用，故本次另行替換根 LICENSE、同步 metadata。第三方 Notice／Covered Source／Microsoft 分發等仍是對應發行的放行條件，不能因程式採 MIT 就略過，也不能因第三方未結案就一概宣稱第一方侵權。

來源：[OSI MIT 官方模板](https://opensource.org/license/mit)。第三方版本證據及義務見 THIRD_PARTY_LICENSES.md；其原始文件不因本候選而改變。
