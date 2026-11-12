# Workspace 0.6.2 → 0.7.0 Development

這是同一 Tauri Workspace 的升級。舊 Tk Local LLM v0.6.2 是另一個產品：Inno AppId `{D03B7A5E-CC74-472E-B620-A978A505B6C1}`，安裝在 `%LOCALAPPDATA%/Programs/Local LLM`；Workspace 為 `com.local-llm.workspace`，安裝在 `%LOCALAPPDATA%/Local LLM Workspace`。不能混用安裝包或更新來源。模型／作品歷史上共用 LocalLLM 根目錄，不要同時啟動兩套程式修改它們。

0.7.0 仍使用 `%LOCALAPPDATA%/LocalLLM` 中原模型、作品、ComfyUI、OpenVINO 與下載暫存；資料庫採 `workspace.sqlite3`。首次發現舊 `desktop.sqlite3` 時，使用 SQLite backup API 取得包含 WAL 的一致快照，先檢查 integrity_check／foreign_key_check，保存在 backups，記錄 SHA-256，再採用副本。原 desktop.sqlite3 保留。舊 Workspace 0.6.2 沒有新版相容性防護，因此藉不同檔名隔離，不能假設舊 binary 會遵守新版標記。

升級前後檢查完整性，檢查實體路徑與磁碟餘量；主 Worker 的 OS 鎖及額外 migration 鎖避免競爭。未完成的聊天／Agent／Team／遠端／Benchmark 按原規則標中斷，不自動重新執行。新資料庫存最低讀取程式版本，遇到未支援 schema 或較新 minimum_reader 就拒絕寫入。

若 Migration 失敗，已驗證備份不被覆蓋；部分資料庫及 WAL／SHM 移至獨立 failed-upgrade 目錄，再以快照恢復工作副本。原始舊資料保持不變。啟動失敗會回傳恢復指引，非靜默建立空資料庫。

## 使用者升級

1. 關閉 Workspace、舊 Local LLM 及同資料夾驗收工具。另行備份整個 LocalLLM 目錄，可涵蓋模型／作品原檔；內建 SQLite 備份不包含大型媒體及模型檔。
2. 核對 Actions 的來源 SHA、BUILD.json、SHA256SUMS.txt，執行 0.7.0 Workspace Setup。不需要先卸載 0.6.2 Workspace。
3. 首次開啟後，於設定查看版本、Worker、建置 SHA；storage-status IPC 可讀取移轉狀態與備份位置。檢查原對話、Agent／Team、來源、Benchmark、配對、作品與設定。
4. 備份與配對金鑰可能包含使用者資料；DPAPI 僅可由原 Windows 使用者解密，不要直接公開整個資料夾。

## 恢復與降級

先關閉所有相關程序，複製整個資料目錄到另一個安全位置，保留原檔、backups、failed-upgrade、WAL／SHM。不要刪除唯一資料或在程序運作時替換資料庫。

以獨立工具查詢選定備份的 `PRAGMA integrity_check`／`foreign_key_check` 與備份 JSON SHA-256，確認來源及版本。若恢復到 0.7.0：先將目前 workspace.sqlite3 及其 WAL／SHM 另存，不覆蓋；把已驗證快照複製成 workspace.sqlite3，再啟動相容版本，使它完成必要 Migration。原 desktop.sqlite3 仍保留供對照。

若回到 0.6.2 Workspace，使用升級前的 desktop.sqlite3 或該版本的已驗證備份。**0.7.0 之後的新聊天／作品中繼資料不會自動回填舊資料庫，也不保證能降級。** 原始作品檔保留不等於舊版能理解全部新版參數。從較新程式降到 0.7.0 時同樣必須先選相容備份，不可略過 minimum_reader。

## 驗收

單元測試涵蓋舊 schema、WAL、損毀、空間不足、較新 schema／reader、注入 Migration 失敗與重試。原始 0.6.2 Worker 產生資料庫後，以填入的歷史、Agent／Team、模型來源、權重校驗、Benchmark、DPAPI 配對資料、作品參數及設定做 18 表指紋比對。

Windows CI 從固定 `4354605` 原始碼重新建立真正 Workspace 0.6.2 NSIS，再同路徑安裝 0.7.0，檢查捷徑、WebView／封裝 Worker、三次程序冷啟動、資料及備份；解除安裝後重查資料。此流程不使用舊 Tk 安裝包，也不建立 Release。最後實際 PASS 與來源／雜湊見 TEST_REPORT；工具與 fixture 的成功不代表真實模型推理通過。
