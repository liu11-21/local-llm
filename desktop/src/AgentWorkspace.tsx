import { useEffect, useState } from 'react'
import { rpc, type Job, type Params, type Registry } from './api'
import { SelectModels, gb } from './ui'

type AgentPlan = { id: string; role: string; model: string; prompt: string; steps: string[] }
type AgentReport = [string, string, string, string, string, string, string]
type ExecutionRecord = { steps: string[]; tools?: string[]; evidence?: Record<string, unknown> }
const toolNames: Record<string, string> = {hardware:'本機硬體摘要', models:'已安裝模型清單'}
const facts = [
  ['cpu_threads', 'CPU 執行緒'], ['ram_total', '記憶體總量'],
  ['ram_available', '可用記憶體'], ['disk_available', '可用磁碟空間'],
] as const

function executionRecord(raw: string): ExecutionRecord {
  try {
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) return {steps: parsed.filter(item => typeof item === 'string')}
    if (parsed && typeof parsed === 'object') return { ...parsed,
      steps: Array.isArray(parsed.steps) ? parsed.steps.filter((item: unknown) => typeof item === 'string') : [] }
    return {steps:[]}
  } catch { return { steps: [] } }
}

function Evidence({evidence}: {evidence?: Record<string, unknown>}) {
  const hardware = evidence?.hardware
  const values = hardware && typeof hardware === 'object' ? hardware as Record<string, unknown> : undefined
  const models = Array.isArray(evidence?.models) ? evidence.models.filter(item => typeof item === 'string') : undefined
  if (!values && !models) return <p className="small muted">此報告沒有結構化工具資料。</p>
  return <>
    {values && <dl className="agent-facts">{facts.map(([key,label]) => {
      const value = values[key]
      return <div key={key}><dt>{label}</dt><dd>{typeof value === 'number' ?
        key === 'cpu_threads' ? value.toLocaleString() : gb(value) : '未知'}</dd></div>
    })}</dl>}
    {models && (models.length ? <ul>{models.map(model => <li key={model}>{model}</li>)}</ul> :
      <p className="small muted">工具未找到已安裝的模型。</p>)}
    <details><summary>工具原始資料</summary><pre className="pre">{JSON.stringify(evidence, null, 2)}</pre></details>
  </>
}

export function AgentWorkspace({ models, registry, engine, busy, job, run, report }: {
  models: string[]
  registry?: Registry['models']
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
      <label>本機模型<SelectModels models={models} registry={registry} disabled={disabled || !models.length}
        value={selectedModel} change={value => { setModel(value); setPlan(undefined) }}/></label>
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
      {busy && <section className="agent-record" aria-label="本次執行"><h3>本次執行</h3>
        <p role="status" className="muted">{job?.message || '正在提交…'}</p>
        {job?.steps?.length && <ol>{job.steps.map((step, index) => <li key={index}>{step}</li>)}</ol>}
        {job?.answer && <><h3>模型正在整理回答</h3><p className="pre">{job.answer}</p></>}
      </section>}
      {!reports.length && <p className="empty">完成任務後，報告與已執行步驟會儲存在這裡。</p>}
      {reports.map(([id, roleName, modelName, task, answer, record, created]) => {
        const {steps, evidence, tools} = executionRecord(record)
        const approved = tools ?? Object.keys(evidence ?? {})
        return <details className="agent-report" key={id}>
          <summary>{task.slice(0, 60)}</summary>
          <section className="agent-record"><h3>任務描述</h3><p className="pre">{task}</p>
            <p className="small muted">{roleName} · {modelName} · {created} UTC</p>
            <h3>核准工具</h3><p>{approved.length ? approved.map(tool => toolNames[tool] || tool).join('、') :
              tools || evidence ? '未使用工具' : '舊報告未記錄'}</p>
            <h3>執行步驟</h3><ol>{steps.map((step, index) => <li key={index}>{step}</li>)}</ol>
          </section>
          <section className="agent-record"><h3>工具取得的事實</h3><Evidence evidence={evidence}/></section>
          <section className="agent-record"><h3>模型整理的最終回答</h3>
            <p className="small muted">模型可能誤讀或遺漏數值。若回答與工具資料有出入，請以上方工具資料為準。</p>
            <p className="pre">{answer}</p>
          </section>
        </details>
      })}
    </section>
  </div>
}
