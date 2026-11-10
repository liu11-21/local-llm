import type { Info, Job } from './api'
import { useState, type ReactNode } from 'react'
import { TaskProgress, type Run } from './taskQueue'
import { SelectModels } from './ui'

export function RuntimePicker({info, task, value, change, refresh, disabled, ariaLabel = '運算環境'}: {
  info?: Info; task: string; value: string; change: (runtime: string) => void; disabled?: boolean; ariaLabel?: string
  refresh?: (runtime:string) => Promise<void>
}) {
  const options = info?.registry.runtimes.filter(runtime => runtime.id !== 'local' && runtime.tasks.includes(task)) ?? []
  const [loading,setLoading] = useState(false)
  return <select aria-label={ariaLabel} value={value} disabled={disabled || loading} aria-busy={loading} onChange={event => {
    const runtime=event.target.value
    change(runtime)
    if (refresh) {
      setLoading(true)
      void refresh(runtime).finally(()=>setLoading(false))
    }
  }}>
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

export function PreparationNotice({title, children}: {title: string; children?: ReactNode}) {
  return <div className="task-preparation">
    <p className="task-preparation-title">{title}</p>
    {children}
  </div>
}

export function TextSetup({info, run, openModels, cancel}: {
  info?: Info; run: Run; openModels: () => void; cancel: (id:string) => void
}) {
  const [pending,setPending] = useState('')
  const [job,setJob] = useState<Job>()
  if (!info || (info.engine && info.models.length)) return null
  const model = info.recommended.find(item => !info.models.includes(item.name))
  async function start(action: string, data: Record<string,unknown>) {
    setPending(action);setJob(undefined)
    try {await run(action,data,setJob)} finally {setPending('')}
  }
  return <PreparationNotice title="準備本機模型">
    <p className="small">{!info.engine && !info.models.length ? '首次使用需要文字引擎和一個模型。' :
      !info.engine ? '已找到模型，還需要文字引擎。' : '文字引擎已就緒，請先選擇一個模型。'}</p>
    <div className="row section-note creation-actions">
      {!info.engine && <button className="button" disabled={!!pending} onClick={()=>void start('engine-install',{})}>
        {pending === 'engine-install' ? '正在安裝 · 見任務中心' : '安裝文字引擎'}</button>}
      {!info.models.length && model && <button className="button" disabled={!!pending}
        onClick={()=>void start('download',{url:model.url, workers:4})}>
        {pending === 'download' ? '正在下載 · 見任務中心' : '下載 ' + model.repo.split('/').at(-1)}</button>}
      <button className="button" onClick={openModels}>瀏覽模型</button>
      {pending && job && <button className="button" onClick={()=>cancel(job.id)}>取消準備</button>}
    </div>
    {pending && job && <TaskProgress message={job.message} received={job.received} total={job.total}/>}
  </PreparationNotice>
}
