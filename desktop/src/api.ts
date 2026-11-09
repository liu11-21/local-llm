import { invoke, isTauri } from '@tauri-apps/api/core'

export type Params = Record<string, unknown>
export type Plan = { device: string | null; layers: number; total_layers: number; ram: number; vram: number; mapped_bytes: number }
export type Provider = { id: string; kind: string; label: string; host: string; port: number; models: string[]; connected: boolean }
export type Recommendation = { repo: string; name: string; description: string; size: number; url: string; fit: string }
export type WorkflowParameter = { key: string; label: string; type: 'integer' | 'text'; default: number | string | null; min: number; max: number; step: number }
export type MediaKind = 'image' | 'video' | 'music'
export type Workflow = { id: string; label: string; kind: MediaKind; models: string[]; output: string; parameters: WorkflowParameter[] }
export type Work = { name: string; kind: MediaKind; created: string; bytes: number; model?: string; workflow?: string; prompt?: string; lyrics?: string; options?: Params }
export type Registry = {
  models: { id: string; label: string; bytes: number; quantization: string | null; format: string; publisher?: string; ram: number }[];
  engines: { id: string; label: string; version: string; installed: boolean; running: boolean }[];
  runtimes: { id: string; label: string; kind: string; ready: boolean; tasks: string[] }[];
  workflows: Workflow[];
}
export type Info = {
  models: string[]; model_folder: string; output_folder: string; engine: boolean;
  hardware: { cpu_threads: number | null; ram_total: number | null; ram_available: number | null; disk_available: number | null };
  active: [string, string, number, Plan] | null; devices: [string, number, boolean][]; recent_model: string | null;
  comfy_running: boolean; comfy_port: number | null; profiles: string[]; comfy_profiles_installed: string[]; providers: Provider[];
  registry: Registry; recommended: Recommendation[];
}
export type Chat = [string, string]
export type Message = { role: string; content: string }
export type TaskState = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted'
export type Task = {
  id: string; action: string; kind: string; title?: string; state: TaskState; message: string;
  created: string; started?: string | null; finished?: string | null; runtime?: string;
  lane?: string; error?: string | null; received?: number | null; total?: number | null; retryable?: boolean;
  history_warning?: string | null;
}
export type Usage = { input: number; context: number; max_output: number; omitted_turns: number }
export type Job = {
  id: string; state: string; message: string; answer?: string; received?: number; total?: number; plan?: Plan;
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
