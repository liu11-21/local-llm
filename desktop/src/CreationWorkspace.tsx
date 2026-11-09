import { useEffect, useState } from 'react'
import { convertFileSrc, isTauri } from '@tauri-apps/api/core'
import { Film, Image, Music2 } from 'lucide-react'
import { rpc, type EngineHealth, type Info, type MediaKind, type Params, type Task, type Work } from './api'
import { activeTask, type Run } from './taskQueue'
import { Empty, Panel, gb } from './ui'

const titles = { image: '圖片', video: '影片', music: '音樂' }
const icons = { image: Image, video: Film, music: Music2 }

function WorkPreview({info, name, kind}: {info?: Info; name: string; kind: MediaKind}) {
  const [failed, setFailed] = useState(false)
  const asset = info && isTauri() ? convertFileSrc(info.output_folder + '/' + name) :
    import.meta.env.MODE === 'preview-worker' ? '/__desktop_dev_output/' + encodeURIComponent(name) : undefined
  if (!asset || failed) return <p className="muted small section-note">目前無法載入預覽。作品檔仍可在作品庫查看位置。</p>
  if (kind === 'image') return <img className="media-output" alt="生成作品" src={asset} onError={() => setFailed(true)}/>
  if (kind === 'video') return <video className="media-output" src={asset} controls onError={() => setFailed(true)}/>
  return <audio className="media-audio" src={asset} controls onError={() => setFailed(true)}/>
}

export function Works({ info, works, selected, choose, reuse }: {
  info?: Info; works: Work[]; selected?: Work; choose: (work: Work) => void; reuse: (work: Work) => void
}) {
  const work = selected ?? works[0]
  return <div className="dashboard"><Panel title="作品庫">
    {!works.length && <Empty>還沒有作品。生成完成後會自動加入。</Empty>}
    {works.map(item => {
      const Icon = icons[item.kind]
      return <button className={'work-link ' + (work?.name === item.name ? 'current' : '')} key={item.name} onClick={() => choose(item)}>
        <Icon size={16}/><span>{item.model || item.name}<small>{new Date(item.created).toLocaleString()}</small></span>
      </button>
    })}
  </Panel><Panel title="作品詳細資料">
    {!work && <Empty>選擇作品後可查看預覽和生成設定。</Empty>}
    {work && <>
      <WorkPreview key={work.name} info={info} name={work.name} kind={work.kind}/>
      <p className="section-note">{work.model || titles[work.kind]} · {gb(work.bytes)}</p>
      <p className="small">{info?.output_folder}/{work.name}</p>
      {work.prompt && <details><summary>提示詞和生成設定</summary><p className="pre">{work.prompt}</p>
        <dl>{Object.entries(work.options || {}).filter(([, value]) => value !== null && value !== '').map(([key, value]) =>
          <div className="list-row" key={key}><dt>{key}</dt><dd>{String(value)}</dd></div>)}</dl></details>}
      {work.workflow && <button className="button section-note" onClick={() => reuse(work)}>重新使用設定</button>}
    </>}
  </Panel></div>
}

type Readiness = {state: 'checking' | 'ready' | 'missing' | 'unavailable'; port: number; missing?: string[]}

export function CreationWorkspace({ kind, info, health, preset, works, tasks, run, go, openWork }: {
  kind: MediaKind; info?: Info; health?: EngineHealth; preset?: Work; works: Work[]; tasks: Task[];
  run: Run; go: (page: 'runtime' | 'works') => void
  openWork: (name: string) => void
}) {
  const [id, setId] = useState('')
  const [prompt, setPrompt] = useState('')
  const [lyrics, setLyrics] = useState('')
  const [overrides, setOverrides] = useState<Params>({})
  const [port, setPort] = useState(8188)
  const [pending, setPending] = useState(false)
  const [result, setResult] = useState<string>()
  const [readiness, setReadiness] = useState<Readiness>()
  const [recheck, setRecheck] = useState(0)
  const workflows = info?.registry.workflows.filter(item => item.kind === kind) || []
  const workflow = workflows.find(item => item.id === id) ?? workflows[0]
  const latest = works.find(work => work.kind === kind)
  const task = tasks.find(task => task.action === 'media' && task.kind === kind)
  const active = task && activeTask(task)
  const servicePort = health && ['ready','busy','starting','unhealthy'].includes(health.comfyui.state) ?
    info?.comfy_port ?? port : port
  const serviceState = health?.comfyui.state
  const preview = result ?? latest?.name
  const apply = (work: Work) => {
    setId(work.workflow ?? ''); setPrompt(work.prompt ?? ''); setLyrics(work.lyrics ?? ''); setOverrides(work.options ?? {})
  }
  useEffect(() => {
    if (preset?.kind === kind) apply(preset)
  }, [preset, kind])
  useEffect(() => {
    let mounted = true
    let timer = 0
    async function check(refresh: boolean) {
      try {
        const state = await rpc<Readiness>('media-readiness', {kind, port: servicePort, refresh})
        if (!mounted) return
        setReadiness(state)
        if (state.state === 'checking') timer = window.setTimeout(() => void check(false), 320)
      } catch { if (mounted) setReadiness({state:'unavailable', port:servicePort}) }
    }
    setReadiness(undefined)
    timer = window.setTimeout(() => void check(true), 250)
    return () => {mounted = false; window.clearTimeout(timer)}
  }, [kind, servicePort, serviceState, recheck])
  const busy = pending || active
  const ready = readiness?.state === 'ready'
  return <div className="dashboard creation">
    <Panel title={'建立' + titles[kind]} description="依所選工作流程調整設定。生成工作會加入任務中心。">
      <label>工作流程<select value={workflow?.id ?? ''} disabled={!workflow || busy} onChange={e => {setId(e.target.value);setOverrides({})}}>
        {workflows.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
      </select></label>
      <form onSubmit={async event => {
        event.preventDefault()
        if (!workflow || busy || !ready || !prompt.trim()) return
        setPending(true); setResult(undefined)
        try {
          const response = await run('media', {kind, prompt, lyrics, port, workflow:workflow.id, options:overrides})
          if (response?.file) setResult(response.file.split('/').at(-1))
        } finally {setPending(false)}
      }}>
        <label>提示詞<textarea maxLength={12000} value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="描述想生成的作品…"/></label>
        {kind === 'music' && <label>歌詞（選填）<textarea maxLength={12000} value={lyrics} onChange={e => setLyrics(e.target.value)}/></label>}
        <details><summary>生成參數</summary><div className="parameters">
          {workflow?.parameters.map(param => <label key={param.key}>{param.label}<input
            type={param.type === 'integer' ? 'number' : 'text'} min={param.min} max={param.max} step={param.step}
            maxLength={param.type === 'text' ? param.max : undefined}
            value={String(overrides[param.key] ?? param.default ?? '')}
            onChange={e => setOverrides(previous => ({...previous, [param.key]:
              param.type === 'text' ? e.target.value : e.target.value === '' ? param.default : Number(e.target.value)}))}/></label>)}
        </div></details>
        <details><summary>連線與必要模型</summary>
          {!(serviceState && ['ready','busy','starting','unhealthy'].includes(serviceState)) &&
            <label>本機 ComfyUI 連接埠<input type="number" min={1024} max={65535} value={port} onChange={e => setPort(+e.target.value)}/></label>}
          <ul>{workflow?.models.map(model => <li key={model}>{model}</li>)}</ul>
        </details>
        <div className="row section-note creation-actions">
          <button className="button primary" disabled={!workflow || busy || !ready || !prompt.trim()}>{busy ? '已提交 · 見任務中心' : '生成' + titles[kind]}</button>
          {latest?.workflow && <button className="button" type="button" disabled={busy} onClick={() => apply(latest)}>沿用上次設定</button>}
        </div>
      </form>
    </Panel>
    <div className="creation-sidebar">
      <Panel title="流程準備">
        <p className="section-note" role="status">{!readiness || readiness.state === 'checking' ? '正在檢查本機 ComfyUI 與權重…' :
          readiness.state === 'unavailable' ? '本機 ComfyUI 目前無法連線。請先啟動服務或檢查連接埠。' :
          readiness.state === 'missing' ? 'ComfyUI 已連線，仍缺少下列權重。' : 'ComfyUI 已連線，必要權重齊備。'}</p>
        {readiness?.missing?.map(name => <p className="small pre" key={name}>{name}</p>)}
        <div className="row section-note creation-actions">
          <button className="button" onClick={() => go('runtime')}>管理 ComfyUI</button>
          <button className="button" onClick={() => setRecheck(n => n+1)}>重新檢查</button>
        </div>
        {active && <p className="pre" role="status">{task.message}</p>}
        {task?.state === 'failed' && <p className="pre creation-error" role="alert">{task.message}</p>}
      </Panel>
      <Panel title={result ? '本次作品' : '最近作品'}>
        {preview ? <><WorkPreview key={preview} info={info} name={preview} kind={kind}/>
          <button className="button section-note" onClick={() => openWork(preview)}>查看作品與參數</button></> :
          <p className="muted small section-note">生成完成後，作品會顯示在這裡。</p>}
        {!preview && <button className="button" onClick={() => go('works')}>開啟作品庫</button>}
      </Panel>
    </div>
  </div>
}
