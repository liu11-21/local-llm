import { useState, type FormEvent } from 'react'
import { ArrowDownToLine } from 'lucide-react'
import { rpc, type EngineHealth, type EngineStatus, type Info, type Task } from './api'
import { engineLabels } from './engineHealth'
import { activeTask, type Run } from './taskQueue'
import { Empty, Estimate, Panel, SelectModels, gb } from './ui'
import { ColabWorkspace } from './ColabWorkspace'

function Health({status}: {status?: EngineStatus}) {
  if (!status) return <p className="muted small">正在查詢引擎健康狀態…</p>
  return <div className="engine-health"><span className="tag">{engineLabels[status.state]}</span>
    {status.code && <details><summary>健康診斷 · {status.code}</summary>
      <p className="small">{status.hint}</p><small>{status.checked_at && new Date(status.checked_at).toLocaleString()}</small>
    </details>}
  </div>
}

export function RuntimeWorkspace({info, health, policy, tasks, run, report, notice, refresh}: {
  info?: Info; health?: EngineHealth; policy: string; tasks: Task[]; run: Run; report: (error: unknown) => void
  notice: (message: string) => void; refresh: () => Promise<void>
}) {
  const models = info?.models ?? []
  const [chosen, setLocal] = useState('')
  const local = models.includes(chosen) ? chosen : models[0] || ''
  const [selectedProfile, setProfile] = useState('')
  const profile = selectedProfile || info?.profiles[0] || ''
  const [port, setPort] = useState(8188)
  const [endpoint, setEndpoint] = useState('')
  const [label, setLabel] = useState('')
  const [key, setKey] = useState('')
  const [kind, setKind] = useState('remote')
  const [testing, setTesting] = useState(false)
  const activeText = info?.active?.[0]
  const engineBusy = tasks.some(task => activeTask(task) && task.action.startsWith('engine-'))
  const comfyBusy = tasks.some(task => activeTask(task) && task.action.startsWith('comfy-'))
  const comfyInstalled = info?.comfy_profiles_installed.includes(profile)
  const comfyActive = health ? ['ready','busy','unhealthy'].includes(health.comfyui.state) : info?.comfy_running
  const connect = async (event: FormEvent) => {
    event.preventDefault(); setTesting(true)
    try {
      await rpc('provider-connect', { url: endpoint, label, key, kind })
      setKey(''); notice('已通過模型清單連線測試。'); await refresh()
    } catch (error) { report(error) } finally { setTesting(false) }
  }
  return <>
          <div className="dashboard"><Panel title="本機文字引擎" description={activeText || (info?.engine ? 'llama.cpp 已安裝，等待載入模型。' : '首次使用需要下載官方 llama.cpp。')}>
            <Health status={health?.llama}/>
            {info?.engine ? <><SelectModels models={models} value={local} change={setLocal} registry={info?.registry.models}/><div className="row section-note"><button className="button primary" disabled={engineBusy || !local} onClick={()=>run('engine-start',{model:local,mode:'auto',context:2048})}>啟動模型</button><button className="button" disabled={engineBusy || !activeText} onClick={()=>run('engine-stop',{})}>停止模型</button></div></> :
            <button className="button primary" disabled={engineBusy || !info} onClick={()=>run('engine-install',{})}><ArrowDownToLine size={16}/>安裝官方 llama.cpp</button>}
            {info?.active?.[3] && <Estimate plan={info.active[3]}/>}
            {info?.devices.map(([device,free,shared])=><div className="list-row" key={device}><span>{device}{shared ? ' · 可能為共享記憶體' : ''}</span><b>偵測時可用 {gb(free)}</b></div>)}
          </Panel><Panel title="ComfyUI" description="工作台可按需安裝官方便攜版。首次安裝會下載較大的執行環境。">
            <Health status={health?.comfyui}/>
            <div className="row"><label className="grow">便攜版<select value={profile} onChange={e=>setProfile(e.target.value)}>{info?.profiles.map(p=><option key={p}>{p}</option>)}</select></label><label>連接埠<input type="number" value={port} min={1024} max={65535} onChange={e=>setPort(Number(e.target.value))}/></label></div>
            <div className="row section-note"><button className="button primary" disabled={comfyBusy || !profile || comfyActive} onClick={()=>comfyInstalled ? run('comfy-start',{profile,port}) : run('comfy-install',{profile})}>{comfyInstalled ? '啟動 ComfyUI' : '背景安裝'}</button><button className="button" disabled={comfyBusy || !comfyActive} onClick={()=>run('comfy-stop',{})}>停止服務</button></div>
          </Panel></div>
          <Panel title="遠端電腦與雲端 API" description="連線測試只讀取模型清單。金鑰保留在本次工作程序的記憶體，關閉程式後須重新連線。">
            <form className="endpoint-form" onSubmit={connect}><label>類型<select value={kind} onChange={e=>setKind(e.target.value)}><option value="remote">遠端電腦</option><option value="cloud">雲端 API</option></select></label>
              <label>連線名稱<input required value={label} maxLength={50} onChange={e=>setLabel(e.target.value)} placeholder="例如：家用桌機"/></label>
              <label>HTTPS 端點<input required value={endpoint} onChange={e=>setEndpoint(e.target.value)} placeholder="https://example.com/v1"/></label>
              <label>API 金鑰<input required type="password" autoComplete="off" value={key} onChange={e=>setKey(e.target.value)}/></label>
              <button className="button primary" disabled={testing}>{testing ? '測試中…' : '測試並連線'}</button></form>
            {!info?.providers.length && <Empty>尚未新增外部連線。所有自動運算仍留在本機。</Empty>}
            {info?.providers.map(p=><div className="list-row" key={p.id}><span><b>{p.label}</b><small>{p.host}:{p.port} · {p.connected ? `${p.models.length} 個模型` : '已中斷'}</small></span>
              <button className="button" disabled={testing} onClick={async()=>{try{await rpc('provider-remove',{id:p.id});await refresh()}catch(e){report(e)}}}>移除</button></div>)}
          </Panel>
          <ColabWorkspace policy={policy} report={report}/>
        </>
}
