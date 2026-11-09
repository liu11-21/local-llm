import { ArrowRight, Boxes, Cpu, HardDrive, Image, MemoryStick, MessageSquare, Server, Users } from 'lucide-react'
import type { Info, Task, Work } from './api'
import { Empty, Panel, gb } from './ui'
import { TaskCenter, activeTask } from './taskQueue'

export function Dashboard({ info, tasks, works, go, openWork }: {
  info?: Info; tasks: Task[]; works: Work[];
  go: (page: 'chat' | 'team' | 'library' | 'image' | 'runtime' | 'tasks' | 'works') => void
  openWork: (work: Work) => void
}) {
  const hardware = info?.hardware
  const model = info?.registry.models.find(item => item.id === info.recent_model)
  const ready = info?.registry.runtimes.filter(item => item.ready) ?? []
  const count = tasks.filter(activeTask).length
  return <div className="home">
    <header className="home-intro">
      <div><p className="eyebrow">LOCAL LLM / WORKSPACE</p><h1>你的 AI 工作台</h1>
        <p>在同一個地方聊天、創作並管理模型。</p></div>
      <button className="button primary" onClick={() => go(info?.models.length ? 'chat' : 'library')}>
        {info?.models.length ? <MessageSquare size={17}/> : <Boxes size={17}/>}
        {info?.models.length ? '開啟聊天' : '下載第一個模型'}
      </button>
    </header>
    {info && !info.models.length && <div className="setup-banner"><Boxes size={20}/><div><strong>設定第一個本機模型</strong>
      <p>在模型中心選擇適合硬體的 GGUF。下載完成後，到運算環境安裝文字引擎，即可開始對話。</p></div></div>}
    <div className="home-summary">
      <button onClick={() => go('chat')}><MessageSquare size={18}/><span>最近使用模型</span><strong>{model?.label || info?.recent_model || '尚未使用'}</strong></button>
      <button onClick={() => go('runtime')}><Server size={18}/><span>可用運算環境</span><strong>{ready.length} 個環境</strong></button>
      <button onClick={() => go('tasks')}><Cpu size={18}/><span>執行中與排隊</span><strong>{count} 筆任務</strong></button>
      <button onClick={() => go('works')}><Image size={18}/><span>最近作品</span><strong>{works.length} 個檔案</strong></button>
    </div>
    <div className="dashboard">
      <TaskCenter tasks={tasks} compact/>
      <Panel title="本機資源">
        <div className="resource-row"><Cpu size={17}/><span>CPU 執行緒</span><b>{hardware?.cpu_threads ?? '—'}</b></div>
        <div className="resource-row"><MemoryStick size={17}/><span>可用記憶體</span><b>{gb(hardware?.ram_available)}</b></div>
        <div className="resource-row"><HardDrive size={17}/><span>可用磁碟</span><b>{gb(hardware?.disk_available)}</b></div>
        <div className="resource-row"><Server size={17}/><span>運算服務</span><b>{info?.registry.engines.filter(engine => engine.running).map(engine => engine.label).join('、') || '待命'}</b></div>
      </Panel>
      <Panel title="快速開始"><div className="quick-links">
        <button onClick={() => go('team')}><Users size={17}/>執行模型團隊<ArrowRight size={15}/></button>
        <button onClick={() => go('image')}><Image size={17}/>開始創作<ArrowRight size={15}/></button>
        <button onClick={() => go('library')}><Boxes size={17}/>探索模型<ArrowRight size={15}/></button>
      </div></Panel>
      <Panel title="最近作品">{works.length ? works.slice(0,3).map(work => <button className="work-link" key={work.name} onClick={() => openWork(work)}>
        <Image size={16}/><span>{work.model || work.name}</span><ArrowRight size={15}/>
      </button>) : <Empty>生成的圖片、影片與音樂會列在這裡。</Empty>}</Panel>
    </div>
  </div>
}
