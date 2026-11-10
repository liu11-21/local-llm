import { useEffect, useRef, useState } from 'react'
import { rpc, type Job, type Params, type Task } from './api'
import { Empty, Panel } from './ui'

const labels: Record<string, string> = {
  'remote-host-chat': '遠端裝置文字推理',
  chat: '文字聊天', download: '模型下載', team: 'AI 團隊', agent: 'AI 代理人',
  'team-workflow': 'AI 團隊角色流程',
  image: '圖片生成', video: '影片生成', music: '音樂生成', media: '創作',
  'engine-start': '啟動文字引擎', 'engine-stop': '停止文字引擎', 'engine-install': '安裝 llama.cpp',
  'comfy-install': '安裝 ComfyUI', 'comfy-start': '啟動 ComfyUI', 'comfy-stop': '停止 ComfyUI', 'update-download': '下載工作台更新',
  'media-install': '安裝創作模型',
}
const states = { queued:'排隊中', running:'進行中', paused:'等待核准', completed:'完成', failed:'失敗', cancelled:'已取消', interrupted:'已中斷' }
export const activeTask = (task: Task) => task.state === 'queued' || task.state === 'running' || task.state === 'paused'
export type Run = (action: string, data: Params, observe?: (job: Job) => void) => Promise<Job['result']>

export function TaskProgress({message, received, total, label = '下載進度'}: {
  message?: string; received?: number | null; total?: number | null; label?: string
}) {
  return <>
    {message && <small className="pre" role="status">{message}</small>}
    {!!total && <progress value={received ?? 0} max={total} aria-label={label}/>}
  </>
}

export function useTaskQueue(report: (error: unknown) => void, refreshed: () => Promise<void>) {
  const [tasks, setTasks] = useState<Task[]>([])
  const refreshing = useRef(0)
  const [loadError, setLoadError] = useState(false)
  async function refresh() {
    const request = ++refreshing.current
    try {
      const tasks = await rpc<Task[]>('task-list')
      if (request === refreshing.current) {setTasks(tasks); setLoadError(false)}
    } catch { if (request === refreshing.current) setLoadError(true) }
  }
  useEffect(() => {
    void refresh()
    const timer = setInterval(() => void refresh(), 1500)
    return () => clearInterval(timer)
  }, [])

  async function follow(id: string, observe?: (job: Job) => void) {
    void refresh()
    try {
      for (;;) {
        const job = await rpc<Job>('job', { id })
        observe?.(job)
        if (job.state === 'failed') throw new Error(job.message)
        if (job.state === 'completed') return job.result
        if (job.state === 'cancelled' || job.state === 'interrupted') return
        await new Promise(resolve => setTimeout(resolve, 280))
      }
    } finally {
      void refresh()
      void refreshed()
    }
  }

  const run: Run = async (action, data, observe) => {
    try {
      const { id } = await rpc<{id: string}>('run', { ...data, action })
      return await follow(id, observe)
    } catch (error) { report(error) }
  }
  async function cancel(id: string) {
    try { await rpc('cancel', {id}); await refresh() } catch (error) { report(error) }
  }
  async function retry(id: string) {
    try { await follow((await rpc<{id: string}>('task-retry', {id})).id) }
    catch (error) { report(error) }
  }
  return { tasks, loadError, run, cancel, retry }
}

export function TaskCenter({ tasks, cancel, retry, compact, loadError }: {
  tasks: Task[]; cancel?: (id: string) => void; retry?: (id: string) => void; compact?: boolean; loadError?: boolean
}) {
  const sorted = [...tasks.filter(activeTask), ...tasks.filter(task => !activeTask(task))]
  return <Panel title={compact ? '最近任務' : '任務與佇列'} description={compact ? undefined : '本機推理依序執行，下載可以同時進行。'}>
    {loadError && <div role="alert" className="empty">暫時無法讀取任務，系統會自動重試。</div>}
    {sorted.length === 0 && !loadError && <Empty>完成或啟動的任務會顯示在這裡。</Empty>}
    <div className="task-list">{(compact ? sorted.slice(0, 4) : sorted).map(task => <article className="list-row" key={task.id}>
      <span><b>{labels[task.kind] || labels[task.action] || task.action}{task.title && ` · ${task.title}`}</b>
        <small>{task.message}</small>
        {!compact && task.history_warning && <small>{task.history_warning}</small>}
        {!compact && <small>{new Date(task.created).toLocaleString()} · {task.runtime === 'local' || !task.runtime ? '本機' : '外部運算'}</small>}
        {activeTask(task) && <TaskProgress received={task.received} total={task.total}/>}
      </span>
      <span className={`tag task-${task.state}`}>{states[task.state] || task.state}</span>
      {!compact && cancel && activeTask(task) && <button className="button" onClick={() => cancel(task.id)}>取消</button>}
      {!compact && retry && task.retryable && <button className="button" onClick={() => retry(task.id)}>重試</button>}
    </article>)}</div>
  </Panel>
}
