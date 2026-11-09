import { useEffect, useState } from 'react'
import {
  Activity, AudioLines, Bot, Boxes, ChevronRight, Film, FolderOpen, House, Image,
  ListTodo, LoaderCircle, Menu, MessageSquare, Moon, Server, Settings, Sun, Users, X,
} from 'lucide-react'
import { rpc, type Info, type Job, type Work } from './api'
import { AgentWorkspace } from './AgentWorkspace'
import { ChatWorkspace } from './ChatWorkspace'
import { CreationWorkspace, Works } from './CreationWorkspace'
import { Dashboard } from './Dashboard'
import { ModelLibrary } from './ModelLibrary'
import { RuntimeWorkspace } from './RuntimeWorkspace'
import { SettingsWorkspace } from './SettingsWorkspace'
import { TeamWorkspace } from './TeamWorkspace'
import { activeTask, TaskCenter, useTaskQueue, type Run } from './taskQueue'
import logo from './logo.png'

const navigation = [
  ['工作台', [['home', '首頁', House], ['chat', '文字聊天', MessageSquare], ['agent', 'AI 代理人', Bot], ['team', 'AI 團隊', Users]]],
  ['創作', [['image', '圖片生成', Image], ['video', '影片生成', Film], ['music', '音樂生成', AudioLines], ['works', '作品庫', FolderOpen]]],
  ['管理', [['tasks', '任務中心', ListTodo], ['library', '模型與應用', Boxes], ['runtime', '運算環境', Server], ['settings', '設定', Settings]]],
] as const

type Page = typeof navigation[number][1][number][0]
const pages = navigation.flatMap(([, items]) => [...items])

export function App() {
  const [page, setPage] = useState<Page>('home')
  const [menu, setMenu] = useState(false)
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'system')
  const [policy, setPolicy] = useState(() => localStorage.getItem('policy') || 'auto')
  const [info, setInfo] = useState<Info>()
  const [works, setWorks] = useState<Work[]>([])
  const [selected, setSelected] = useState<Work>()
  const [preset, setPreset] = useState<Work>()
  const [agentJob, setAgentJob] = useState<Job>()
  const [agentBusy, setAgentBusy] = useState(false)
  const [banner, setBanner] = useState<{text: string; error: boolean}>()

  const report = (error: unknown) => setBanner({text: error instanceof Error ? error.message : String(error), error:true})
  const notice = (message: string) => setBanner({text:message, error:false})
  async function refresh() {
    try {
      const [workspace, recent] = await Promise.all([rpc<Info>('info'), rpc<Work[]>('works')])
      setInfo(workspace)
      setWorks(recent)
    } catch (error) { report(error) }
  }
  useEffect(() => { void refresh() }, [])
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem('theme', theme) }, [theme])
  useEffect(() => { localStorage.setItem('policy', policy) }, [policy])
  const queue = useTaskQueue(report, refresh)
  const count = queue.tasks.filter(activeTask).length
  const runningEngine = info?.registry.engines.some(engine => engine.running)
  const go = (value: Page) => {setPage(value);setMenu(false)}
  const [_, title, Icon] = pages.find(item => item[0] === page)!
  const creation = page === 'image' || page === 'video' || page === 'music'
  const runAgent: Run = async (action, data) => {
    setAgentBusy(true); setAgentJob(undefined)
    try {
      const result = await queue.run(action, data, setAgentJob)
      if (result?.message) notice(result.message)
      return result
    } finally {setAgentBusy(false)}
  }
  async function openSavedWork(name: string) {
    try {
      const recent = await rpc<Work[]>('works')
      setWorks(recent)
      setSelected(recent.find(work => work.name === name))
      go('works')
    } catch (error) {report(error)}
  }

  return <div className="shell">
    <aside className={menu ? 'sidebar open' : 'sidebar'}>
      <button className="brand" onClick={() => go('home')}><img src={logo} alt=""/><span>Local LLM<small>AI 工作台</small></span></button>
      <nav aria-label="主要導覽">{navigation.map(([group, items]) => <div className="nav-group" key={group}><p>{group}</p>
        {items.map(([id, text, ItemIcon]) => <button key={id} className={page === id ? 'nav-item selected' : 'nav-item'}
          onClick={() => go(id)} aria-current={page === id ? 'page' : undefined}>
          <ItemIcon size={17}/>{text}{id === 'tasks' && count > 0 && <span className="nav-count">{count}</span>}
        </button>)}</div>)}</nav>
      <div className="sidebar-foot"><span className={info ? 'signal good' : 'signal'}/><span>{info ? '本機工作台已連線' : '等待工作程序'}</span><small>開發版</small></div>
    </aside>
    <main>
      <header className="topbar"><div>
        <button className="mobile icon" title="導覽" aria-expanded={menu} onClick={() => setMenu(!menu)}><Menu size={19}/></button>
        <span>工作區</span><ChevronRight size={14}/><b>{title}</b>
      </div><div>
        <button className="button top-tasks" onClick={() => go('tasks')}><Activity size={16}/>任務{count > 0 && ' ' + count}</button>
        <span className="status-chip engine-chip"><span className={runningEngine ? 'signal good' : 'signal'}/>{runningEngine ? '引擎運行中' : '引擎待命'}</span>
        <button className="icon" title="切換主題" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
          {theme === 'light' ? <Moon size={17}/> : <Sun size={17}/>}
        </button>
      </div></header>
      <div className={'content ' + (page === 'chat' ? 'chat-content' : '')}>
        {banner && <div role={banner.error ? 'alert' : 'status'} className={banner.error ? 'notice failure' : 'notice'}>
          <span>{banner.text}</span><button className="icon" title="關閉訊息" onClick={() => setBanner(undefined)}><X size={17}/></button>
        </div>}
        {!info && !banner?.error && <div role="status" className="work-strip"><LoaderCircle className="spin" size={18}/> 正在連接本機工作程序…</div>}
        {!info && banner?.error && <button className="button" onClick={() => void refresh()}>重新連線</button>}
        {page !== 'home' && page !== 'chat' && <div className="page-title"><div className="tile-icon"><Icon size={22}/></div><h1>{title}</h1></div>}
        {page === 'home' && <Dashboard info={info} tasks={queue.tasks} works={works} go={go}
          openWork={work => {setSelected(work);go('works')}}/>}
        <div hidden={page !== 'chat'}><ChatWorkspace info={info} policy={policy} run={queue.run} cancel={queue.cancel}
          report={report} notice={notice} go={go}/></div>
        {page === 'tasks' && <TaskCenter tasks={queue.tasks} cancel={queue.cancel} retry={queue.retry} loadError={queue.loadError}/>}
        {page === 'library' && <ModelLibrary info={info} tasks={queue.tasks} run={queue.run} report={report} go={go}/>}
        {page === 'runtime' && <RuntimeWorkspace info={info} policy={policy} tasks={queue.tasks} run={queue.run} report={report} notice={notice} refresh={refresh}/>}
        <div hidden={page !== 'team'}><TeamWorkspace info={info} policy={policy} run={queue.run} report={report}/></div>
        {creation && <CreationWorkspace key={page} kind={page} info={info} preset={preset} run={queue.run} go={go} openWork={openSavedWork}/>}
        {page === 'works' && <Works info={info} works={works} selected={selected} choose={setSelected}
          reuse={work => {setPreset(work);go(work.kind)}}/>}
        <div hidden={page !== 'agent'}><AgentWorkspace models={info?.models ?? []} registry={info?.registry.models} engine={!!info?.engine}
          busy={agentBusy} job={agentJob} run={runAgent} report={report}/></div>
        <div hidden={page !== 'settings'}><SettingsWorkspace theme={theme} setTheme={setTheme} policy={policy} setPolicy={setPolicy}
          busy={queue.tasks.some(task => task.action === 'update-download' && activeTask(task))} run={queue.run} report={report}/></div>
      </div>
    </main>
  </div>
}
