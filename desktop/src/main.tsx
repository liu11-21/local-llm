import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { convertFileSrc, isTauri } from '@tauri-apps/api/core'
import { Activity, ArrowDownToLine, ArrowRight, ArrowUp, AudioLines, Bot, Boxes, Check, ChevronRight, CircleHelp, Cpu, Film,
  HardDrive, House, Image, Layers3, LoaderCircle, MemoryStick, Menu, MessageSquare, Moon, Plus, Search, Server, Settings,
  Square, Sun, Users, X } from 'lucide-react'
import { rpc, type Info, type Params, type Job, type Chat, type Message, type Task, type Plan, type Recommendation } from './api'
import logo from './logo.png'
import './style.css'

const navigation = [
  ['工作台', [['home', '首頁', House], ['chat', '文字聊天', MessageSquare], ['agent', 'AI 代理人', Bot], ['team', 'AI 團隊', Users]]],
  ['創作', [['image', '圖片生成', Image], ['video', '影片生成', Film], ['music', '音樂生成', AudioLines]]],
  ['管理', [['library', '模型與應用', Boxes], ['runtime', '運算環境', Server], ['settings', '設定', Settings]]]
] as const
type Page = typeof navigation[number][1][number][0]
const pages = navigation.flatMap(([, items]) => [...items])
const descriptions: Record<Page, string> = {
  home: '讓聊天、創作與模型管理都在同一個工作台完成。', chat: '使用本機模型，或手動選擇你信任的端點。',
  agent: '設定角色、工具權限與人工確認的工作空間。', team: '把同一份任務交給不同模型，再由主模型整合回答。',
  image: '用文字提示建立圖片。', video: '用文字提示生成短片。', music: '以提示詞或歌詞生成音樂。',
  library: '找出適合這台電腦的模型，並管理已安裝的推理引擎。', runtime: '管理本機引擎及經驗證的外部連線。',
  settings: '自訂工作台外觀與運算政策。'
}
const actions: Record<string, string> = { chat: '文字聊天', download: '模型下載', team: 'AI 團隊', media: '生成作品',
  'engine-start': '啟動文字引擎', 'engine-stop': '停止文字引擎', 'engine-install': '安裝 llama.cpp', 'comfy-start': '啟動 ComfyUI', 'comfy-stop': '停止 ComfyUI' }
const states: Record<string, string> = { running: '進行中', done: '完成', cancelled: '已取消', error: '失敗', interrupted: '已中斷' }
const gb = (n?: number | null) => n == null ? '—' : `${(n / 2 ** 30).toFixed(n < 2 ** 30 ? 2 : 1)} GB`
const newId = () => crypto.randomUUID().replaceAll('-', '')
const errorText = (error: unknown) => error instanceof Error ? error.message : String(error)
const pause = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

function Panel({ title, children, description }: { title?: string; children: ReactNode; description?: string }) {
  return <section className="panel">{title && <h2>{title}</h2>}{description && <p className="muted section-note">{description}</p>}{children}</section>
}
function Empty({ children }: { children: ReactNode }) { return <div className="empty">{children}</div> }
function Estimate({ plan }: { plan: Plan }) {
  return <div className="estimate"><Layers3 size={17}/><div><b>載入預估</b><p>RAM {gb(plan.ram)} · VRAM {gb(plan.vram)} · 磁碟映射 {gb(plan.mapped_bytes)}</p>
    <p>{plan.device || 'CPU'} · GPU 分層 {plan.layers}/{plan.total_layers}。實際用量會隨上下文與驅動程式變動。</p></div></div>
}
function SelectModels({ models, value, change }: { models: string[]; value: string; change: (s: string) => void }) {
  return <select value={value} onChange={e => change(e.target.value)}><option value="">選擇模型</option>{models.map(m => <option key={m}>{m}</option>)}</select>
}

function App() {
  const [page, setPage] = useState<Page>('home')
  const [menu, setMenu] = useState(false)
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'system')
  const [policy, setPolicy] = useState(() => localStorage.getItem('policy') || 'auto')
  const [info, setInfo] = useState<Info>()
  const [tasks, setTasks] = useState<Task[]>([])
  const [chats, setChats] = useState<Chat[]>([])
  const [chat, setChat] = useState(newId)
  const [messages, setMessages] = useState<Message[]>([])
  const [prompt, setPrompt] = useState('')
  const [pending, setPending] = useState('')
  const [local, setLocal] = useState('')
  const [remote, setRemote] = useState('')
  const [runtime, setRuntime] = useState('local')
  const [context, setContext] = useState(2048)
  const [budget, setBudget] = useState(512)
  const [temperature, setTemperature] = useState(0.4)
  const [mode, setMode] = useState('auto')
  const [job, setJob] = useState<Job>()
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<{text: string; error: boolean}>()
  const [query, setQuery] = useState('')
  const [found, setFound] = useState<[string, number | null][]>()
  const [repo, setRepo] = useState('')
  const [files, setFiles] = useState<[string, number | null, string][]>();
  const [reading, setReading] = useState(false)
  const [workers, setWorkers] = useState(4)
  const [plan, setPlan] = useState<Plan>()
  const [profile, setProfile] = useState('')
  const [port, setPort] = useState(8188)
  const [endpoint, setEndpoint] = useState(''), [label, setLabel] = useState(''), [key, setKey] = useState('')
  const [kind, setKind] = useState('remote')
  const [testing, setTesting] = useState(false)
  const [mediaPrompt, setMediaPrompt] = useState(''), [lyrics, setLyrics] = useState('')
  const [mediaResult, setMediaResult] = useState<{kind: Page; file: string}>()
  const [team, setTeam] = useState<string[]>(['', ''])
  const [teamRuntimes, setTeamRuntimes] = useState<string[]>(['local', 'local'])
  const [lead, setLead] = useState(0)
  const [teamPrompt, setTeamPrompt] = useState('')
  const [serial, setSerial] = useState(false)
  const [teamResult, setTeamResult] = useState<Job['result']>()
  const [jobAction, setJobAction] = useState('')
  const working = useRef(false)
  const last = useRef<HTMLDivElement>(null)
  const provider = info?.providers.find(p => p.id === runtime)
  const models = info?.models ?? []
  const model = runtime === 'local' ? local : remote
  const report = (value: unknown) => setNotice({ text: errorText(value), error: true })
  const refresh = async () => {
    try {
      const data = await rpc<Info & {recommended: Recommendation[]}>('info')
      setInfo(data)
      setLocal(old => data.models.includes(old) ? old : data.models[0] || '')
      setProfile(old => old || data.profiles[0] || '')
      setChats(await rpc<Chat[]>('chats'))
      setTasks(await rpc<Task[]>('tasks'))
    } catch (error) { report(error) }
  }
  useEffect(() => { void refresh() }, [])
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem('theme', theme) }, [theme])
  useEffect(() => { localStorage.setItem('policy', policy) }, [policy])
  useEffect(() => { last.current?.scrollIntoView({ block: 'nearest' }) }, [messages, pending, job?.answer])
  const go = (p: Page) => { setPage(p); setMenu(false) }

  const run = async (action: string, payload: Params): Promise<Job['result']> => {
    if (working.current) return
    working.current = true
    setBusy(true); setJob(undefined); setNotice(undefined); setJobAction(action)
    try {
      const {id} = await rpc<{id: string}>('run', { action, ...payload })
      while (true) {
        const value = await rpc<Job>('job', { id })
        setJob(value)
        if (value.state === 'error') throw new Error(value.message)
        if (value.state === 'cancelled') {
          setNotice({text: value.result?.message || '工作已取消。', error: false})
          return action === 'team' ? value.result : undefined
        }
        if (value.state === 'done') {
          if (action !== 'chat') setNotice({text: value.result?.message || '工作已完成。', error: action === 'team' && !value.result?.answer})
          return value.result
        }
        await pause(220)
      }
    } catch (error) { report(error) }
    finally { working.current = false; setBusy(false); void refresh() }
  }
  const cancel = async () => {
    if (!job) return
    try { await rpc('cancel', {id: job.id}); setJob(j => j && {...j, message: '正在取消…'}) } catch (error) { report(error) }
  }
  const openChat = async (id?: string) => {
    if (busy) return
    setPrompt(''); setMessages([])
    setChat(id || newId())
    go('chat')
    if (id) try { setMessages(await rpc<Message[]>('history', {chat: id})) } catch (error) { report(error) }
  }
  const send = async (event: FormEvent) => {
    event.preventDefault()
    const text = prompt.trim()
    if (!text || !model || busy) return
    const consent = provider && policy === 'manual'
      ? window.confirm(`允許將本輪提示詞及相關對話歷史傳送至 ${provider.host}:${provider.port}？此端點可能產生費用。`) : false
    if (provider && !consent) {
      if (policy !== 'manual') report('請先在設定切換為手動運算政策。')
      return
    }
    setPending(text); setPrompt('')
    const result = await run('chat', { chat, prompt: text, model, runtime, policy, consent, context, mode,
      max_tokens: budget, temperature })
    if (result) {
      setMessages(old => [...old, {role:'user', content:text}, {role:'assistant', content:result.answer || ''}])
    } else { setPrompt(text) }
    setPending('')
  }
  const search = async (event: FormEvent) => {
    event.preventDefault(); setReading(true); setFiles(undefined); setRepo(''); setFound(undefined); setNotice(undefined)
    try { setFound(await rpc('search', { query })) } catch (error) { report(error) } finally { setReading(false) }
  }
  const showFiles = async (name: string) => {
    setRepo(name); setFiles(undefined); setReading(true); setNotice(undefined)
    try { setFiles(await rpc('files', {repo: name})) } catch (error) { report(error) } finally { setReading(false) }
  }
  const connect = async (event: FormEvent) => {
    event.preventDefault(); setTesting(true); setNotice(undefined)
    try {
      await rpc('provider-connect', { url: endpoint, label, key, kind })
      setKey(''); setNotice({text: '已通過模型清單連線測試。', error: false}); await refresh()
    } catch (error) { report(error) } finally { setTesting(false) }
  }
  const runTeam = async () => {
    const external = teamRuntimes.filter(id => id !== 'local').map(id => info?.providers.find(p => p.id === id))
    if (external.includes(undefined)) { report('團隊包含已移除的端點，請重新選擇。'); return }
    if (external.length && policy !== 'manual') { report('請先在設定切換為手動運算政策。'); return }
    const hosts = [...new Set(external.map(p => `${p!.host}:${p!.port}`))].join('、')
    const consent = !!external.length && window.confirm(
      `允許將共同任務傳送至 ${hosts}？` + (teamRuntimes[lead] !== 'local' ?
        '遠端主模型也會收到成功成員的草稿。這些請求可能產生費用。' : '這些請求可能產生費用。'))
    if (external.length && !consent) return
    setTeamResult(undefined)
    setTeamResult(await run('team', {members: team.map((model,i) => ({runtime: teamRuntimes[i],model})),
      lead,prompt:teamPrompt,serial,policy,consent}))
  }
  const selected = pages.find(item => item[0] === page)!
  const PageIcon = selected[2]
  const progress = job?.total && job.received != null ? Math.min(100, 100 * job.received / job.total) : null
  const activeText = info?.active?.[0]
  const hw = info?.hardware
  const showMedia = page === 'image' || page === 'video' || page === 'music'
  const asset = mediaResult?.kind === page && info && isTauri() ?
    convertFileSrc(info.output_folder + '\\' + mediaResult.file.replace(/^\/output\//, '')) : undefined
  const recommendations = (info as (Info & { recommended: Recommendation[] }) | undefined)?.recommended || []

  return <div className="shell">
    <aside className={menu ? 'sidebar open' : 'sidebar'}>
      <button className="brand" onClick={() => go('home')}><img src={logo} alt=""/><span>Local LLM<small>AI 工作台</small></span></button>
      <nav aria-label="主要導覽">{navigation.map(([group, items]) => <div className="nav-group" key={group}><p>{group}</p>
        {items.map(([id, title, Icon]) => <button key={id} className={page === id ? 'nav-item selected' : 'nav-item'}
          onClick={() => go(id)} aria-current={page === id ? 'page' : undefined}><Icon size={17}/>{title}{page === id && <span className="nav-dot"/>}</button>)}</div>)}</nav>
      <div className="sidebar-foot"><span className={info ? 'signal good' : 'signal'}/><span>{info ? '本機工作台已連線' : '等待工作程序'}</span><small>開發版</small></div>
    </aside>
    <main>
      <header className="topbar"><div><button className="mobile icon" title="導覽" onClick={() => setMenu(!menu)}><Menu size={19}/></button>
        <span>工作區</span><ChevronRight size={14}/><b>{selected[1]}</b></div><div>
        <span className="status-chip"><span className={activeText || info?.comfy_running ? 'signal good' : 'signal'}/>{activeText || info?.comfy_running ? '引擎運行中' : '引擎待命'}</span>
        <button className="icon" title="切換主題" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>{theme === 'light' ? <Moon size={17}/> : <Sun size={17}/>}</button></div></header>
      <div className="content">
        {notice && <div role={notice.error ? 'alert' : 'status'} className={notice.error ? 'notice failure' : 'notice'}><span>{notice.text}</span><button className="icon" title="關閉訊息" onClick={() => setNotice(undefined)}><X size={17}/></button></div>}
        {busy && <section className="work-strip" aria-label="工作進度"><LoaderCircle className="spin" size={18}/><div className="grow"><b>{actions[jobAction]}</b>
          <div role="status">{job?.message || '正在準備…'}{progress != null && ` · ${Math.floor(progress)}%`}</div>
          {progress != null && <progress value={progress} max={100}/>}</div><button className="button" disabled={!job} onClick={cancel}><Square size={14}/> 取消</button></section>}
        {!info && !notice && <div role="status" className="work-strip"><LoaderCircle className="spin" size={18}/> 正在連接本機工作程序…</div>}
        {!info && notice?.error && <button className="button" onClick={refresh}>重新連線</button>}

        {page === 'home' ? <>
          <section className="hero"><div><div className="eyebrow"><span className="signal good"/> LOCAL LLM / WORKSPACE</div>
            <h1>你的 AI 工作台</h1><p>{descriptions.home}</p><div className="row"><button className="button primary" onClick={() => openChat()}><Plus size={17}/>開始對話</button>
            <button className="button" onClick={() => go('library')}><Boxes size={16}/>探索模型</button></div></div><div className="hero-art"><img alt="" src={logo}/></div></section>
          <div className="section-label"><h2>快速開始</h2><span>選擇要進行的工作</span></div>
          <div className="quick-grid">{([['chat','與模型聊天','選擇模型，開啟一段新對話',MessageSquare],['team','執行模型團隊','比較答案，再整合成一份結果',Users],
            ['image','生成圖片','從提示詞開始創作',Image],['runtime','管理運算環境','啟動引擎或測試遠端端點',Activity]] as const).map(([id,title,desc,Icon]) =>
            <button className="quick panel" key={id} onClick={() => go(id)}><div className="tile-icon"><Icon size={20}/></div><ArrowRight size={17} className="quick-arrow"/><b>{title}</b><span>{desc}</span></button>)}</div>
          <div className="dashboard">
            <Panel title="系統資源" description="本機目前可用資源，模型載入前會重新估算。">
              <div className="metrics">{[[Cpu, 'CPU 執行緒', hw?.cpu_threads ?? '—'], [MemoryStick, '可用 RAM', gb(hw?.ram_available)],
                [HardDrive, '可用磁碟', gb(hw?.disk_available)]].map(([Icon, text, value]) => { const MetricIcon = Icon as typeof Cpu; return <div key={String(text)}><MetricIcon size={16}/><span>{String(text)}</span><b>{String(value)}</b></div> })}</div>
              <div className="list-row"><span>服務</span><strong>{info?.comfy_running ? 'ComfyUI 已啟動' : activeText ? 'llama.cpp 已啟動' : '目前沒有運行中的服務'}</strong></div>
              <div className="list-row"><span>最近使用模型</span><strong>{info?.recent_model || '尚未使用'}</strong></div>
            </Panel>
            <Panel title="最近任務" description={`本機與 ${info?.providers.filter(p=>p.connected).length || 0} 個外部端點`}>{tasks.length ? tasks.slice(0,4).map(([action,status,time], i) =>
              <div className="list-row" key={i}><span>{actions[action] || action}<small>{time.slice(0,16)} UTC</small></span><span className="tag">{states[status] || status}</span></div>) : <Empty>尚無任務。開始對話或下載模型後，這裡會顯示工作狀態。</Empty>}</Panel>
          </div>
        </> : <><div className="page-title"><div className="tile-icon"><PageIcon size={22}/></div><div><h1>{selected[1]}</h1><p>{descriptions[page]}</p></div></div>
        {page === 'chat' && <div className="chat-grid">
          <Panel title="對話歷史"><button className="button full" disabled={busy} onClick={() => openChat()}><Plus size={16}/> 新對話</button>
            {chats.length ? <div className="history">{chats.map(([id,title]) => <button className={chat===id ? 'history-item current':'history-item'} title={title} disabled={busy} onClick={() => openChat(id)} key={id}><MessageSquare size={14}/><span>{title}</span></button>)}</div> : <Empty>完成第一輪對話後，會自動儲存在這裡。</Empty>}</Panel>
          <Panel><div className="chat-controls"><label>運算環境<select value={runtime} disabled={busy} onChange={e => {setRuntime(e.target.value);setRemote('')}}><option value="local">本機 CPU／GPU</option>{info?.providers.map(p => <option key={p.id} value={p.id}>{p.label}{p.connected ? '' : ' · 已中斷'}</option>)}</select></label>
            <label>模型<SelectModels models={runtime === 'local' ? models : provider?.models || []} value={model} change={runtime === 'local' ? setLocal : setRemote}/></label></div>
            {runtime === 'local' && (!info?.engine || !models.length) && <button className="inline-link" onClick={() => go(info?.engine ? 'library' : 'runtime')}>{info?.engine ? '先下載一個本機模型' : '先安裝 llama.cpp'} <ArrowRight size={14}/></button>}
            <details><summary>生成參數</summary><div className="parameters">
              <label>溫度 <input type="number" min="0" max="2" step="0.1" value={temperature} onChange={e => setTemperature(Number(e.target.value))}/></label>
              <label>最大輸出 Token<input type="number" min="64" max="2048" step="32" value={budget} onChange={e => setBudget(Number(e.target.value))}/></label>
              <label>上下文<select value={context} onChange={e => setContext(Number(e.target.value))}>{[2048,4096,8192].map(c => <option key={c}>{c}</option>)}</select></label>
              <label>本機裝置<select value={mode} onChange={e => setMode(e.target.value)}><option value="auto">自動分層</option><option value="cpu">只使用 CPU</option></select></label>
            </div></details>
            <div className="messages" aria-label="對話內容">{!messages.length && !pending && <div className="chat-empty"><div className="tile-icon"><MessageSquare size={24}/></div><h2>今天想聊什麼？</h2><p>提問、整理想法，或從一個草稿開始。</p></div>}
              {[...messages, ...(pending ? [{role:'user',content:pending}, ...(jobAction === 'chat' && job?.answer ? [{role:'assistant',content:job.answer}] : [])] : [])].map((m,i) =>
                <article className={`message ${m.role}`} key={i}><b>{m.role === 'user' ? '你' : '模型'}</b><p>{m.content}</p></article>)}<div ref={last}/></div>
            <form className="composer" onSubmit={send}><textarea aria-label="訊息" placeholder="輸入訊息…" value={prompt} maxLength={12000} onChange={e => setPrompt(e.target.value)}
              onKeyDown={e => { if (e.key==='Enter' && (e.ctrlKey || e.metaKey) && !e.nativeEvent.isComposing) e.currentTarget.form?.requestSubmit() }}/>
              <button className="button primary" type="submit" title="送出" disabled={busy || !model || !prompt.trim() || (runtime==='local' && !info?.engine)}><ArrowUp size={18}/><span>送出</span></button></form>
            <p className="small muted">Ctrl + Enter 送出。外部端點需要逐次確認傳送。</p>
          </Panel>
        </div>}
        {page === 'library' && <>
          <div className="dashboard"><Panel title="本機模型" description={info?.model_folder || '正在讀取資料夾'}>
            {!models.length && <Empty>尚未安裝 GGUF。可以從下方推薦或 Hugging Face 搜尋下載。</Empty>}
            {models.map(name => <div key={name} className="list-row"><span>{name}</span><button className="button" disabled={!info?.engine || reading || busy} onClick={async()=>{setReading(true);try{setPlan(await rpc('plan',{model:name}))}catch(e){report(e)}finally{setReading(false)}}}>估算</button></div>)}
            {plan && <Estimate plan={plan}/>}</Panel>
            <Panel title="引擎與應用"><div className="list-row"><span>llama.cpp <small>{info?.engine ? '已安裝' : '尚未安裝'}</small></span><button className="button" disabled={!info || busy || info.engine} onClick={()=>run('engine-install',{})}><ArrowDownToLine size={15}/>安裝</button></div>
              <div className="list-row"><span>ComfyUI<small>{info?.comfy_running ? '運行中' : '按需安裝'}</small></span><button className="button" onClick={()=>go('runtime')}>管理</button></div>
              <label>下載執行緒<select value={workers} onChange={e=>setWorkers(Number(e.target.value))}>{[1,2,4,8].map(n=><option key={n}>{n}</option>)}</select></label>
            </Panel></div>
          <Panel title="硬體推薦"><div className="download-list">{recommendations.map(item => <div className="list-row" key={item.repo}><span><b>{item.repo}</b><small>{item.description} · {gb(item.size)}</small></span>
            <span className="tag">{item.fit}</span><button className="button" disabled={busy || models.includes(item.name)} onClick={()=>run('download',{url:item.url,workers})}>
            {models.includes(item.name) ? <Check size={16}/> : <ArrowDownToLine size={16}/>} {models.includes(item.name) ? '已安裝' : '下載'}</button></div>)}</div></Panel>
          <Panel title="Hugging Face 搜尋" description="搜尋公開 GGUF 模型，從固定版本選擇檔案。">
            <form className="row" onSubmit={search}><input className="grow" value={query} onChange={e=>setQuery(e.target.value)} placeholder="輸入模型或作者名稱" aria-label="搜尋模型"/><button className="button primary" disabled={reading}><Search size={16}/>搜尋</button></form>
            {reading && <p className="section-note" role="status"><LoaderCircle className="spin inline" size={16}/> 正在讀取 Hugging Face…</p>}
            {found?.length === 0 && <Empty>沒有符合的公開 GGUF 模型。</Empty>}
            {repo && <p className="section-note"><b>{repo}</b><button className="icon" title="關閉檔案清單" onClick={()=>setRepo('')}><X size={14}/></button></p>}
            {repo && files?.length === 0 && <Empty>沒有可下載的 GGUF 檔案。</Empty>}
            {repo && files?.map(([name,size,url]) => <div className="list-row" key={url}><span>{name}<small>{gb(size)}</small></span><button className="button" disabled={busy} onClick={()=>run('download',{url,workers})}>下載</button></div>)}
            {!repo && found?.map(([name,count]) => <div className="list-row" key={name}><span>{name}<small>{count?.toLocaleString() || '—'} 次下載</small></span><button className="button" disabled={reading} onClick={()=>showFiles(name)}>選擇檔案</button></div>)}
          </Panel>
        </>}
        {page === 'runtime' && <>
          <div className="dashboard"><Panel title="本機文字引擎" description={activeText || (info?.engine ? 'llama.cpp 已安裝，等待載入模型。' : '首次使用需要下載官方 llama.cpp。')}>
            {info?.engine ? <><SelectModels models={models} value={local} change={setLocal}/><div className="row section-note"><button className="button primary" disabled={busy || !local} onClick={()=>run('engine-start',{model:local,mode,context})}>啟動模型</button><button className="button" disabled={busy || !activeText} onClick={()=>run('engine-stop',{})}>停止模型</button></div></> :
            <button className="button primary" disabled={busy || !info} onClick={()=>run('engine-install',{})}><ArrowDownToLine size={16}/>安裝官方 llama.cpp</button>}
            {(job?.plan || info?.active?.[3]) && <Estimate plan={(job?.plan || info?.active?.[3])!}/>}
            {info?.devices.map(([device,free,shared])=><div className="list-row" key={device}><span>{device}{shared ? ' · 可能為共享記憶體' : ''}</span><b>偵測時可用 {gb(free)}</b></div>)}
          </Panel><Panel title="ComfyUI" description="工作台可按需安裝官方便攜版。首次安裝會下載較大的執行環境。">
            <div className="row"><label className="grow">便攜版<select value={profile} onChange={e=>setProfile(e.target.value)}>{info?.profiles.map(p=><option key={p}>{p}</option>)}</select></label><label>連接埠<input type="number" value={port} min={1024} max={65535} onChange={e=>setPort(Number(e.target.value))}/></label></div>
            <div className="row section-note"><button className="button primary" disabled={busy || !profile || info?.comfy_running} onClick={()=>run('comfy-start',{profile,port})}>安裝並啟動</button><button className="button" disabled={busy || !info?.comfy_running} onClick={()=>run('comfy-stop',{})}>停止服務</button></div>
          </Panel></div>
          <Panel title="遠端電腦與雲端 API" description="連線測試只讀取模型清單。金鑰保留在本次工作程序的記憶體，關閉程式後須重新連線。">
            <form className="endpoint-form" onSubmit={connect}><label>類型<select value={kind} onChange={e=>setKind(e.target.value)}><option value="remote">遠端電腦</option><option value="cloud">雲端 API</option></select></label>
              <label>連線名稱<input required value={label} maxLength={50} onChange={e=>setLabel(e.target.value)} placeholder="例如：家用桌機"/></label>
              <label>HTTPS 端點<input required value={endpoint} onChange={e=>setEndpoint(e.target.value)} placeholder="https://example.com/v1"/></label>
              <label>API 金鑰<input required type="password" autoComplete="off" value={key} onChange={e=>setKey(e.target.value)}/></label>
              <button className="button primary" disabled={testing || busy}>{testing ? '測試中…' : '測試並連線'}</button></form>
            {!info?.providers.length && <Empty>尚未新增外部連線。所有自動運算仍留在本機。</Empty>}
            {info?.providers.map(p=><div className="list-row" key={p.id}><span><b>{p.label}</b><small>{p.host}:{p.port} · {p.connected ? `${p.models.length} 個模型` : '已中斷'}</small></span>
              <button className="button" disabled={busy} onClick={async()=>{try{await rpc('provider-remove',{id:p.id});if(runtime===p.id)setRuntime('local');await refresh()}catch(e){report(e)}}}>移除</button></div>)}
          </Panel>
          <Panel title="Google Colab"><span className="tag">尚未開放</span><p className="section-note muted">Colab Enterprise 需要自己的 Google Cloud 專案、授權、GPU 配額及計費設定。這個版本不會建立執行環境或使用額度。</p></Panel>
        </>}
        {page === 'team' && <>
          <Panel title="建立模型團隊" description="至少選擇兩個成員。本機依資源預估決定是否並行；使用外部端點前會先確認。">
            {team.map((m,i)=><div className="list-row" key={i}><span>成員 {i+1} {i===lead ? '· 主模型' : ''}<small>{jobAction==='team' && job?.members?.[i]}</small></span>
              <select className="team-runtime" aria-label={`成員 ${i+1} 運算環境`} disabled={busy} value={teamRuntimes[i]} onChange={e=>{
                const value=e.target.value;setTeamRuntimes(t=>t.map((old,j)=>j===i?value:old));setTeam(t=>t.map((old,j)=>j===i?'':old))
              }}><option value="local">本機</option>{info?.providers.map(p=><option value={p.id} key={p.id}>{p.label}</option>)}</select>
              <SelectModels models={teamRuntimes[i]==='local'?models:info?.providers.find(p=>p.id===teamRuntimes[i])?.models||[]} value={m} change={v=>setTeam(t=>t.map((old,j)=>j===i?v:old))}/>
              <button className="button" disabled={busy || lead===i} onClick={()=>setLead(i)}>設為主模型</button>
              <button className="icon" title="移除成員" disabled={busy || team.length<=2} onClick={()=>{setTeam(t=>t.filter((_,j)=>j!==i));setTeamRuntimes(t=>t.filter((_,j)=>j!==i));setLead(l=>l>=i?Math.max(0,l-1):l)}}><X size={16}/></button></div>)}
            <div className="row section-note"><button className="button" disabled={busy || team.length>=6} onClick={()=>{setTeam(t=>[...t,'']);setTeamRuntimes(t=>[...t,'local'])}}><Plus size={16}/>成員</button><label className="check"><input type="checkbox" checked={serial} onChange={e=>setSerial(e.target.checked)}/>強制依序執行本機模型</label></div>
            <label>共同任務<textarea value={teamPrompt} onChange={e=>setTeamPrompt(e.target.value)} maxLength={12000} placeholder="描述團隊需要解決的問題…"/></label>
            <button className="button primary section-note" disabled={busy || !teamPrompt.trim() || team.some(v=>!v) || (teamRuntimes.includes('local') && !info?.engine)}
              onClick={runTeam}>執行團隊</button>
          </Panel>
          <Panel title="整合回答">{teamResult ? <><p className="pre">{teamResult.answer}</p><p className="small muted">{teamResult.folder}</p>{teamResult.drafts?.map((d,i)=><details key={i}><summary>{d.name}</summary><p className="pre">{d.text}</p></details>)}</> : <Empty>團隊執行完畢後會顯示主模型回答與成員草稿。</Empty>}</Panel>
        </>}
        {showMedia && <>
          <div className="dashboard"><Panel title="建立作品"><label>工作流程<input value={info?.media[page]?.[1] || ''} readOnly/></label>
            <label>提示詞<textarea value={mediaPrompt} maxLength={12000} onChange={e=>setMediaPrompt(e.target.value)} placeholder="描述想生成的作品…"/></label>
            {page==='music' && <label>歌詞（選填）<textarea maxLength={12000} value={lyrics} onChange={e=>setLyrics(e.target.value)}/></label>}
            <div className="row section-note"><button className="button primary" disabled={busy || !mediaPrompt.trim()} onClick={async()=>{
              const result=await run('media',{kind:page,prompt:mediaPrompt,lyrics,port});if(result?.file)setMediaResult({kind:page,file:result.file})}}>生成{selected[1].slice(0,2)}</button>
              {!info?.comfy_running && <button className="button" onClick={()=>go('runtime')}>管理 ComfyUI</button>}</div>
            <details><summary>必要模型與連線</summary><p className="muted">使用工作台啟動的 ComfyUI，或連接本機連接埠 {port}。請先把下列模型放入 ComfyUI 對應的模型目錄。</p>
              <ul>{info?.media[page]?.[2].map(([, , name])=><li key={name}>{name}</li>)}</ul></details></Panel>
            <Panel title="作品預覽">{asset ? (page==='image' ? <img className="media-output" src={asset} alt="生成的圖片"/> :
              page==='video' ? <video className="media-output" controls src={asset}/> : <audio controls src={asset}/>) :
              <Empty>{mediaResult?.kind===page ? mediaResult.file.split('/').pop() : '生成後會在這裡顯示預覽。'}</Empty>}
              {mediaResult?.kind===page && <p className="small muted section-note">{info?.output_folder}</p>}</Panel></div>
        </>}
        {page === 'agent' && <Panel title="代理人工作流程尚未開放" description="工具權限與人工確認尚未實作，這個版本不會替你執行工具。"><Empty><CircleHelp size={19}/> 現在可使用模型團隊分工，並查看每個成員的回答。</Empty><button className="button section-note" onClick={()=>go('team')}>前往 AI 團隊 <ArrowRight size={16}/></button></Panel>}
        {page === 'settings' && <div className="dashboard"><Panel title="外觀"><label>色彩模式<select value={theme} onChange={e=>setTheme(e.target.value)}><option value="system">依系統設定</option><option value="dark">深色</option><option value="light">淺色</option></select></label><p className="muted section-note">介面語言：繁體中文</p></Panel>
          <Panel title="運算政策"><label>預設政策<select value={policy} onChange={e=>setPolicy(e.target.value)}><option value="auto">自動（僅本機）</option><option value="local">只用本機</option>
            <option value="privacy">隱私優先</option><option value="manual">手動選擇</option><option value="performance">效能優先（僅本機）</option><option value="cost">成本優先（僅本機）</option></select></label>
            <p className="muted section-note">只有手動選擇已連線端點，並確認當次資料傳送後，才會呼叫外部模型。</p></Panel></div>}
        </>}
      </div>
    </main>
  </div>
}
createRoot(document.getElementById('root')!).render(<App/>)
