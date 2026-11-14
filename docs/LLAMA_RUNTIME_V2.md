# llama.app Runtime integration — 0.8.0 Development

Architecture baseline: e2ba347 (0.7.0), inspected 2026-11-14. No uncommitted user changes existed.

| Area | Existing call chain and reuse |
|---|---|
| UI / native bridge | React ChatWorkspace / RuntimeWorkspace → api.rpc → Tauri Worker IPC; frontend never needs a Runtime API key |
| Worker / lifecycle | Desktop.perform → prepare → load_model → LocalEngine.start; EngineHealth handles readiness and stop |
| Scheduling | TaskManager → DeviceExecution admission / per-task copy → bound local engine; ResourceDemand reserves host / accelerator capacity |
| Agent / Team | desktop_agent + AgentRuntime + local_decision; TeamStore / team_dispatch depend on the same bound engine interface and retained tool grants |
| Benchmark | BenchmarkService → LlamaBenchmark → completion_events; saves raw usage / timings and evidence |
| Remote | RemoteClients / Host call existing scheduled worker actions; no new public llama listener is needed |
| Models / storage | catalog + downloads + registries; pinned HF revisions, resumed downloads and hashes; SQLite workspace.sqlite3 and protected upgrade snapshots retained |
| Other backends | OpenVINOAdapter / ComfyResources remain separate adapters; llama.app is text inference, not an image/video/music generator |

Legacy `llama-server.exe` takes server flags directly. New `llama.exe` is a dispatcher:
`version`, `serve ...`, `serve --help`, `serve --list-devices`; do not prepend the
same arguments blindly. Both use an OpenAI-compatible local API, but supported flags,
chat templates, thinking and cache behavior must be checked rather than assumed.
The official installer script was read, not executed. It selects CPU/Vulkan/CUDA/ROCm
artifacts and creates a WindowsApps alias; an alias is not evidence of the final process image.

Official sources: [installer](https://github.com/ggml-org/llama-install.sh),
[script](https://llama.app/install.ps1),
[server API](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

The maintainer-reported remote hardware baseline is build 12360 / commit 2d8a32502,
Vulkan RTX 5070 Ti, Qwen3-4B Q4_0, prompt 160.92 and generation 215.09 token/s.
Those are supplied observations, not tests rerun on this development host. CUDA,
all auxiliary signatures, SAC, GPU utilization/power and other physical hosts remain unverified.
