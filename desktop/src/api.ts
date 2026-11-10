import { invoke, isTauri } from '@tauri-apps/api/core'

export type Params = Record<string, unknown>
export type Plan = { device: string | null; layers: number; total_layers: number; ram: number; vram: number; mapped_bytes: number }
export type RuntimeCapability = {
  schema: number; id: string; label: string; kind: string; health: string; connected: boolean | null; error?: string;
  checked_at: number; cost: string; tasks: string[]; formats: string[]; models: string[];
  resources: Record<string, {value: number | string[] | null; source: string}>;
}
export type Provider = { id: string; kind: string; label: string; host: string; port: number; models: string[]; connected: boolean;
  capability?: RuntimeCapability }
export type EngineStatus = { state: 'not_installed' | 'installed' | 'starting' | 'ready' | 'busy' | 'stopping' | 'stopped' | 'unhealthy' | 'failed';
  code?: string | null; hint?: string | null; checked_at?: string }
export type EngineHealth = { llama: EngineStatus; comfyui: EngineStatus }
export type Recommendation = { repo: string; name: string; description: string; size: number; url: string; fit: string }
export type WorkflowParameter = { key: string; label: string; type: 'integer' | 'text'; default: number | string | null; min: number; max: number; step: number; basic?: boolean }
export type MediaKind = 'image' | 'video' | 'music'
export type Workflow = { id: string; label: string; kind: MediaKind; models: string[]; output: string; parameters: WorkflowParameter[] }
export type MediaWeight = { filename: string; path: string; url: string; bytes: number; sha256: string }
export type MediaModel = { id: string; label: string; kind: MediaKind; publisher: string; version: string;
  source: string; revision: string; license: string; terms: string; weights: MediaWeight[]; ram: number | null; vram: number | null }
export type MediaInstallPlan = { model: MediaModel; target: string; profile: string; installed: boolean;
  files: (MediaWeight & {status: 'missing' | 'detected' | 'verified' | 'conflict' | 'unavailable'})[];
  free: number; needed: number; conflict: boolean; unavailable: boolean; verified: boolean }
export type WorkDimensions = { width?: number; height?: number; duration?: number }
export type Work = { name: string; kind: MediaKind; created: string; bytes: number; model?: string; workflow?: string; prompt?: string;
  lyrics?: string; options?: Params; schema?: number; runtime?: string; status?: string; dimensions?: WorkDimensions;
  source?: {engine: string; job: string; original: string} }
export type Registry = {
  models: { id: string; label: string; bytes: number; quantization: string | null; format: string; publisher?: string; ram: number;
    verification: 'verified' | 'known' | 'imported' | 'unknown'; repository?: string; version?: string; source?: string;
    sha256?: string; license?: string; downloaded?: string }[];
  engines: { id: string; label: string; version: string; installed: boolean; running: boolean }[];
  runtimes: { id: string; label: string; kind: string; ready: boolean; tasks: string[] }[];
  workflows: Workflow[];
  media_models?: MediaModel[];
}
export type Info = {
  models: string[]; model_folder: string; output_folder: string; engine: boolean;
  hardware: { cpu_threads: number | null; ram_total: number | null; ram_available: number | null; disk_available: number | null };
  active: [string, string, number, Plan] | null; devices: [string, number, boolean][]; recent_model: string | null;
  comfy_running: boolean; comfy_port: number | null; profiles: string[]; comfy_profiles_installed: string[]; providers: Provider[];
  registry: Registry; recommended: Recommendation[];
  recoverable_downloads: {name: string; url: string; received: number; total: number}[];
}
export type Chat = [string, string]
export type Message = { role: string; content: string; runtime?: string; model?: string; provider?: string }
export type TaskState = 'queued' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled' | 'interrupted'
export type Task = {
  id: string; action: string; kind: string; title?: string; state: TaskState; message: string;
  created: string; started?: string | null; finished?: string | null; runtime?: string;
  lane?: string; error?: string | null; received?: number | null; total?: number | null; retryable?: boolean;
  history_warning?: string | null;
  media_target?: string;
}
export type Usage = { input: number; context: number; max_output: number; omitted_turns: number }
export type Job = {
  id: string; state: string; message: string; answer?: string; received?: number; total?: number; plan?: Plan; plan_id?: string;
  team_run_id?: string;
  members?: string[]; steps?: string[]; usage?: Usage;
  result?: { message?: string; answer?: string; folder?: string; name?: string; file?: string; plan?: Plan; usage?: Usage; drafts?: {name: string; text: string}[] };
}
type Reply<T> = { ok: true; value: T } | { ok: false; error: string }

export async function rpc<T>(op: string, data: Params = {}): Promise<T> {
  let reply: Reply<T>
  if (isTauri()) {
    reply = await invoke('workspace', { op, data })
  } else if (import.meta.env.MODE === 'preview-worker') {
    const response = await fetch('/__desktop_dev_rpc', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ op, data })
    })
    if (!response.ok) throw new Error('無法連線至本機開發工作程序。')
    reply = await response.json()
  } else {
    throw new Error('請使用桌面程式開啟工作台。')
  }
  if (!reply.ok) throw new Error(reply.error)
  return reply.value
}
