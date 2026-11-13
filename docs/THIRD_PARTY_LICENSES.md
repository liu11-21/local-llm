# Third-party distribution review

基準為 0.7.0 Development。機器清單保存每個元件的來源、版本、原始宣告、SPDX 正規化、校驗、Notice 路徑及狀態。A＝庫內直接包含；B＝安裝包／可能編入的鎖檔依賴；C＝安裝後下載；D＝使用者匯入。B 是保守的完整圖，不代表每個 target／build 套件都出現在 Windows payload；PE 實際清單另由 CI 產生。

| 元件 | 分類 | 宣告／處理義務與限制 |
|---|---|---|
| 庫內 llama.cpp LICENSE | A | MIT；原文逐位元保留，不改成專案持有人 |
| React、Lucide、Tauri API、Vite、Tailwind、Markdown／highlight 及 npm 間接依賴 | B 或建置 | 逐項依 lock 宣告 MIT／ISC／BSD／Apache／MPL 等；保留原 Notice，不能以頂層 React 授權概括全部 |
| Tauri、serde、windows-sys 與 Cargo 全圖 | B 或建置／其他平台 | 選擇多授權的合法分支仍需記錄；MPL-2.0 元件若散布執行碼需提供相應 Covered Source 與取用方式。靜態連結不會讓 MPL 檔案變成 MIT |
| CPython 3.12.10、stdlib、libffi、SQLite、OpenSSL | B | Python-2.0 及各子元件條款；保留 CPython 授權歷史、crypto／libffi 等聲明。確切 PE／OpenSSL 版本及完整子元件對應待候選盤點 |
| PyInstaller 6.22.3 | 建置、bootloader B | GPL-2.0-or-later WITH Bootloader-exception；例外允許封裝應用依自有授權散布，不能據此把 PyInstaller 本身改成 MIT；修改 bootloader／額外再散布需另查。hooks 另有 Apache／GPL 範圍 |
| cryptography／cffi／pycparser | B | Apache-2.0 OR BSD-3-Clause／MIT-0／BSD-3-Clause；保留依確切版本取得的全文與著作權，不用舊版本猜測 |
| setuptools、pefile、packaging、jsonschema 等 | 建置／審查 | 不因建置使用就全部視為 App runtime；清單保留所有固定版本與各自聲明 |
| llama.cpp／Vulkan／LLVM OpenMP 引擎 | C；舊 Stable 為 B | MIT 與 Apache-2.0 WITH LLVM-exception 等；DLL 實際組成、驅動及下載包條款另查。不重簽 upstream DLL |
| OpenVINO／GenAI／tokenizers／telemetry／NumPy | C | 鎖定 wheel 與 SHA，收錄包內原始授權；多行／classifier 不能自動推論 SPDX。NumPy 含 BLAS 等多授權子元件，telemetry 隱私需另核對 |
| ComfyUI v0.44.0 portable | C | ComfyUI core GPL-3.0-only；提供相應來源／修改及散布義務。PyTorch／CUDA／FFmpeg／Python 與自訂節點各自授權，portable 不能用一個 GPL 宣告概括；未以 Comfy Desktop 的不同授權替代 |
| SD 1.5 | C | CreativeML OpenRAIL-M 等模型條款，含使用限制；不等同 OSI MIT，商用也受模型條款限制 |
| Wan 2.1／ACE-Step v1 | C | 目前固定 manifest 宣告 Apache-2.0，需核對轉換權重、文字編碼器、VAE、來源及完整 Notice，不能只看模型名稱就批准 |
| HF／GGUF／WebLLM 模型及匯入檔 | C、D | GGUF 是格式，不是授權；逐模型依原作、轉換、模型卡及商用限制審查。使用者匯入不表示權利移轉 |
| Microsoft VC／UCRT／API sets、WebView2 | B 或系統安裝 | 專有／系統元件依 Microsoft 再散布條款；需確認取得來源與 SignPath System Library 例外，不能套 MIT |
| Rust stdlib、NSIS stub／uninstaller、WebView2 bootstrapper | B | 編譯／安裝工具鏈嵌入內容需列來源與原始條款；專案未自動取得對上游程式單獨簽章的資格 |
| WebLLM 0.2.87 CDN | C（網頁） | 頂層 Apache-2.0；CDN JS／WASM／模型之完整 transitive graph 未鎖定，列 REVIEW REQUIRED |
| SPDX 2.3 schema | A、B（審查資料） | 原始 schema 依上游 CC-BY-3.0 保留授權與來源；SBOM metadata 的 CC0 不會重新授權 schema 或應用程式 |

MIT／BSD／ISC 通常允許商用、修改及再散布，但仍須保留聲明；Apache 還涉及 NOTICE／修改告知及專利條款。GPL、MPL、模型限制及 Microsoft 條款需依實際散布形式處理，不以此表取代全文審查。未發現宣告層面必然要求全部專案改 GPL 的證據，也不能據此宣稱所有再散布已合法。

下載元件與模型沒有在本輪刪除或重新授權。未完成的來源、全文、binary mapping、隱私與 SignPath 問題見 LICENSE_AUDIT／OPEN_SOURCE_BLOCKERS。原始文件位元組與 hash 由 license_audit.py validate 驗證。

依據：[PyInstaller 官方 COPYING](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt)、[Cargo license 欄位規則](https://doc.rust-lang.org/cargo/reference/manifest.html#the-license-and-license-file-fields)、[Microsoft 再散布說明](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files)。版本專屬證據以 SBOM 內原始內容優先。

## 現有 Windows payload 的限定映射

本輪僅沿用 [installed-pe-inventory.json](evidence/open-source/installed-pe-inventory.json) 的
72 PE，以及同一舊 Run 43409624156／來源 12869bc 的
[CI-NOTICE-INDEX.json](evidence/open-source/CI-NOTICE-INDEX.json) 與
[CI_NOTICES.md](evidence/open-source/CI_NOTICES.md)。不是新二進位或全 641 項盤點。
表中簽章候選身分不表示已獲 Foundation 批准；新建置須再次匹配實際 payload。

| 實際 PE 分組 | 數量 | 已有來源／原文對應 | 尚需處理 |
|---|---:|---|---|
| Rust shell／Worker／NSIS uninstaller | 3 | `localllm-desktop.exe`、`worker/LocalLLMWorker.exe`、`uninstall.exe`；第一方程式現為 MIT，嵌入上游仍另計 | 靜態 Rust 圖、PyInstaller bootloader、NSIS 生成碼的可簽範圍需 Foundation；Worker 原包 PE FileVersion 缺失，不冒稱已修 |
| CPython DLL／擴充模組 | 18 | CI index 的 CPython 3.12.10、Python-2.0；原包 Python-LICENSE 及 CI 原文保留 | 以該發行版綜合 LICENSE 對應嵌入子元件，不用根 MIT 取代 |
| Microsoft API sets／UCRT／VC Runtime | 45 | PE 路徑及既有簽章證據已定位 | 合法再散布來源／條款及 Foundation System Library 接受度；不是重簽對象 |
| cffi `_cffi_backend` | 1 | cffi 2.1.1 宣告 MIT-0；原文 hash `5ba24ddc57067f9249add644c3afc41a5d6dc37e23433ef759d95df370b0af63` | 保留 upstream 身分／原文，不因 NotSigned 就納入自己的簽章 |
| cryptography `_rust.pyd` | 1 | 50.0.2，Apache-2.0 OR BSD-3-Clause；CI 已有 LICENSE／LICENSE.APACHE／LICENSE.BSD | 內含元件與所選授權義務對應，不重簽 upstream PYD |
| OpenSSL DLL | 2 | libcrypto／libssl，既有 PE 版本 3.0.16；CI Apache-2.0 原文 | 確認該版本的完整 Notice／嵌入來源；不假設所有 crypto 只一份頂層授權 |
| libffi／SQLite DLL | 2 | `libffi-8.dll`／`sqlite3.dll`，既有 Python payload 證據 | 核對 CPython 綜合 LICENSE 對其版本的涵蓋，缺失則補對應上游原文；不推定已侵權 |

安裝器本體在 installed inventory 外，另由 BUILD.json／SHA256SUMS 識別；應與上述三個自身產物
分別設定可簽範圍，不做遞迴「簽所有 EXE／DLL／PYD」。WebView2 bootstrapper／系統安裝及
Tauri 靜態程式不會只靠這 72 個檔案全部涵蓋。MPL Covered Source 義務應針對實際編入的檔案
確認並提供，不把僅存在完整 lock graph 的其他平台依賴直接當作 Windows 缺陷。

所以目前沒有新增已證實迫使第一方放棄 MIT 的相容性問題；正式整包放行仍待上述實際映射、
適用授權／來源提供及 Logo 資產方案完成。這些待確認事項不是全部都需要 Foundation 判法律；
維護者可先完成可核對的 Notice／來源材料，再讓 Foundation 決定其自己的服務資格。
