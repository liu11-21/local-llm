import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import type { Info, Job } from './api'
import type { Run } from './taskQueue'
import { Empty, Panel } from './ui'
import { RuntimePicker, TaskModelPicker } from './TaskSelection'
import { useTaskPreparation } from './TaskPreparation'
import { TeamWorkflow } from './TeamWorkflow'

export function TeamWorkspace({info, policy, run, report, cancel}: {
  info?: Info; policy: string; run: Run; report: (error: unknown) => void; cancel: (id: string) => void
}) {
  const [workflow, setWorkflow] = useState(false)
  const [team, setTeam] = useState<string[]>(['', ''])
  const [teamRuntimes, setTeamRuntimes] = useState<string[]>(['local', 'local'])
  const [lead, setLead] = useState(0)
  const [teamPrompt, setTeamPrompt] = useState('')
  const [serial, setSerial] = useState(false)
  const [teamResult, setTeamResult] = useState<Job['result']>()
  const [job, setJob] = useState<Job>()
  const [busy, setBusy] = useState(false)
  const prepare = useTaskPreparation()
  const runTeam = async () => {
    setBusy(true)
    try {
      const members = team.map((model,i) => ({runtime: teamRuntimes[i],model}))
      const preparation = await prepare('team',members,policy,teamRuntimes[lead] === 'local' ? '共同任務' : '共同任務與成員草稿')
      if (preparation === 'cancelled') return
      setTeamResult(undefined); setJob(undefined)
      setTeamResult(await run('team', {members,lead,prompt:teamPrompt,serial,policy,consent:preparation === 'confirmed'}, setJob))
    } catch (error) {report(error)
    } finally {setBusy(false)}
  }
  return <>
          <div className="row team-flow-actions section-note">
            <button className={workflow ? 'button' : 'button primary'} aria-pressed={!workflow} onClick={()=>setWorkflow(false)}>多模型整合</button>
            <button className={workflow ? 'button primary' : 'button'} aria-pressed={workflow} onClick={()=>setWorkflow(true)}>角色與工作流程</button>
          </div>
          <TeamWorkflow visible={workflow} info={info} policy={policy} run={run} report={report} cancel={cancel}/>
          <div hidden={workflow} className="team-classic">
          <Panel title="建立模型團隊" description="至少選擇兩個成員。本機依資源預估決定是否並行；使用外部端點前會先確認。">
            {team.map((m,i)=><div className="team-member" key={i}>
              <div className="team-member-title"><strong>成員 {i+1}</strong>{i===lead && <span className="tag">主模型</span>}</div>
              <div className="team-member-actions">
                {lead!==i && <button className="button" disabled={busy} onClick={()=>setLead(i)}>設為主模型</button>}
                {team.length>2 && <button className="icon" aria-label={`移除成員 ${i+1}`} disabled={busy} onClick={()=>{setTeam(t=>t.filter((_,j)=>j!==i));setTeamRuntimes(t=>t.filter((_,j)=>j!==i));setLead(l=>l>=i?Math.max(0,l-1):l)}}><X size={16}/></button>}
              </div>
              <label>運算環境<RuntimePicker info={info} task="team" ariaLabel={`成員 ${i+1} 運算環境`} disabled={busy}
                value={teamRuntimes[i]} change={value=>{
                  setTeamRuntimes(t=>t.map((old,j)=>j===i?value:old));setTeam(t=>t.map((old,j)=>j===i?'':old))
                }}/></label>
              <label>模型<TaskModelPicker ariaLabel={`成員 ${i+1} 模型`} info={info} runtime={teamRuntimes[i]}
                model={m} disabled={busy} change={v=>setTeam(t=>t.map((old,j)=>j===i?v:old))}/></label>
              {job?.members?.[i] && <p className="team-member-status muted small" role="status">{job.members[i]}</p>}
            </div>)}
            <div className="row section-note"><button className="button" disabled={busy || team.length>=6} onClick={()=>{setTeam(t=>[...t,'']);setTeamRuntimes(t=>[...t,'local'])}}><Plus size={16}/>成員</button><label className="check"><input type="checkbox" checked={serial} onChange={e=>setSerial(e.target.checked)}/>強制依序執行本機模型</label></div>
            <label>共同任務<textarea value={teamPrompt} onChange={e=>setTeamPrompt(e.target.value)} maxLength={12000} placeholder="描述團隊需要解決的問題…"/></label>
            <button className="button primary section-note" disabled={busy || !teamPrompt.trim() || team.some(v=>!v) || (teamRuntimes.includes('local') && !info?.engine)}
              onClick={runTeam}>執行團隊</button>
          </Panel>
          <Panel title="整合回答">{teamResult ? <><p className="pre">{teamResult.answer}</p><p className="small muted">{teamResult.folder}</p>{teamResult.drafts?.map((d,i)=><details key={i}><summary>{d.name}</summary><p className="pre">{d.text}</p></details>)}</> : <Empty>團隊執行完畢後會顯示主模型回答與成員草稿。</Empty>}</Panel>
          {busy && job?.id && <button className="button" onClick={()=>cancel(job.id)}>取消團隊</button>}
          </div>
        </>
}
