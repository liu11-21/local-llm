import type { ReactNode } from 'react'
import { Layers3 } from 'lucide-react'
import type { Plan, Registry } from './api'

export const gb = (bytes?: number | null) => bytes == null ? '—' : `${(bytes / 2 ** 30).toFixed(bytes < 2 ** 30 ? 2 : 1)} GB`

export function Panel({ title, children, description }: { title?: string; children: ReactNode; description?: string }) {
  return <section className="panel">{title && <h2>{title}</h2>}{description && <p className="muted section-note">{description}</p>}{children}</section>
}
export function Empty({ children }: { children: ReactNode }) { return <div className="empty">{children}</div> }

export function Estimate({ plan }: { plan: Plan }) {
  return <div className="estimate"><Layers3 size={17}/><div><b>載入預估</b>
    <p>RAM {gb(plan.ram)} · VRAM {gb(plan.vram)} · 磁碟映射 {gb(plan.mapped_bytes)}</p>
    <p>{plan.device || 'CPU'} · GPU 分層 {plan.layers}/{plan.total_layers}。實際用量會隨上下文與驅動程式變動。</p>
  </div></div>
}

export function SelectModels({ models, value, change, registry, disabled }: {
  models: string[]; value: string; change: (model: string) => void; registry?: Registry['models']; disabled?: boolean
}) {
  return <select value={value} disabled={disabled} onChange={e => change(e.target.value)}>
    <option value="">選擇模型</option>
    {models.map(id => {
      const record = registry?.find(model => model.id === id)
      return <option key={id} value={id} title={id}>{record ? [record.label, record.quantization].filter(Boolean).join(' · ') : id}</option>
    })}
  </select>
}
