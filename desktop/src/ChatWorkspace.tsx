import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { ArrowUp, Copy, MessageSquare, Pencil, Plus, RotateCcw, Square, Trash2 } from 'lucide-react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { common, createLowlight } from 'lowlight'
import type { RootContent } from 'hast'
import { rpc, type Chat, type Info, type Job, type Message, type Usage } from './api'
import { PreparationNotice, RuntimePicker, TaskModelPicker, TextSetup } from './TaskSelection'
import { TaskFit, useTaskPreparation } from './TaskPreparation'
import type { Run } from './taskQueue'

const highlighter = createLowlight(common)
const identifier = () => crypto.randomUUID().replaceAll('-', '')

function highlightNode(node: RootContent, index: number): ReactNode {
  if (node.type === 'text') return node.value
  if (node.type === 'element') return <span key={index} className={(node.properties.className as string[] || []).join(' ')}>
    {node.children.map(highlightNode)}</span>
  return null
}

function Reply({ content }: { content: string }) {
  return <div className="markdown"><Markdown skipHtml remarkPlugins={[remarkGfm]} components={{
    img: ({alt}) => <span>{alt || '圖片'}</span>,
    a: ({children, href}) => <span className="markdown-link" title={href}>{children}</span>,
    code: ({className, children}) => {
      const language = /^language-([\w+-]+)$/.exec(className || '')?.[1]
      const code = String(children)
      if (!language || !highlighter.registered(language) || code.length > 20_000) return <code>{children}</code>
      return <code className={className}>{highlighter.highlight(language, code).children.map(highlightNode)}</code>
    },
  }}>{content}</Markdown></div>
}

export function ChatWorkspace({ info, policy, run, cancel, report, notice, go, preferredRuntime }: {
  info?: Info; policy: string; run: Run; cancel: (id: string) => void; report: (error: unknown) => void
  notice: (message: string) => void; go: (page: 'library' | 'runtime') => void
  preferredRuntime?: {id:string;model?:string}
}) {
  const [chats, setChats] = useState<Chat[]>([])
  const [chat, setChat] = useState(identifier)
  const [messages, setMessages] = useState<Message[]>([])
  const [prompt, setPrompt] = useState('')
  const [pending, setPending] = useState<{text: string; regenerate: boolean}>()
  const [job, setJob] = useState<Job>()
  const [usage, setUsage] = useState<Usage>()
  const [runtime, setRuntime] = useState('local')
  const [selectedModel, setModel] = useState('')
  const [context, setContext] = useState(2048)
  const [budget, setBudget] = useState(512)
  const [temperature, setTemperature] = useState(0.4)
  const [mode, setMode] = useState('auto')
  const [title, setTitle] = useState<string>()
  const [opening, setOpening] = useState(false)
  const locked = useRef(false)
  const latest = useRef(0)
  const scroll = useRef<HTMLDivElement>(null)
  const stick = useRef(true)
  const provider = info?.providers.find(item => item.id === runtime)
  const prepare = useTaskPreparation()
  const models = runtime === 'local' ? info?.models ?? [] : provider?.models ?? []
  const model = models.includes(selectedModel) ? selectedModel : models[0] || ''
  const canSend = !pending && !opening && !!model && (runtime === 'local' ? !!info?.engine : !!provider?.connected)
  const current = chats.find(([id]) => id === chat)

  async function refreshChats() { setChats(await rpc<Chat[]>('chats')) }
  useEffect(() => { void refreshChats().catch(report) }, [])
  useEffect(() => {
    if (preferredRuntime && !locked.current) {setRuntime(preferredRuntime.id);setModel(preferredRuntime.model ?? '')}
  }, [preferredRuntime])
  useEffect(() => {
    if (scroll.current && stick.current) scroll.current.scrollTop = scroll.current.scrollHeight
  }, [messages, job?.answer, pending])

  async function open(id?: string) {
    if (locked.current) return
    const request = ++latest.current
    setChat(id || identifier()); setMessages([]); setPrompt(''); setUsage(undefined); setTitle(undefined)
    setOpening(!!id); stick.current = true
    try {
      if (id) {
        const rows = await rpc<Message[]>('history', {chat:id,with_runtime:true})
        if (request === latest.current) setMessages(rows)
      }
    } catch (error) { report(error) }
    finally { if (request === latest.current) setOpening(false) }
  }

  async function generate(regenerate: boolean) {
    if (!canSend || locked.current) return
    const text = regenerate ? messages.at(-2)?.content || '' : prompt.trim()
    if (!text || (regenerate && messages.at(-1)?.role !== 'assistant')) return
    locked.current = true
    try {
      const preparation = await prepare('chat',[{model,runtime}],policy,'提示詞及相關對話歷史')
      if (preparation === 'cancelled') return
      const consent = preparation === 'confirmed'
      setPending({text, regenerate}); setJob(undefined); setUsage(undefined); stick.current = true
      if (!regenerate) setPrompt('')
      const result = await run('chat', { chat, prompt:text, model, runtime, policy, consent, context, mode,
        max_tokens:budget, temperature, regenerate }, setJob)
      if (result?.answer) {
        const rows = await rpc<Message[]>('history', {chat,with_runtime:true})
        setPending(undefined); setJob(undefined); setMessages(rows)
        setUsage(result.usage)
        await refreshChats()
      } else if (!regenerate) setPrompt(text)
    } catch (error) { report(error) }
    finally { locked.current = false; setPending(undefined); setJob(undefined) }
  }

  async function rename(event: FormEvent) {
    event.preventDefault()
    if (!title?.trim() || !current || pending) return
    try { await rpc('chat-rename', {chat, title}); setTitle(undefined); await refreshChats() }
    catch (error) { report(error) }
  }
  async function remove() {
    if (!current || pending || !window.confirm('確定刪除「' + current[1] + '」及其中的訊息？')) return
    try { await rpc('chat-delete', {chat, confirmed:true}); await open(); await refreshChats() }
    catch (error) { report(error) }
  }
  const display: Message[] = pending ? [
    ...messages.slice(0, pending.regenerate ? -1 : messages.length),
    ...(!pending.regenerate ? [{role:'user', content:pending.text}] : []),
    ...(job?.answer ? [{role:'assistant', content:job.answer}] : []),
  ] : messages
  const tokens = job?.usage ?? usage

  return <div className="chat-grid">
    <aside className="chat-rail" aria-label="對話歷史">
      <button className="button primary full" disabled={!!pending} onClick={() => void open()}><Plus size={17}/>新對話</button>
      <h2>對話歷史</h2>
      <div className="history">{chats.map(([id, name]) => <button key={id} type="button"
        className={chat === id ? 'history-item current' : 'history-item'} title={name} aria-current={chat === id ? 'true' : undefined}
        disabled={!!pending} onClick={() => void open(id)}><MessageSquare size={15}/><span>{name}</span></button>)}</div>
      {!chats.length && <p className="muted small">完成對話後，歷史會保存在這裡。</p>}
    </aside>
    <section className="chat-stage" aria-label="文字聊天">
      <header className="conversation-top">
        {title !== undefined ? <form className="row" onSubmit={rename}>
          <input autoFocus aria-label="對話名稱" maxLength={80} value={title} onChange={e => setTitle(e.target.value)}/>
          <button className="button">儲存</button><button className="button" type="button" onClick={() => setTitle(undefined)}>取消</button>
        </form> : <div className="row">
          <h2>{current?.[1] || '新對話'}</h2>
          {current && <><button className="icon" title="重新命名對話" disabled={!!pending} onClick={() => setTitle(current[1])}><Pencil size={16}/></button>
            <button className="icon" title="刪除對話" disabled={!!pending} onClick={() => void remove()}><Trash2 size={16}/></button></>}
        </div>}
        <div className="chat-controls">
          <label>模型<TaskModelPicker info={info} runtime={runtime} model={model} change={setModel} disabled={!!pending}/></label>
          <label>運算環境<RuntimePicker info={info} task="chat" value={runtime} disabled={!!pending}
            change={value => {setRuntime(value);setModel('')}}/></label>
        </div>
        <TaskFit key={`${runtime}:${model}:${policy}`} task="chat" runtime={runtime} model={model} policy={policy}/>
        {runtime === 'local' && <TextSetup info={info} run={run} cancel={cancel} openModels={()=>go('library')}/>}
        {runtime !== 'local' && !provider?.connected && <PreparationNotice title="需要重新連線">
          <button className="button section-note" onClick={()=>go('runtime')}>檢查運算環境</button>
        </PreparationNotice>}
      </header>
      <div className="messages" ref={scroll} aria-label="對話內容" onScroll={event => {
        const node = event.currentTarget; stick.current = node.scrollHeight - node.scrollTop - node.clientHeight < 72
      }}>
        {opening ? <p role="status" className="empty">正在開啟對話…</p> : !display.length && <div className="chat-empty">
          <div className="tile-icon"><MessageSquare size={24}/></div><h2>今天想聊什麼？</h2>
          <p>提問、整理想法，或從一個草稿開始。</p>
        </div>}
        {display.map((message, index) => <article className={'message ' + message.role} key={index}>
          <b>{message.role === 'user' ? '你' : '模型'}</b>
          {message.model && <div className="small muted pre">{message.provider} · {message.model}</div>}
          {message.role === 'user' ? <p>{message.content}</p> : <Reply content={message.content}/>}
          {message.role === 'assistant' && !(pending && index === display.length - 1) && <div className="message-tools row">
            <button className="icon" title="複製回答" onClick={() => void navigator.clipboard.writeText(message.content).then(() => notice('已複製回答。'), report)}><Copy size={15}/></button>
            {index === display.length - 1 && !pending && <button className="icon" title="重新生成回答" disabled={!canSend}
              onClick={() => void generate(true)}><RotateCcw size={15}/></button>}
          </div>}
        </article>)}
        {pending && <p role="status" className="muted small">{job?.message || '正在提交…'}</p>}
      </div>
      <footer className="compose-footer">
        <details><summary>生成參數</summary><div className="parameters">
          <label>溫度<input type="number" min={0} max={2} step={0.1} value={temperature} onChange={e => setTemperature(+e.target.value)}/></label>
          <label>最大輸出 Token<input type="number" min={64} max={2048} step={1} value={budget} onChange={e => setBudget(+e.target.value)}/></label>
          {runtime === 'local' && <>
            <label>上下文<select value={context} onChange={e => setContext(+e.target.value)}>{[2048,4096,8192].map(value => <option key={value}>{value}</option>)}</select></label>
            <label>本機裝置<select value={mode} onChange={e => setMode(e.target.value)}><option value="auto">自動分層</option><option value="cpu">只使用 CPU</option></select></label>
          </>}
        </div></details>
        <form className="composer" onSubmit={event => {event.preventDefault(); void generate(false)}}>
          <textarea aria-label="訊息" placeholder="輸入訊息…" value={prompt} maxLength={12000} onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => {if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && !e.nativeEvent.isComposing) e.currentTarget.form?.requestSubmit()}}/>
          {pending ? <button type="button" className="button" title="停止生成" disabled={!job} onClick={() => job && cancel(job.id)}><Square size={17}/>停止</button> :
            <button type="submit" className="button primary" disabled={!canSend || !prompt.trim()}><ArrowUp size={18}/>送出</button>}
        </form>
        <p className="small muted">{tokens ? <>輸入 {tokens.input} / {tokens.context} Token · 最多輸出 {tokens.max_output}{tokens.omitted_turns > 0 && ' · 略過較早 ' + tokens.omitted_turns + ' 輪'}</> :
          <>{runtime === 'local' ? '上下文上限 ' + context + ' Token' : '端點未回報上下文用量'} · Ctrl + Enter 送出</>} · 目前支援文字輸入</p>
      </footer>
    </section>
  </div>
}
