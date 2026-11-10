import { useState, type FormEvent } from 'react'
import { ArrowDownToLine } from 'lucide-react'
import { rpc, type EngineHealth, type EngineStatus, type Info, type Task } from './api'
import { engineLabels } from './engineHealth'
import { activeTask, type Run } from './taskQueue'
import { Estimate, Panel, SelectModels, gb } from './ui'
import { ColabWorkspace } from './ColabWorkspace'
import { RemoteWorkspace } from './RemoteWorkspace'
import { RuntimeComparison } from './RuntimeComparison'

function Health({status}: {status?: EngineStatus}) {
  if (!status) return <p className="muted small">正在查詢引擎健康狀態…</p>
  return <div className="engine-health"><span className="tag">{engineLabels[status.state]}</span>
    {status.code && <details><summary>健康診斷 · {status.code}</summary>
      <p className="small">{status.hint}</p><small>{status.checked_at && new Date(status.checked_at).toLocaleString()}</small>
    </details>}
  </div>
}

export function RuntimeWorkspace({info, health, policy, tasks, run, report, notice, refresh, openChat}: {
  info?: Info; health?: EngineHealth; policy: string; tasks: Task[]; run: Run; report: (error: unknown) => void
  notice: (message: string) => void; refresh: () => Promise<void>
  openChat: (id: string) => void
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
  const [mode, setMode] = useState<'local' | 'remote' | 'cloud' | 'colab'>('local')
  const [testing, setTesting] = useState(false)
  const activeText = info?.active?.[0]
  const engineBusy = tasks.some(task => activeTask(task) && task.action.startsWith('engine-'))
  const comfyBusy = tasks.some(task => activeTask(task) && task.action.startsWith('comfy-'))
  const comfyInstalled = info?.comfy_profiles_installed.includes(profile)
  const comfyActive = health ? ['ready','busy','unhealthy'].includes(health.comfyui.state) : info?.comfy_running
  const connect = async (event: FormEvent) => {
    event.preventDefault(); setTesting(true)
    try {
      await rpc('provider-connect', { url: endpoint, label, key, kind:mode })
      setKey(''); notice('已通過模型清單連線測試。'); await refresh()
    } catch (error) { report(error) } finally { setTesting(false) }
  }
  return <>
          <Panel title="選擇運算來源" description="預設在本機運算。外部服務需要手動選擇和確認資料傳送，並可能收費。">
            <div className="runtime-choices">
              {([['local','使用本機'],['remote','連接另一台電腦'],['cloud','新增雲端 AI'],['colab','Google Colab／Notebook']] as const)
                .map(([id,text]) => <button key={id} className={mode===id ? 'button primary' : 'button'} aria-pressed={mode===id}
                  disabled={testing} onClick={() => {
                    if (mode!==id) {setMode(id);setKey('');setEndpoint('');setLabel('')}
                  }}>{text}</button>)}
            </div>
            <p className="small section-note">{info?.providers.length ?? 0} 個外部端點已設定 ·
              {info?.registry.runtimes.find(item=>item.id==='colab')?.ready ? ' Colab Enterprise 已連線' : ' Colab Enterprise 尚未連線'}</p>
          </Panel>
          <RuntimeComparison info={info} policy={policy}/>
          {mode==='local' && <div className="dashboard"><Panel title="本機文字引擎" description={activeText || (info?.engine ? 'llama.cpp 已安裝，等待載入模型。' : '首次使用需要下載官方 llama.cpp。')}>
            <Health status={health?.llama}/>
            {info?.engine ? <><SelectModels models={models} value={local} change={setLocal} registry={info?.registry.models}/><div className="row section-note"><button className="button primary" disabled={engineBusy || !local} onClick={()=>run('engine-start',{model:local,mode:'auto',context:2048})}>啟動模型</button><button className="button" disabled={engineBusy || !activeText} onClick={()=>run('engine-stop',{})}>停止模型</button></div></> :
            <button className="button primary" disabled={engineBusy || !info} onClick={()=>run('engine-install',{})}><ArrowDownToLine size={16}/>安裝官方 llama.cpp</button>}
            {info?.active?.[3] && <Estimate plan={info.active[3]}/>}
            {info?.devices.map(([device,free,shared])=><div className="list-row" key={device}><span>{device}{shared ? ' · 可能為共享記憶體' : ''}</span><b>偵測時可用 {gb(free)}</b></div>)}
          </Panel><Panel title="ComfyUI" description="工作台可按需安裝官方便攜版。首次安裝會下載較大的執行環境。">
            <Health status={health?.comfyui}/>
            <div className="row"><label className="grow">便攜版<select value={profile} onChange={e=>setProfile(e.target.value)}>{info?.profiles.map(p=><option key={p}>{p}</option>)}</select></label><label>連接埠<input type="number" value={port} min={1024} max={65535} onChange={e=>setPort(Number(e.target.value))}/></label></div>
            <div className="row section-note"><button className="button primary" disabled={comfyBusy || !profile || comfyActive} onClick={()=>comfyInstalled ? run('comfy-start',{profile,port}) : run('comfy-install',{profile})}>{comfyInstalled ? '啟動 ComfyUI' : '背景安裝'}</button><button className="button" disabled={comfyBusy || !comfyActive} onClick={()=>run('comfy-stop',{})}>停止服務</button></div>
          </Panel></div>}
          {mode==='remote' && <RemoteWorkspace info={info} refresh={refresh} openChat={openChat} run={run}/>}
          {(mode==='remote' || mode==='cloud') && <details open={mode==='cloud' || undefined}><summary>{mode==='remote' ? '進階：外部 HTTPS 端點' : '設定雲端 API'}</summary><Panel title={mode==='remote' ? '既有 HTTPS 端點' : '雲端 AI 的連線設定'}
            description="需要支援 OpenAI-compatible 的 HTTPS 端點。連線測試讀取模型清單。金鑰只保留在本次工作階段。">
            <form className="endpoint-form runtime-endpoint" onSubmit={connect}>
              <label>連線名稱<input required value={label} maxLength={50} onChange={e=>setLabel(e.target.value)} placeholder={mode==='remote' ? '例如：家用桌機' : '例如：雲端文字服務'}/></label>
              <label>HTTPS 端點<input required value={endpoint} onChange={e=>setEndpoint(e.target.value)} placeholder="https://example.com/v1"/></label>
              <label>API 金鑰<input required type="password" autoComplete="off" value={key} onChange={e=>setKey(e.target.value)}/></label>
              <button className="button primary" disabled={testing}>{testing ? '測試中…' : '測試並連線'}</button></form>
            <p className="small section-note">測試通過後，可在聊天或團隊選擇已連線的模型。工作台會在送出提示詞前再次確認。</p>
          </Panel></details>}
          {!!info?.providers.some(p=>p.kind!=='paired') && <Panel title="已設定的外部端點">
            {info?.providers.filter(p=>p.kind!=='paired').map(p=><div className="list-row" key={p.id}><span><b>{p.label}</b><small>{p.host}:{p.port} · {p.connected ? `${p.models.length} 個模型` : '已中斷'}</small></span>
              <button className="button" disabled={testing} onClick={async()=>{try{await rpc('provider-remove',{id:p.id});await refresh()}catch(e){report(e)}}}>移除</button></div>)}
          </Panel>}
          {mode==='colab' && <ColabWorkspace policy={policy} report={report} onConnectionChange={refresh}/>}
        </>
}
