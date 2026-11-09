import { useEffect, useState } from 'react'
import { rpc, type Info, type Job } from './api'
import type { Run } from './taskQueue'
import { Empty, Panel, SelectModels } from './ui'

type Member = {id: string; name: string; role: string; system: string; goal: string;
  model: string; runtime: string; tools: string[]; tokens: number; steps: number}
type Node = {id: string; agent: string; label: string; task: string; deps: string[]; partial: boolean;
  state?: string; text?: string; error?: string; evidence?: unknown[]; finished?: string}
type Team = {id?: string; name: string; mode: string; lead: string; expected: string; members: Member[];
  final?: string; nodes?: Node[]; seconds?: number}
type Role = {id: string; name: string; system: string}
type Tool = {id: string; name: string; trusted: boolean; permission: string; input_schema: {required: string[]}}
type Summary = {id: string; name: string; mode: string; state: string}
type Record = {id: string; spec: Team; state: string; nodes: Node[]; answer?: string; error?: string}
const modes = {parallel:'獨立研究', delegated:'分工流程', review:'交叉審查', custom:'自訂 DAG'} as const
const states: {[key: string]: string} = {draft:'準備中', queued:'等待執行', running:'執行中', completed:'完成',
  failed:'失敗', cancelled:'已取消', interrupted:'重開後中斷', skipped:'已略過'}

function Graph({nodes, members}: {nodes: Node[]; members: Member[]}) {
  const names = new Map(members.map(item => [item.id,item.name]))
  return <ol className="team-graph">{nodes.map(item => <li key={item.id}>
    <div className="team-node-heading"><strong>{item.label}</strong>{item.state && <span className="tag">{states[item.state] || item.state}</span>}</div>
    <p className="muted small">{names.get(item.agent)} · {item.id} · {item.deps.length ? '依賴 ' + item.deps.join('、') : '獨立輸入'}</p>
    {item.finished && <time className="small" dateTime={item.finished}>{new Date(item.finished).toLocaleTimeString()}</time>}
    {item.error && <p className="pre creation-error">{item.error}</p>}
    {item.text && <details><summary>查看{item.label}輸出</summary><p className="pre">{item.text}</p></details>}
    {!!item.evidence?.length && <details><summary>工具事實及執行結果</summary><pre className="pre">{JSON.stringify(item.evidence,null,2)}</pre></details>}
  </li>)}</ol>
}

export function TeamWorkflow({visible, info, policy, run, report, cancel}: {
  visible: boolean; info?: Info; policy: string; run: Run; report: (error: unknown) => void; cancel: (id: string) => void
}) {
  const [definitions, setDefinitions] = useState<{templates:Team[]; roles:Role[]}>()
  const [tools, setTools] = useState<Tool[]>([])
  const [saved, setSaved] = useState<Team[]>([])
  const [history, setHistory] = useState<Summary[]>([])
  const [team, setTeam] = useState<Team>()
  const [savedId, setSavedId] = useState<string>()
  const [prompt, setPrompt] = useState('')
  const [custom, setCustom] = useState('')
  const [preview, setPreview] = useState<Team>()
  const [record, setRecord] = useState<Record>()
  const [job, setJob] = useState<Job>()
  const [busy, setBusy] = useState(false)
  const [checking, setChecking] = useState(false)

  async function refreshHistory() {
    try {setHistory(await rpc('team-runs'))} catch(error) {report(error)}
  }
  async function refreshSaved() {
    try {setSaved(await rpc('team-configs'))} catch(error) {report(error)}
  }

  function load(item: Team, id?: string) {
    setTeam(structuredClone(item)); setSavedId(id); setPreview(undefined)
    setCustom(item.nodes?.length ? JSON.stringify(item.nodes,null,2) : '')
  }

  useEffect(() => {
    if (!visible || definitions) return
    let mounted = true
    void rpc<{templates:Team[];roles:Role[]}>('team-templates').then(value => {
      if (!mounted) return
      setDefinitions(value)
      if (value.templates[0]) load(value.templates[0])
      void refreshSaved(); void refreshHistory()
      void rpc<Tool[]>('agent-tools').then(setTools,report)
    }, report)
    return () => {mounted = false}
  }, [visible, definitions])

  const runId = job?.team_run_id
  useEffect(() => {
    if (!busy || !runId) return
    let mounted = true
    let timer: number | undefined
    async function check() {
      try {
        const current = await rpc<Record>('team-run-get', {id:runId})
        if (mounted) {setRecord(current); timer = window.setTimeout(check,500)}
      } catch (error) {if (mounted) report(error)}
    }
    void check()
    return () => {mounted = false; window.clearTimeout(timer)}
  }, [busy,runId])

  const edit = (changes: Partial<Team>) => {
    setTeam(current => current && {...current,...changes})
    setPreview(undefined)
  }
  const editMember = (id: string, changes: Partial<Member>) => {
    setTeam(current => current && {...current, members:current.members.map(item => item.id===id ? {...item,...changes} : item)})
    setPreview(undefined)
  }
  const modelOptions = (member: Member) => member.runtime==='local' ? info?.models || [] :
    info?.providers.find(provider => provider.id===member.runtime)?.models || []
  const payload = () => {
    if (!team) throw Error('請先選擇團隊。')
    if (team.mode!=='custom') return team
    try {return {...team,final:team.final ?? 'final',nodes:JSON.parse(custom)}}
    catch {throw Error('自訂 DAG 必須是合法的 JSON 節點陣列。')}
  }
  async function verify(save = false, copy = false) {
    setChecking(true)
    try {
      const result = await rpc<Team>(save ? 'team-config-save' : 'team-preview',
        {team:payload(), ...(save && !copy && savedId ? {id:savedId} : {})})
      setPreview(result)
      setRecord(undefined)
      if (save) {setSavedId(result.id); void refreshSaved()}
    } catch (error) {report(error)}
    finally {setChecking(false)}
  }

  async function execute() {
    if (!team || !preview || busy || !prompt.trim()) return
    const external = team.members.filter(member => member.runtime !== 'local')
      .map(member => info?.providers.find(provider => provider.id===member.runtime))
    if (external.includes(undefined) || (external.length && policy!=='manual')) {
      report('請重新選擇已連線的端點，並切換為手動運算政策。'); return
    }
    const hosts = [...new Set(external.map(provider => provider!.host + ':' + provider!.port))]
    const consent = hosts.length > 0 && window.confirm('允許將任務與相關節點草稿傳送至 ' + hosts.join('、') + '？可能產生費用。')
    if (hosts.length && !consent) return
    const selectedTools = [...new Set(team.members.flatMap(member => member.tools))]
    const confirmTools = selectedTools.length > 0 && window.confirm('允許本次團隊流程讀取已勾選的本機唯讀工具？')
    if (selectedTools.length && !confirmTools) return
    setBusy(true); setRecord(undefined); setJob(undefined)
    let id: string | undefined
    try {
      await run('team-workflow',{team:preview,prompt,policy,consent,confirm_tools:confirmTools}, current => {
        id = current.team_run_id; setJob(current)
      })
      if (id) setRecord(await rpc('team-run-get',{id}))
      void refreshHistory()
    } catch(error) {report(error)}
    finally {setBusy(false)}
  }

  return <div hidden={!visible} className="dashboard team-flow">
    <Panel title="角色工作流程" description="節點使用各自的上下文。本機依序排程，依賴完成才會開始下一步。">
      {!team || !definitions ? <Empty>正在讀取工作台範本…</Empty> : <fieldset className="team-editor" disabled={busy || checking}>
        <div className="team-flow-fields">
          <label>團隊範本<select value="" disabled={busy} onChange={e => {
            const item = definitions.templates.find(value=>value.id===e.target.value); if (item) load(item)
          }}><option value="">套用範本</option>{definitions.templates.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>已保存的設定<select value={savedId || ''} disabled={busy} onChange={e => {
            const item = saved.find(value=>value.id===e.target.value); if (item) load(item,item.id)
          }}><option value="">選擇設定</option>{saved.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>團隊名稱<input value={team.name} maxLength={80} disabled={busy} onChange={e=>edit({name:e.target.value})}/></label>
          <label>工作模式<select value={team.mode} disabled={busy} onChange={e=>{
            if (e.target.value==='custom' && !custom && preview?.nodes) setCustom(JSON.stringify(preview.nodes,null,2))
            edit({mode:e.target.value})
          }}>
            {Object.entries(modes).map(([id,text])=><option key={id} value={id}>{text}</option>)}
          </select></label>
        </div>
        {team.members.map((member,index) => <section className="team-profile" key={member.id}>
          <div className="team-member-title"><strong>{member.name || '成員 ' + (index+1)}</strong><span className="tag">
            {definitions.roles.find(role=>role.id===member.role)?.name}</span>
            {team.members.length>2 && <button className="button" disabled={busy} onClick={()=>{
              const remaining=team.members.filter(item=>item.id!==member.id)
              edit({members:remaining,lead:team.lead===member.id ? remaining[0].id : team.lead})
            }}>移除</button>}</div>
          <div className="team-flow-fields">
            <label>運算環境<select aria-label={'角色 '+(index+1)+' 運算環境'} value={member.runtime} disabled={busy}
              onChange={e=>editMember(member.id,{runtime:e.target.value,model:''})}>
              <option value="local">本機</option>
              {member.runtime!=='local' && !info?.providers.some(provider=>provider.id===member.runtime) &&
                <option value={member.runtime}>端點需重新連線</option>}
              {info?.providers.map(provider=><option value={provider.id} key={provider.id}>{provider.label}</option>)}
            </select></label>
            <label>模型<SelectModels ariaLabel={'角色 '+(index+1)+' 模型'} models={modelOptions(member)}
              value={member.model} registry={member.runtime==='local' ? info?.registry.models : undefined}
              disabled={busy} change={value=>editMember(member.id,{model:value})}/></label>
          </div>
          <details><summary>角色設定 · {member.id}</summary>
            <div className="team-flow-fields">
              <label>角色<select disabled={busy} value={member.role} onChange={e=>{
                const role=definitions.roles.find(item=>item.id===e.target.value)
                if (role) editMember(member.id,{role:role.id,system:role.system})
              }}>{definitions.roles.map(role=><option key={role.id} value={role.id}>{role.name}</option>)}</select></label>
              <label>顯示名稱<input maxLength={60} value={member.name} disabled={busy} onChange={e=>editMember(member.id,{name:e.target.value})}/></label>
              <label>輸出 Token<input type="number" min={64} max={1024} value={member.tokens} disabled={busy}
                onChange={e=>editMember(member.id,{tokens:Number(e.target.value)})}/></label>
              <label>最多步驟<input type="number" min={1} max={12} value={member.steps} disabled={busy}
                onChange={e=>editMember(member.id,{steps:Number(e.target.value)})}/></label>
            </div>
            <label>System Prompt<textarea maxLength={1200} value={member.system} disabled={busy} onChange={e=>editMember(member.id,{system:e.target.value})}/></label>
            <label>角色目標<textarea maxLength={1200} value={member.goal} disabled={busy} onChange={e=>editMember(member.id,{goal:e.target.value})}/></label>
            <p className="small section-note">本機唯讀工具由成員明確選擇。使用外部端點時，請先取消本機工具。</p>
            {tools.filter(tool=>tool.trusted && tool.permission==='read-only' && !tool.input_schema.required.length)
              .map(tool=><label className="check" key={tool.id}><input type="checkbox" checked={member.tools.includes(tool.id)}
                disabled={busy} onChange={e=>editMember(member.id,{tools:e.target.checked ? [...member.tools,tool.id] :
                  member.tools.filter(id=>id!==tool.id)})}/>{tool.name}</label>)}
          </details>
        </section>)}
        <button className="button section-note" disabled={busy || team.members.length>=6} onClick={()=>{
          const id='m'+crypto.randomUUID().replaceAll('-','').slice(0,8)
          edit({members:[...team.members,{id,name:'新成員',role:'custom',system:'',goal:'',model:'',runtime:'local',tools:[],tokens:384,steps:6}]})
        }}>新增角色</button>
        <details><summary>工作流程進階設定</summary>
          <label>協調成員<select value={team.lead} disabled={busy} onChange={e=>edit({lead:e.target.value})}>
            {team.members.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>預期輸出<input maxLength={300} disabled={busy} value={team.expected} onChange={e=>edit({expected:e.target.value})}/></label>
          <label>總時間（秒）<input type="number" min={30} max={900} value={team.seconds ?? 360} disabled={busy}
            onChange={e=>edit({seconds:Number(e.target.value)})}/></label>
        </details>
        {team.mode==='custom' && <><label>最終節點 ID<input maxLength={32} disabled={busy} value={team.final ?? 'final'}
          onChange={e=>edit({final:e.target.value})}/></label><label>自訂 DAG<textarea value={custom} disabled={busy} maxLength={20000}
          onChange={e=>{setCustom(e.target.value);setPreview(undefined)}}/></label>
          <p className="small">每筆節點包含 id、agent、label、task、deps 和 partial。可先預覽內建流程，再用相同格式建立自己的節點。</p></>}
        <label>團隊共同任務<textarea maxLength={2400} value={prompt} disabled={busy} onChange={e=>setPrompt(e.target.value)}/></label>
        <div className="row section-note team-flow-actions">
          <button className="button" disabled={busy || checking} onClick={()=>void verify()}>預覽依賴</button>
          <button className="button" disabled={busy || checking} onClick={()=>void verify(true)}>保存設定</button>
          {savedId && <button className="button" disabled={busy || checking} onClick={()=>void verify(true,true)}>另存設定</button>}
          <button className="button primary" disabled={!preview || busy || checking || !prompt.trim() ||
            team.members.some(member=>!modelOptions(member).includes(member.model) || (member.runtime==='local' && !info?.engine))}
            onClick={()=>void execute()}>執行角色流程</button>
        </div>
      </fieldset>}
    </Panel>
    <Panel title="依賴與結果">
      {preview?.nodes && !record && <><h3>已驗證的工作流程</h3><Graph nodes={preview.nodes} members={preview.members}/></>}
      {busy && <div className="section-note"><p role="status">{job?.message || '正在提交…'}</p>
        {job?.id && <button className="button" onClick={()=>cancel(job.id)}>取消角色流程</button>}</div>}
      {record && <section className="agent-record"><h3>{record.spec.name} · {states[record.state] || record.state}</h3>
        {record.error && <p role="alert" className="pre creation-error">{record.error}</p>}
        {record.answer && <><h3>最終整合結果</h3><p className="pre">{record.answer}</p></>}
        <Graph nodes={record.nodes} members={record.spec.members}/>
      </section>}
      {!record && !preview && <Empty>預覽節點依賴，或從歷史查看已保存的草稿與審查。</Empty>}
      {!!history.length && <details><summary>團隊執行歷史</summary>{history.map(item=><button className="work-link" key={item.id} disabled={busy}
        onClick={()=>void rpc<Record>('team-run-get',{id:item.id}).then(setRecord,report)}>
        <span>{item.name}<small>{states[item.state] || item.state}</small></span></button>)}</details>}
    </Panel>
  </div>
}
