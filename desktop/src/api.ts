import { invoke, isTauri } from '@tauri-apps/api/core'

export type Params = Record<string, unknown>
export type Plan = { device: string | null; layers: number; total_layers: number; ram: number; vram: number; mapped_bytes: number }
export type Provider = { id: string; kind: string; label: string; host: string; port: number; models: string[]; connected: boolean }
export type Recommendation = { repo: string; name: string; description: string; size: number; url: string; fit: string }
export type Info = {
  models: string[]; model_folder: string; output_folder: string; engine: boolean;
  hardware: { cpu_threads: number | null; ram_total: number | null; ram_available: number | null; disk_available: number | null };
  active: [string, string, number, Plan] | null; devices: [string, number, boolean][]; recent_model: string | null;
  comfy_running: boolean; comfy_port: number | null; profiles: string[]; providers: Provider[];
  media: Record<string, [string, string, [string, string, string][]]>;
}
export type Chat = [string, string]
export type Message = { role: string; content: string }
export type Task = [string, string, string]
export type Job = {
  id: string; state: string; message: string; answer?: string; received?: number; total?: number; plan?: Plan;
  members?: string[]; steps?: string[];
  result?: { message?: string; answer?: string; folder?: string; name?: string; file?: string; plan?: Plan; drafts?: {name: string; text: string}[] };
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
