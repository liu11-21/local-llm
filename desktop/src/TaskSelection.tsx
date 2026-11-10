import type { Info } from './api'
import { SelectModels } from './ui'

export function RuntimePicker({info, task, value, change, disabled, ariaLabel = '運算環境'}: {
  info?: Info; task: string; value: string; change: (runtime: string) => void; disabled?: boolean; ariaLabel?: string
}) {
  const options = info?.registry.runtimes.filter(runtime => runtime.id !== 'local' && runtime.tasks.includes(task)) ?? []
  return <select aria-label={ariaLabel} value={value} disabled={disabled} onChange={event => change(event.target.value)}>
    <option value="local">本機 CPU／GPU</option>
    {value !== 'local' && !options.some(runtime => runtime.id === value) && <option value={value}>端點需重新連線</option>}
    {options.map(runtime => <option key={runtime.id} value={runtime.id}>
      {runtime.kind === 'paired' ? '遠端電腦 · ' : runtime.kind === 'cloud' ? '雲端 · ' : ''}
      {runtime.label}{!runtime.ready ? ' · 尚未連線' : ''}
    </option>)}
  </select>
}

export function TaskModelPicker({info, runtime, model, change, disabled, ariaLabel = '模型'}: {
  info?: Info; runtime: string; model: string; change: (model: string) => void; disabled?: boolean; ariaLabel?: string
}) {
  const models = runtime === 'local' ? info?.models : info?.providers.find(item => item.id === runtime)?.models
  return <SelectModels ariaLabel={ariaLabel} models={models ?? []} value={model}
    registry={runtime === 'local' ? info?.registry.models : undefined} disabled={disabled} change={change}/>
}

export function PreparationNotice({title, children}: {title: string; children?: React.ReactNode}) {
  return <div className="task-preparation">
    <p className="task-preparation-title">{title}</p>
    {children}
  </div>
}
