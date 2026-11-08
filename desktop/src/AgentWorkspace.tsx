import { useEffect, useState } from 'react'
import { rpc, type Job, type Params } from './api'

type AgentPlan = { id: string; role: string; model: string; prompt: string; steps: string[] }
type AgentReport = [string, string, string, string, string, string, string]
type ExecutionRecord = { steps: string[]; evidence?: Record<string, unknown> }

function executionRecord(raw: string): ExecutionRecord {
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? { steps: parsed } : parsed
  } catch { return { steps: [] } }
}

export function AgentWorkspace({ models, engine, busy, job, run, report }: {
  models: string[]
  engine: boolean
  busy: boolean
  job?: Job
  run: (action: string, payload: Params) => Promise<Job['result']>
  report: (error: unknown) => void
}) {
  const [role, setRole] = useState('general')
  const [model, setModel] = useState('')
  const [prompt, setPrompt] = useState('')
  const [tools, setTools] = useState<string[]>([])
  const [plan, setPlan] = useState<AgentPlan>()
  const [planning, setPlanning] = useState(false)
  const [reports, setReports] = useState<AgentReport[]>([])
  const selectedModel = models.includes(model) ? model : models[0] || ''

  useEffect(() => {
    void rpc<AgentReport[]>('agent-reports').then(setReports, report)
  }, [])

  async function preview() {
    setPlanning(true)
    setPlan(undefined)
    try { setPlan(await rpc('agent-plan', { role, model: selectedModel, prompt, tools })) }
    catch (error) { report(error) }
    finally { setPlanning(false) }
  }

  async function execute() {
    if (!plan) return
    const result = await run('agent', { id: plan.id, confirmed: true })
    setPlan(undefined)
    if (result) {
      try { setReports(await rpc('agent-reports')) }
      catch (error) { report(error) }
    }
  }

  function toggleTool(tool: string) {
    setPlan(undefined)
    setTools(previous => previous.includes(tool) ? previous.filter(value => value !== tool) : [...previous, tool])
  }

  const disabled = busy || planning
  return <div className="dashboard">
    <section className="panel">
      <h2>建立代理人任務</h2>
      <p className="muted section-note">選擇角色和需要的資料。先檢閱計畫，再核准本次操作。</p>
      <label>角色<select disabled={disabled} value={role} onChange={e => { setRole(e.target.value); setPlan(undefined) }}>
        <option value="general">一般助理</option><option value="research">研究整理</option>
        <option value="technical">技術分析</option>
      </select></label>
      <label>本機模型<select disabled={disabled || !models.length} value={selectedModel}
        onChange={e => { setModel(e.target.value); setPlan(undefined) }}>
        {!models.length && <option value="">請先下載模型</option>}
        {models.map(value => <option key={value}>{value}</option>)}
      </select></label>
      <label>任務描述<textarea disabled={disabled} value={prompt} maxLength={2400}
        onChange={e => { setPrompt(e.target.value); setPlan(undefined) }}/></label>
      <p className="section-note">本次允許的唯讀工具</p>
      <label className="check"><input type="checkbox" disabled={disabled} checked={tools.includes('hardware')}
        onChange={() => toggleTool('hardware')}/>讀取本機硬體摘要</label>
      <label className="check"><input type="checkbox" disabled={disabled} checked={tools.includes('models')}
        onChange={() => toggleTool('models')}/>列出已安裝的模型檔名</label>
      <button className="button section-note" disabled={disabled || !engine || !selectedModel || !prompt.trim()}
        onClick={preview}>{planning ? '準備中…' : '預覽執行計畫'}</button>
      {!engine && <p className="small muted">請先在運算環境安裝 llama.cpp。</p>}
      {plan && <section className="estimate"><div><strong>待核准 · {plan.role}</strong>
        <p>{plan.model}</p><ol>{plan.steps.map((step, index) => <li key={step}>{index + 1}. {step}</li>)}</ol>
        <button className="button primary section-note" disabled={busy} onClick={execute}>核准並執行</button>
      </div></section>}
    </section>
    <section className="panel">
      <h2>代理人報告</h2>
      {busy && job?.steps?.map(step => <p className="muted" key={step}>{step}</p>)}
      {busy && job?.answer && <p className="pre">{job.answer}</p>}
      {!reports.length && <p className="empty">完成任務後，報告與已執行步驟會儲存在這裡。</p>}
      {reports.map(([id, roleName, modelName, task, answer, record, created]) => <details key={id}>
        <summary>{task.slice(0, 60)}</summary>
        <p className="muted">{roleName} · {modelName} · {created} UTC</p>
        <ul>{executionRecord(record).steps.map(step => <li key={step}>{step}</li>)}</ul>
        {executionRecord(record).evidence && <details><summary>工具原始資料</summary>
          <pre className="pre">{JSON.stringify(executionRecord(record).evidence, null, 2)}</pre>
        </details>}
        <p className="pre">{answer}</p>
      </details>)}
    </section>
  </div>
}
