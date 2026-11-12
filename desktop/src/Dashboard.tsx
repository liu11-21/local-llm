import { useEffect, useState } from 'react'
import { Activity, ArrowRight, AudioLines, Bot, Cpu, Film, Image, MessageSquare, Server, Users } from 'lucide-react'
import { rpc, type Info, type Task, type Work, type HardwareCapabilities } from './api'
import { Empty, Panel, gb } from './ui'
import { TaskCenter, activeTask } from './taskQueue'

const destinations = [
  ['chat', '文字聊天', '提問、整理與寫作', MessageSquare],
  ['agent', 'AI 代理人', '使用已核准的工具', Bot],
  ['team', 'AI 團隊', '分工、審查與整合', Users],
  ['image', '圖片生成', '把構想轉成圖像', Image],
  ['video', '影片生成', '從文字建立短片', Film],
  ['music', '音樂生成', '建立配樂與歌曲', AudioLines],
] as const

type Sample = {cpu_percent: number | null; ram_used: number | null; ram_total: number | null;
  gpu_percent: number | null; vram_used: number | null; vram_total: number | null;hardware?:HardwareCapabilities}

function Resources({info, tasks}: {info?: Info; tasks: Task[]}) {
  const [sample, setSample] = useState<Sample>()
  const [selected,setSelected] = useState('')
  useEffect(() => {
    if (!info) return
    let mounted = true
    let pending = false
    const update = async () => {
      if (document.hidden || pending) return
      pending = true
      try {
        const current = await rpc<Sample>('system-resources')
        if (mounted) setSample(current)
      } catch { if (mounted) setSample(undefined) }
      finally { pending = false }
    }
    void update()
    const interval = window.setInterval(update, 3500)
    return () => {mounted = false; window.clearInterval(interval)}
  }, [!!info])
  const running = tasks.filter(task => task.state === 'running')
  const gpus = sample?.hardware?.devices.filter(device=>device.kind==='gpu') ?? []
  const gpu = gpus.find(device=>device.id===selected) ?? gpus[0]
  const model = info?.registry.models.find(item => item.id === info.active?.[0])
  const usage = (used?: number | null, total?: number | null) =>
    total && used != null ? Math.round(100 * used / total) : undefined
  const meters = [
    {label:'CPU', value:sample?.cpu_percent},
    {label:'RAM', value:usage(sample?.ram_used, sample?.ram_total), detail:sample?.ram_used != null ?
      gb(sample.ram_used) + ' / ' + gb(sample.ram_total) : undefined},
    {label:'GPU', value:gpu?.utilization.value},
    {label:'VRAM', value:usage(gpu?.vram_used.value,gpu?.vram_total.value),detail:gpu?.vram_used.value!=null ?
      gb(gpu.vram_used.value)+' / '+gb(gpu.vram_total.value) : undefined},
  ]
  return <section className="resource-board" aria-label="本機資源">
    <header><Activity size={16}/><h2>本機資源</h2><span className="small">{sample ? '即時取樣' : '等待資料'}</span></header>
    {gpus.length>0 && <label className="small section-note">監控 GPU<select value={gpu?.id} onChange={event=>setSelected(event.target.value)}>
      {gpus.map(device=><option value={device.id} key={device.id}>{device.name}</option>)}
    </select></label>}
    <div className="resource-meters">{meters.map(({label,value,detail}) =>
      <div key={label} className="resource-meter">
        <span>{label}</span><b>{value == null ? '未知' : value + '%'}</b>
        {value == null ? <div className="meter-track" aria-hidden="true"/> :
          <meter min={0} max={100} value={value} aria-label={label + ' 使用率'}/>}
        {detail && <small>{detail}</small>}
      </div>)}</div>
    <div className="resource-foot"><Server size={15}/><p className="pre">{model?.label || info?.active?.[0] ||
      (info?.comfy_running ? 'ComfyUI 運作中' : '尚未載入本機模型')}</p>
      <span>{running.length ? [...new Set(running.map(task => task.runtime === 'local' || !task.runtime ? '本機' : '外部'))].join('、') : '運算待命'}</span></div>
  </section>
}

export function Dashboard({ info, tasks, works, go, openWork, openGuide,openChat,openRemote }: {
  info?: Info; tasks: Task[]; works: Work[];
  go: (page: typeof destinations[number][0] | 'library' | 'runtime' | 'tasks' | 'works') => void
  openWork: (work: Work) => void
  openGuide: () => void
  openChat:(id:string)=>void
  openRemote:(runtime:string,task:'chat'|'image'|'video'|'music',model:string)=>void
}) {
  const count = tasks.filter(activeTask).length
  const [recent,setRecent]=useState<{chats:[string,string][];first_use:boolean;recent_model?:string}>()
  useEffect(()=>{if(info)void rpc<NonNullable<typeof recent>>('home-summary').then(setRecent,()=>setRecent(undefined))},[!!info,count,works.length,info?.recent_model])
  const hosts=info?.providers.filter(provider=>provider.kind==='paired') ?? []
  const first=recent?.first_use && !info?.models.length
  return <div className="home">
    <div className="workspace-head">
      <header className="workspace-intro">
        <p className="eyebrow"><span className={info ? 'signal good' : 'signal'}/> LOCAL LLM / WORKSPACE</p>
        <h1>{count ? `${count} 項工作正在處理` : first ? '開始第一項 AI 工作' : '繼續你的工作'}</h1>
        <p>{count ? '可查看進度、取消任務，或在資源允許時開始其他工作。' : first ? '選一項用途，平台會協助準備合適的模型。' : '接續對話、建立作品，或切換已連接的運算來源。'}</p>
        <div className="row creation-actions">
          <button className="button primary" onClick={() => count ? go('tasks') : first ? openGuide() : go('chat')}>{count ? '查看執行任務' : first ? '開始使用' : '開始聊天'} <ArrowRight size={16}/></button>
          <button className="button" onClick={() => go('runtime')}>檢視運算環境</button>
          <button className="button" disabled={!info} onClick={openGuide}>新手引導</button>
        </div>
      </header>
      <Resources info={info} tasks={tasks}/>
    </div>
    <section aria-labelledby="workspace-destinations">
      <div className="workspace-section-title"><h2 id="workspace-destinations">選擇任務</h2><button className="button" aria-label="前往模型與應用" onClick={()=>go('library')}>模型與應用 <ArrowRight size={14}/></button></div>
      <div className="workspace-destinations">{destinations.map(([id,title,description,Icon]) =>
        <button key={id} className="destination" onClick={() => go(id)}>
          <Icon size={20}/><div><strong>{title}</strong><small>{description}</small></div><ArrowRight size={15}/>
        </button>)}</div>
    </section>
    <div className="dashboard">
      <div className="workspace-recent"><TaskCenter tasks={tasks} compact info={info}/>
        {!!count && <button className="button" onClick={()=>go('tasks')}><Cpu size={15}/>查看 {count} 筆執行中或排隊任務</button>}</div>
      <Panel title="最近作品">{works.length ? works.slice(0,3).map(work => <button className="work-link" key={work.name} onClick={() => openWork(work)}>
        <Image size={16}/><span>{work.model || work.name}</span><ArrowRight size={15}/>
      </button>) : <Empty>生成的圖片、影片與音樂會列在這裡。</Empty>}</Panel>
      <Panel title="最近對話">{recent?.chats.length ? recent.chats.map(([id,title])=><button className="work-link" key={id} onClick={()=>openChat(id)}>
        <MessageSquare size={16}/><span>{title}</span><ArrowRight size={15}/></button>) : <Empty>完成聊天後可從這裡接續。</Empty>}
        {info?.recent_model && <p className="small pre section-note">最近模型 · {info.registry.models.find(model=>model.id===info.recent_model)?.label || info.recent_model}</p>}
      </Panel>
      {!!hosts.length && <Panel title="已配對的運算電腦">{hosts.map(host=><article className="home-host" key={host.id}>
        <b>{host.label}</b><p className="small">{host.connected ? '主機在線' : '主機離線'} · 文字推理 {host.capability?.task_health?.chat || '未知'} · {host.models.length} 個文字模型</p>
        <p className="small">{(['image','video','audio'] as const).map(kind=>host.capability?.media?.[kind] ? `${kind==='image' ? '圖片' : kind==='video' ? '影片' : '音樂'} ${host.capability.media[kind]?.state==='ready' ? '就緒' : '待準備'}` : '').filter(Boolean).join(' · ')}</p>
        <button className="button" onClick={()=>{
          const kind=(['video','audio','image'] as const).find(kind=>host.connected && host.capability?.media?.[kind]?.state==='ready')
          if(kind)openRemote(host.id,kind==='audio' ? 'music' : kind,host.capability!.media![kind]!.workflows[0])
          else if(host.connected && host.capability?.task_health?.chat==='ready' && host.models[0])openRemote(host.id,'chat',host.models[0])
          else go('runtime')
        }}>{host.connected ? '開始遠端工作' : '檢查主機'}</button>
      </article>)}</Panel>}
    </div>
  </div>
}
