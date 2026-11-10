import { useEffect, useState } from 'react'
import { rpc, type Info, type Job, type Params } from './api'
import { gb } from './ui'
import { RuntimePicker, TaskModelPicker, TextSetup } from './TaskSelection'
import { useTaskPreparation } from './TaskPreparation'
import type { Run } from './taskQueue'

type PlanEvent = {kind: string; at: string; tool?: string; message?: string; code?: string; step?: number; arguments?: Params}
type AgentPlan = { id: string; version: number; role: string; model: string; prompt: string; steps: string[];
  state: string; tools: string[]; mode?: string; task_id?: string; error?: string; answer?: string; review_calls?: boolean;
  pending?: {id: string; tool: string; arguments: Params; decision?: boolean};
  events: PlanEvent[]; evidence: {tool: string; output: unknown}[] }
type ToolDefinition = {id: string; name: string; description: string; permission: string; trusted: boolean;
  input_schema: {required: string[]}}
type AgentReport = [string, string, string, string, string, string, string]
type ExecutionRecord = { steps: string[]; tools?: string[]; evidence?: Record<string, unknown> }
const toolNames: Record<string, string> = {hardware:'本機硬體摘要', models:'已安裝模型清單', engines:'引擎健康狀態',
  tasks:'工作台任務狀態', work:'作品生成參數'}
const eventNames: Record<string, string> = {
  draft:'建立草稿', revised:'修改版本', awaiting_approval:'等待計畫核准', approved:'已核准計畫',
  running:'開始執行', paused:'已暫停', tool_requested:'工具請求', approval_wait:'等待工具核准',
  tool_approved:'核准這次工具', tool_rejected:'拒絕這次工具', tool_result:'工具結果已保存', tool_failed:'工具失敗',
  model_decision:'模型決策', model_format_error:'模型格式不符', model_answer:'模型已提交回答',
  step:'執行步驟', completed:'完成', failed:'失敗', cancelled:'取消', expired:'已過期', interrupted:'重開後中斷',
}
const limits = [
  ['steps','最多步驟',1,12,6], ['calls','最多工具調用',0,8,4], ['seconds','總時間（秒）',15,600,240],
  ['tokens','輸出 Token 上限',64,4096,1536], ['retries','格式重試',0,2,1], ['tool_seconds','單次工具逾時（秒）',1,15,4],
] as const
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
  if (!evidence || !Object.keys(evidence).length) return <p className="small muted">此報告沒有結構化工具資料。</p>
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

export function AgentWorkspace({ info, busy, job, run, report, cancel, setupRun, openModels }: {
  info?: Info
  setupRun: Run
  openModels: () => void
  busy: boolean
  job?: Job
  run: (action: string, payload: Params) => Promise<Job['result']>
  report: (error: unknown) => void
  cancel: (id: string) => void
}) {
  const prepare = useTaskPreparation()
  const models = info?.models ?? []
  const [role, setRole] = useState('general')
  const [model, setModel] = useState('')
  const [prompt, setPrompt] = useState('')
  const [tools, setTools] = useState<string[]>([])
  const [mode, setMode] = useState('simple')
  const [review, setReview] = useState(true)
  const [bounds, setBounds] = useState<Record<string, number>>({})
  const [plan, setPlan] = useState<AgentPlan>()
  const [history, setHistory] = useState<Pick<AgentPlan,'id'|'prompt'|'state'>[]>([])
  const [deciding, setDeciding] = useState(false)
  const [planning, setPlanning] = useState(false)
  const [reports, setReports] = useState<AgentReport[]>([])
  const [definitions, setDefinitions] = useState<ToolDefinition[]>([])
  const selectedModel = models.includes(model) ? model : models[0] || ''

  useEffect(() => {
    void rpc<AgentReport[]>('agent-reports').then(setReports, report)
    void rpc<ToolDefinition[]>('agent-tools').then(setDefinitions, report)
    void refreshHistory()
  }, [])

  async function refreshHistory() {
    try { setHistory(await rpc('agent-plans')) } catch (error) { report(error) }
  }

  const planId = plan?.id
  useEffect(() => {
    if (!busy || !planId || (job?.plan_id && job.plan_id !== planId)) return
    let active = true
    let timer: number | undefined
    async function check() {
      try {
        const next = await rpc<AgentPlan>('agent-plan-get', {id:planId})
        if (active) { setPlan(next); timer = window.setTimeout(check, 450) }
      } catch (error) { if (active) report(error) }
    }
    void check()
    return () => {active = false; window.clearTimeout(timer)}
  }, [busy, planId, job?.plan_id])

  async function preview() {
    setPlanning(true)
    const previous = plan?.state === 'awaiting_approval' ? plan : undefined
    try {
      if (await prepare('agent',[{runtime:'local',model:selectedModel}],'local') === 'cancelled') return
      setPlan(await rpc('agent-plan', {role, model:selectedModel, prompt, tools, mode, review_calls:review,
        limits:bounds, previous:previous?.id, version:previous?.version}))
      void refreshHistory()
    }
    catch (error) { report(error) }
    finally { setPlanning(false) }
  }

  async function execute() {
    if (!plan) return
    await run('agent', { id: plan.id, version:plan.version, confirmed: true })
    try {
      setPlan(await rpc('agent-plan-get', {id:plan.id}))
      setReports(await rpc('agent-reports'))
      void refreshHistory()
    } catch (error) { report(error) }
  }

  async function decide(approved: boolean) {
    if (!plan?.pending) return
    setDeciding(true)
    try {
      await rpc('agent-decision', {id:plan.id, request:plan.pending.id, approved})
      setPlan(await rpc('agent-plan-get', {id:plan.id}))
    } catch (error) {report(error)}
    finally {setDeciding(false)}
  }

  function invalidatePlan() {
    if (!plan || plan.state !== 'awaiting_approval') return
    setPlan(undefined)
    void rpc('agent-plan-revoke', {id:plan.id, version:plan.version}).then(refreshHistory, report)
  }

  function toggleTool(tool: string) {
    invalidatePlan()
    setTools(previous => previous.includes(tool) ? previous.filter(value => value !== tool) : [...previous, tool])
  }

  const disabled = busy || planning
  return <div className="dashboard">
    <section className="panel">
      <h2>建立代理人任務</h2>
      <p className="muted section-note">選擇角色和需要的資料。先檢閱計畫，再核准本次操作。</p>
      <label>代理人模式<select value={mode} disabled={disabled} onChange={e => {
        invalidatePlan()
        setMode(e.target.value)
        if (e.target.value === 'simple') setTools(current => current.filter(key =>
          !definitions.find(tool => tool.id === key)?.input_schema.required.length))
      }}><option value="simple">簡易模式</option><option value="structured">多步驟 · 結構化輸出</option>
        <option value="native">多步驟 · 原生工具調用（實驗）</option></select></label>
      <label>角色<select disabled={disabled} value={role} onChange={e => { setRole(e.target.value); invalidatePlan() }}>
        <option value="general">一般助理</option><option value="research">研究整理</option>
        <option value="technical">技術分析</option>
      </select></label>
      <div className="chat-controls">
        <label>模型<TaskModelPicker ariaLabel="本機模型" info={info} runtime="local" disabled={disabled || !models.length}
          model={selectedModel} change={value => { setModel(value); invalidatePlan() }}/></label>
        <label>運算環境<RuntimePicker info={info} task="agent" value="local" disabled change={()=>{}}/></label>
      </div>
      <TextSetup info={info} run={setupRun} cancel={cancel} openModels={openModels}/>
      {mode !== 'simple' && <p className="small section-note">目前選定模型的工具能力未驗證。可嘗試結構化輸出；若無法遵循格式，可切換簡易模式。</p>}
      <label>任務描述<textarea disabled={disabled} value={prompt} maxLength={2400}
        onChange={e => { setPrompt(e.target.value); invalidatePlan() }}/></label>
      <p className="section-note">本次允許的唯讀工具</p>
      {definitions.filter(tool => tool.trusted && tool.permission === 'read-only' && (mode !== 'simple' || !tool.input_schema.required.length))
        .map(tool => <label className="check" key={tool.id} title={tool.description}><input type="checkbox" disabled={disabled} checked={tools.includes(tool.id)}
          onChange={() => toggleTool(tool.id)}/>{tool.name}</label>)}
      {mode !== 'simple' && <details><summary>進階執行限制</summary>
        <label className="check"><input type="checkbox" disabled={disabled} checked={review} onChange={e => {
          invalidatePlan(); setReview(e.target.checked)
        }}/>每次調用都要核准</label>
        <div className="agent-facts">{limits.map(([key,label,min,max,fallback]) =>
          <label key={key}>{label}<input type="number" min={min} max={max} disabled={disabled} value={bounds[key] ?? fallback}
            onChange={e => {invalidatePlan(); setBounds(current => ({...current, [key]:Number(e.target.value)}))}}/></label>)}</div>
      </details>}
      <button className="button section-note" disabled={disabled || !info?.engine || !selectedModel || !prompt.trim()}
        onClick={preview}>{planning ? '準備中…' : '預覽執行計畫'}</button>
      {plan?.state === 'awaiting_approval' && <section className="estimate"><div><strong>待核准 · {plan.role}</strong>
        <p>{plan.model} · 版本 {plan.version}</p><ol>{plan.steps.map((step, index) => <li key={step}>{index + 1}. {step}</li>)}</ol>
        <p>{plan.tools.length ? plan.tools.map(tool => toolNames[tool] || tool).join('、') : '不使用工具'} · {plan.review_calls ? '逐次核准' : '核准後可在清單內使用'}</p>
        <div className="row section-note"><button className="button primary" disabled={disabled} onClick={execute}>核准並執行</button>
          <button className="button" disabled={disabled} onClick={invalidatePlan}>撤銷計畫</button>
          <button className="button" disabled={disabled} onClick={() => setPlan(undefined)}>保留並另建</button></div>
      </div></section>}
    </section>
    <section className="panel">
      <h2>代理人報告</h2>
      {plan && <section className="agent-record" aria-label="執行時間軸">
        <h3>執行時間軸</h3><p className="pre">{plan.prompt}</p><p className="muted small">{plan.model} · {eventNames[plan.state] || plan.state}</p>
        {plan.pending && plan.state === 'paused' && plan.pending.decision === undefined && <div className="approval-box">
          <h3>核准這次工具調用</h3><p>{toolNames[plan.pending.tool] || plan.pending.tool} · 唯讀本機資料</p>
          <pre className="pre">{JSON.stringify(plan.pending.arguments, null, 2)}</pre>
          <div className="row"><button className="button primary" disabled={deciding} onClick={() => void decide(true)}>允許這一次</button>
            <button className="button" disabled={deciding} onClick={() => void decide(false)}>拒絕這一次</button></div>
        </div>}
        {busy && plan.task_id && <button className="button section-note" onClick={() => cancel(plan.task_id!)}>取消代理人任務</button>}
        <ol className="agent-events">{plan.events.map((event,index) => <li key={index}>
          <time>{new Date(event.at).toLocaleTimeString()}</time> <b>{eventNames[event.kind] || event.kind}</b>
          {event.step ? ' ' + event.step : ''}{event.tool && ' · ' + (toolNames[event.tool] || event.tool)}
          {event.message && <p className="pre small">{event.message}</p>}
        </li>)}</ol>
        {plan.error && <p role="alert" className="creation-error pre">{plan.error}</p>}
        {plan.evidence.length > 0 && <><h3>工具取得的事實</h3>
          {plan.evidence.map((item,index) => <section key={index} className="agent-record">
            <b>{index+1}. {toolNames[item.tool] || item.tool}</b>
            <Evidence evidence={{[item.tool]:item.output}}/>
          </section>)}</>}
        {plan.answer && <><h3>最終回答</h3><p className="pre">{plan.answer}</p></>}
      </section>}
      {busy && <section className="agent-record" aria-label="本次執行"><h3>本次執行</h3>
        <p role="status" className="muted">{job?.message || '正在提交…'}</p>
        {job?.steps?.length && <ol>{job.steps.map((step, index) => <li key={index}>{step}</li>)}</ol>}
        {job?.answer && <><h3>模型正在整理回答</h3><p className="pre">{job.answer}</p></>}
      </section>}
      {!reports.length && <p className="empty">完成任務後，報告與已執行步驟會儲存在這裡。</p>}
      {history.length > 0 && <details><summary>計畫歷史</summary>
        {history.map(item => <button className="work-link" key={item.id} disabled={busy || planning}
          onClick={() => void rpc<AgentPlan>('agent-plan-get',{id:item.id}).then(setPlan,report)}>
          <span>{item.prompt}<small>{eventNames[item.state] || item.state}</small></span></button>)}
      </details>}
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
