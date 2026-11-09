import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import type { Info, Job } from './api'
import type { Run } from './taskQueue'
import { Empty, Panel, SelectModels } from './ui'

export function TeamWorkspace({info, policy, run, report}: {
  info?: Info; policy: string; run: Run; report: (error: unknown) => void
}) {
  const models = info?.models ?? []
  const [team, setTeam] = useState<string[]>(['', ''])
  const [teamRuntimes, setTeamRuntimes] = useState<string[]>(['local', 'local'])
  const [lead, setLead] = useState(0)
  const [teamPrompt, setTeamPrompt] = useState('')
  const [serial, setSerial] = useState(false)
  const [teamResult, setTeamResult] = useState<Job['result']>()
  const [job, setJob] = useState<Job>()
  const [busy, setBusy] = useState(false)
  const runTeam = async () => {
    const external = teamRuntimes.filter(id => id !== 'local').map(id => info?.providers.find(p => p.id === id))
    if (external.includes(undefined)) { report('團隊包含已移除的端點，請重新選擇。'); return }
    if (external.length && policy !== 'manual') { report('請先在設定切換為手動運算政策。'); return }
    const hosts = [...new Set(external.map(p => `${p!.host}:${p!.port}`))].join('、')
    const consent = !!external.length && window.confirm(
      `允許將共同任務傳送至 ${hosts}？` + (teamRuntimes[lead] !== 'local' ?
        '遠端主模型也會收到成功成員的草稿。這些請求可能產生費用。' : '這些請求可能產生費用。'))
    if (external.length && !consent) return
    setTeamResult(undefined); setJob(undefined); setBusy(true)
    try {
      setTeamResult(await run('team', {members: team.map((model,i) => ({runtime: teamRuntimes[i],model})),
        lead,prompt:teamPrompt,serial,policy,consent}, setJob))
    } finally {setBusy(false)}
  }
  return <>
          <Panel title="建立模型團隊" description="至少選擇兩個成員。本機依資源預估決定是否並行；使用外部端點前會先確認。">
            {team.map((m,i)=><div className="list-row" key={i}><span>成員 {i+1} {i===lead ? '· 主模型' : ''}<small>{job?.members?.[i]}</small></span>
              <select className="team-runtime" aria-label={`成員 ${i+1} 運算環境`} disabled={busy} value={teamRuntimes[i]} onChange={e=>{
                const value=e.target.value;setTeamRuntimes(t=>t.map((old,j)=>j===i?value:old));setTeam(t=>t.map((old,j)=>j===i?'':old))
              }}><option value="local">本機</option>{info?.providers.map(p=><option value={p.id} key={p.id}>{p.label}</option>)}</select>
              <SelectModels models={teamRuntimes[i]==='local'?models:info?.providers.find(p=>p.id===teamRuntimes[i])?.models||[]} value={m} registry={teamRuntimes[i]==='local' ? info?.registry.models : undefined} disabled={busy} change={v=>setTeam(t=>t.map((old,j)=>j===i?v:old))}/>
              <button className="button" disabled={busy || lead===i} onClick={()=>setLead(i)}>設為主模型</button>
              <button className="icon" title="移除成員" disabled={busy || team.length<=2} onClick={()=>{setTeam(t=>t.filter((_,j)=>j!==i));setTeamRuntimes(t=>t.filter((_,j)=>j!==i));setLead(l=>l>=i?Math.max(0,l-1):l)}}><X size={16}/></button></div>)}
            <div className="row section-note"><button className="button" disabled={busy || team.length>=6} onClick={()=>{setTeam(t=>[...t,'']);setTeamRuntimes(t=>[...t,'local'])}}><Plus size={16}/>成員</button><label className="check"><input type="checkbox" checked={serial} onChange={e=>setSerial(e.target.checked)}/>強制依序執行本機模型</label></div>
            <label>共同任務<textarea value={teamPrompt} onChange={e=>setTeamPrompt(e.target.value)} maxLength={12000} placeholder="描述團隊需要解決的問題…"/></label>
            <button className="button primary section-note" disabled={busy || !teamPrompt.trim() || team.some(v=>!v) || (teamRuntimes.includes('local') && !info?.engine)}
              onClick={runTeam}>執行團隊</button>
          </Panel>
          <Panel title="整合回答">{teamResult ? <><p className="pre">{teamResult.answer}</p><p className="small muted">{teamResult.folder}</p>{teamResult.drafts?.map((d,i)=><details key={i}><summary>{d.name}</summary><p className="pre">{d.text}</p></details>)}</> : <Empty>團隊執行完畢後會顯示主模型回答與成員草稿。</Empty>}</Panel>
        </>
}
