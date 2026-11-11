# GPU／NPU 支援範圍

Batch 4E＋NPU 本輪交付 E1、E2，程式版本 0.6.2。NPU 裝置偵測、Provider 列舉與模型實際執行各自有不同的證據。NPU Engine Adapter、模型相容性執行、異質派送和推理 Benchmark 屬 E3 後續工作。

| 狀態 | 能力 | 實際限制 |
|---|---|---|
| 已支援 | Windows DXGI GPU 清單、PDH 使用率與專用／共享記憶體，CIM 驅動及裝置狀態 | Intel Iris Xe 實測。驅動未提供的計數器顯示未知。GPU 資料按 LUID 配對，多 GPU 分別顯示 |
| 已實作待驗證 | NVIDIA／AMD／其他 Intel GPU 的同一套 Windows 監控 | NEEDS GPU，尚無各廠牌實體驗收 |
| 已實作待驗證 | Intel AI Boost／NPU、AMD IPU／NPU、Qualcomm Hexagon／NPU 的 Windows PnP 識別 | NEEDS NPU。單元測試採受控裝置資料，CPU 型號不參與推測。泛用 ComputeAccelerator 保留候選身分 |
| 已支援 | 可選 OpenVINO／ONNX Runtime 的獨立程序能力查詢 | 只檢查目前工作程序環境已安裝的套件，記錄版本、裝置和 Provider。此電腦兩套均未安裝 |
| 僅完成契約 | 硬體／Provider 版本、來源、未知值、時間與格式候選欄位 | 此契約可供 E3 使用，尚未新增 NPU Engine Registry 執行 Adapter |
| 實驗性，未實作 | 同模型 HETERO、跨 CPU／GPU／NPU 算子分配與效能比較 | NOT RUN。尚未開放選取或排程 |
| 不支援 | 直接把任意 GGUF 交給 NPU 執行、將 CPU fallback 記為 NPU 驗證、保證所有裝置都有 NPU 使用率／獨立記憶體 | 現有 GGUF 走原有 llama.cpp，創作走原有 ComfyUI |

硬體紀錄含 `schema`、清單時間、取樣時間、每裝置身分、廠牌、驅動、裝置錯誤碼、量測數值、來源及支援狀態。`verified_inference` 在本輪探測維持 false。NPU 使用率與專用記憶體目前標記未支援，UI 會顯示相應說明。CIM 查詢失敗時 NPU 是否存在為未知。

GPU 使用率以每張 GPU 最忙的引擎顯示，同一引擎各程序的計數器先相加。專用顯存總量取自 DXGI，已用量取自對應的 Windows GPU Adapter Memory 計數器。共享記憶體另列，不加進專用顯存。無法配對或互相矛盾的數值保留未知。計數器和清單的來源分別見 Windows 官方介面。 [PDH 陣列](https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetformattedcounterarrayw) · [語系中立計數器](https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhaddenglishcounterw) · [DXGI 記憶體欄位](https://learn.microsoft.com/en-us/windows/win32/api/dxgi/ns-dxgi-dxgi_adapter_desc1) · [PnP 裝置](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-pnpentity)

Provider 查詢可在運算環境的「GPU 與 NPU → 進階」手動執行。OpenVINO 用 `Core.available_devices`，ONNX Runtime 用 `get_available_providers()`。初始化程序最長 25 秒，錯誤採固定診斷訊息。這兩個 API 的列舉結果尚未證明模型算子分配或 NPU 推理。OpenVINO IR、ONNX 是後端的候選格式，量化及模型支援要以 E3 的相容性測試為準。 [OpenVINO NPU](https://docs.openvino.ai/2025/openvino-workflow/running-inference/inference-devices-and-modes/npu-device.html) · [ONNX Runtime Provider](https://onnxruntime.ai/docs/execution-providers/)

後續 E3 的廠牌適配候選為 Intel OpenVINO、AMD Ryzen AI 的 Vitis AI EP，以及 Qualcomm QNN EP。需要分別準備相容模型、版本和驅動，測試算子分配、CPU fallback 和輸出，才可加入實際派送與推薦。 [AMD 官方模型執行](https://ryzenai.docs.amd.com/en/latest/modelrun.html) · [QNN 官方契約](https://onnxruntime.ai/docs/execution-providers/QNN-ExecutionProvider.html)

在專案根目錄執行 `python hardware_acceptance.py --providers --output hardware-evidence.json` 可保存真實裝置清單、三次取樣、取樣耗時與既有 Provider。檔案只驗收偵測和監控，`npu_inference` 明確為 `NOT RUN`。本輪 Intel Iris Xe 三次取樣耗時中位數 2.20 ms，取樣不包含背景裝置清單查詢。WMI／CIM 在背景執行，最多 20 秒，每次清單更新至少間隔 60 秒，關閉工作台可取消查詢。 [測試紀錄](TEST_REPORT.md)
