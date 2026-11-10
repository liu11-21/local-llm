import { useEffect, useState } from 'react'
import { convertFileSrc, isTauri } from '@tauri-apps/api/core'
import { Film, Image, Music2 } from 'lucide-react'
import { rpc, type EngineHealth, type Info, type MediaInstallPlan, type MediaKind, type Params, type Task, type Work,
  type WorkDimensions, type WorkflowParameter } from './api'
import { activeTask, type Run } from './taskQueue'
import { Empty, Panel, gb } from './ui'

const titles = { image: '圖片', video: '影片', music: '音樂' }
const icons = { image: Image, video: Film, music: Music2 }

function workAsset(info: Info | undefined, name: string) {
  if (!/^[a-f0-9]{12}\.(png|webm|flac)$/.test(name)) return undefined
  if (info && isTauri()) return convertFileSrc(info.output_folder + '/' + name)
  if (import.meta.env.MODE === 'preview-worker') return '/__desktop_dev_output/' + encodeURIComponent(name)
}

function WorkPreview({info, name, kind, onMetadata}: {info?: Info; name: string; kind: MediaKind;
  onMetadata?: (dimensions: WorkDimensions) => void}) {
  const [failed, setFailed] = useState(false)
  const asset = workAsset(info, name)
  if (!asset || failed) return <p className="muted small section-note">目前無法載入預覽。作品檔仍可在作品庫查看位置。</p>
  if (kind === 'image') return <img className="media-output" alt="生成作品" src={asset} onError={() => setFailed(true)}
    onLoad={e => onMetadata?.({width:e.currentTarget.naturalWidth, height:e.currentTarget.naturalHeight})}/>
  if (kind === 'video') return <video className="media-output" src={asset} controls preload="metadata" onError={() => setFailed(true)}
    onLoadedMetadata={e => onMetadata?.({width:e.currentTarget.videoWidth, height:e.currentTarget.videoHeight,
      duration:e.currentTarget.duration})}/>
  return <audio className="media-audio" src={asset} controls preload="metadata" onError={() => setFailed(true)}
    onLoadedMetadata={e => onMetadata?.({duration:e.currentTarget.duration})}/>
}

function WorkDetails({work, info, reuse}: {work: Work; info?: Info; reuse: (work: Work) => void}) {
  const [dimensions, setDimensions] = useState<WorkDimensions>()
  const [error, setError] = useState('')
  const {width, height, duration} = {...work.dimensions, ...dimensions}
  const workflow = info?.registry.workflows.find(item => item.id === work.workflow && item.kind === work.kind)
  const compatible = workflow && (work.schema === undefined || work.schema === 1)
  const supported = new Set(workflow?.parameters.map(parameter => parameter.key))
  const settings = Object.fromEntries(Object.entries(work.options ?? {}).filter(([key]) => supported.has(key)))
  const fields = [
    ['模型', work.model], ['工作流程', workflow?.label ?? work.workflow], ['運算環境', work.runtime === 'local-comfyui' ? '本機 ComfyUI' : undefined],
    ['建立時間', new Date(work.created).toLocaleString()], ['檔案大小', work.bytes < 1024 ** 2 ?
      (work.bytes / 1024).toFixed(1) + ' KiB' : (work.bytes / 1024 ** 2).toFixed(1) + ' MiB'],
    ['輸出尺寸', width && height ? `${width} × ${height}` : undefined],
    ['時長', duration && Number.isFinite(duration) ? duration.toFixed(2) + ' 秒' : undefined],
    ['種子', work.options?.seed], ['任務狀態', work.status === 'completed' ? '已完成' : undefined],
    ['來源任務', work.source?.job], ['來源檔名', work.source?.original],
  ]
  return <>
    <WorkPreview info={info} name={work.name} kind={work.kind} onMetadata={setDimensions}/>
    <dl>{fields.filter(([, value]) => value != null).map(([label, value]) =>
      <div className="list-row pre" key={String(label)}><dt>{String(label)}</dt><dd>{String(value)}</dd></div>)}</dl>
    {(work.prompt || work.lyrics || work.options) && <details><summary>提示詞和生成設定</summary>
      {work.prompt && <p className="pre">{work.prompt}</p>}
      {work.lyrics && <><h3>歌詞</h3><p className="pre">{work.lyrics}</p></>}
      <dl>{Object.entries(work.options ?? {}).filter(([, value]) => value != null && value !== '').map(([key, value]) =>
        <div className="list-row pre" key={key}><dt>{workflow?.parameters.find(p => p.key === key)?.label ?? key}</dt><dd>{String(value)}</dd></div>)}</dl>
    </details>}
    <div className="row section-note creation-actions">
      {compatible && <button className="button" onClick={() => reuse({...work, options:settings})}>重新使用設定</button>}
      <button className="button" onClick={async () => {
        setError('')
        try { await rpc('work-open', {name:work.name}) }
        catch (failure) {setError(failure instanceof Error ? failure.message : String(failure))}
      }}>開啟原始檔案</button>
    </div>
    {work.workflow && !compatible && <p className="small muted">這件作品的工作流程版本目前無法回填。</p>}
    {error && <p className="creation-error pre" role="alert">{error}</p>}
  </>
}

export function Works({ info, revision, selected, choose, reuse }: {
  info?: Info; revision: Work[]; selected?: Work; choose: (work: Work) => void; reuse: (work: Work) => void
}) {
  const [kind, setKind] = useState('')
  const [model, setModel] = useState('')
  const [sort, setSort] = useState('newest')
  const [query, setQuery] = useState('')
  const [offset, setOffset] = useState(0)
  const [page, setPage] = useState<{items:Work[]; models:string[]; total:number}>()
  const [issue, setIssue] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let mounted = true
    setLoading(true); setIssue('')
    const timer = setTimeout(() => {
      void rpc<NonNullable<typeof page>>('works-library', {kind, model, sort, query, offset}).then(
        result => {if (mounted) {setPage(result); setLoading(false)}},
        error => {if (mounted) {setIssue(String(error instanceof Error ? error.message : error)); setLoading(false)}},
      )
    }, 180)
    return () => {mounted = false; clearTimeout(timer)}
  }, [kind, model, sort, query, offset, revision])
  const works = page?.items ?? []
  const work = works.find(item => item.name === selected?.name) ?? (!kind && !model && !query && offset === 0 ? selected : undefined) ?? works[0]
  return <div className="dashboard"><Panel title="作品庫">
    <label>搜尋作品<input type="search" maxLength={180} value={query} placeholder="提示詞、模型或檔名"
      onChange={e => {setQuery(e.target.value);setOffset(0)}}/></label>
    <div className="parameters work-filters section-note">
      <label>類型<select aria-label="類型" value={kind} onChange={e => {setKind(e.target.value);setOffset(0)}}>
        <option value="">全部類型</option>{Object.entries(titles).map(([value, title]) => <option value={value} key={value}>{title}</option>)}
      </select></label>
      <label>模型篩選<select aria-label="模型篩選" value={model} onChange={e => {setModel(e.target.value);setOffset(0)}}>
        <option value="">全部模型</option>{page?.models.map(name => <option key={name}>{name}</option>)}
      </select></label>
      <label>日期排序<select aria-label="日期排序" value={sort} onChange={e => {setSort(e.target.value);setOffset(0)}}>
        <option value="newest">最新優先</option><option value="oldest">最舊優先</option>
      </select></label>
    </div>
    {loading && <p className="muted section-note" role="status">正在讀取作品…</p>}
    {issue && <p role="alert" className="creation-error pre">{issue}</p>}
    {!loading && !issue && !works.length && <Empty>{kind || model || query ? '找不到符合條件的作品。' : '還沒有作品。生成完成後會自動加入。'}</Empty>}
    {works.map(item => {
      const Icon = icons[item.kind]
      const thumbnail = item.kind === 'image' ? workAsset(info, item.name) : undefined
      return <button className={'work-link ' + (work?.name === item.name ? 'current' : '')} key={item.name} onClick={() => choose(item)}>
        {thumbnail ? <img className="work-thumb" src={thumbnail} alt="" loading="lazy"
          onError={e => {e.currentTarget.hidden = true}}/> : <Icon size={16}/>}
        <span>{item.model || item.name}<small>{new Date(item.created).toLocaleString()}</small></span>
      </button>
    })}
    {(offset > 0 || (page?.total ?? 0) > 24) && <div className="row section-note creation-actions">
      <button className="button" disabled={!offset || loading} onClick={() => setOffset(n => n - 24)}>上一頁</button>
      <button className="button" disabled={offset + 24 >= (page?.total ?? 0) || loading} onClick={() => setOffset(n => n + 24)}>下一頁</button>
    </div>}
  </Panel><Panel title="作品詳細資料">
    {!work && <Empty>選擇作品後可查看預覽和生成設定。</Empty>}
    {work && <WorkDetails key={work.name} work={work} info={info} reuse={reuse}/>}
  </Panel></div>
}

type Readiness = {state: 'checking' | 'ready' | 'missing' | 'unavailable'; port: number; missing?: string[]; missing_nodes?: string[]}

function MediaSetup({kind, info, port, ready, tasks, run, cancel, retry, refresh}: {
  kind: MediaKind; info?: Info; port: number; ready: boolean; tasks: Task[]; run: Run;
  cancel: (id: string) => void; retry: (id: string) => Promise<void>; refresh: () => void
}) {
  const [selection, setSelection] = useState('')
  const [plan, setPlan] = useState<MediaInstallPlan>()
  const [issue, setIssue] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [pending, setPending] = useState(false)
  const [check, setCheck] = useState(0)
  const profiles = info?.profiles ?? []
  const profile = selection || info?.comfy_profiles_installed[0] || profiles[0] || ''
  const model = info?.registry.media_models?.find(item => item.kind === kind)
  const install = plan && tasks.find(task => task.media_target === plan.target)
  const downloading = install && activeTask(install)
  const busy = pending || downloading || tasks.some(task => activeTask(task) && ['comfy-install','comfy-start'].includes(task.action))
  const installedProfiles = info?.comfy_profiles_installed.join(',')
  const installState = install?.state
  useEffect(() => {
    if (!profile || !model) return
    let mounted = true
    setIssue('')
    void rpc<MediaInstallPlan>('media-install-plan', {kind, profile}).then(
      result => {if (mounted) setPlan(result)},
      error => {if (mounted) {setIssue(String(error instanceof Error ? error.message : error)); setPlan(undefined)}},
    )
    return () => {mounted = false}
  }, [kind, profile, model?.id, installedProfiles, check, installState === 'completed'])
  if (!model || !profile) return null
  const current = plan?.profile === profile ? plan : undefined
  const missing = current?.files.some(file => file.status === 'missing')
  async function finish(action: () => Promise<unknown>) {
    setPending(true)
    try {await action()} finally {
      setPending(false); setConfirmed(false); setCheck(n => n + 1); refresh()
    }
  }
  return <details className="section-note" open={!ready || undefined}>
    <summary>安裝或檢查本機模型</summary>
    <label>本機運算環境<select value={profile} disabled={!!busy} onChange={event => {
      setSelection(event.target.value); setConfirmed(false)
    }}>{profiles.map(name => <option key={name}>{name}</option>)}</select></label>
    {!current && <p className="small" role={issue ? 'alert' : 'status'}>{issue || '正在讀取安裝摘要…'}</p>}
    {current && <>
      <p className="small pre">{model.label} · {model.publisher} · {model.version} · {model.license}</p>
      <p className="small pre">Hugging Face · 固定版本 {model.revision}</p>
      <p className="small">待下載 {gb(current.needed)} · 磁碟可用 {gb(current.free)}</p>
      <p className="small muted">本機可用 RAM {info?.hardware.ram_available != null ? gb(info.hardware.ram_available) : '未知'}。模型所需 RAM 與 VRAM 隨生成設定變動，目前沒有經實測的最低值。</p>
      {kind !== 'image' && profile === 'CPU' && <p className="small">影片與音樂在 CPU 上可能非常慢，或因記憶體不足而失敗。</p>}
      <details><summary>權重、安裝位置與校驗值</summary>
        {current.files.map(file => <div className="section-note small pre" key={file.filename}>
          <strong>{file.filename}</strong> · {gb(file.bytes)} · {file.status === 'present' ? '已找到' : file.status === 'conflict' ? '同名衝突' : '缺少'}
          <div>{file.path}</div><div>SHA-256 {file.sha256}</div>
        </div>)}
        <p className="small pre">{model.terms}</p>
      </details>
      {current.conflict && <p className="creation-error small" role="alert">權重目錄有同名衝突。請檢查並自行移開該檔案後重新檢查。</p>}
      {current.needed > current.free && <p className="creation-error small" role="alert">磁碟空間不足。</p>}
      {!current.installed ? <button className="button section-note" disabled={!!busy}
        onClick={() => void finish(() => run('comfy-install', {profile}))}>下載並安裝 ComfyUI</button> :
        <>
          {!current.conflict && current.needed <= current.free && <label className="row section-note">
            <input type="checkbox" checked={confirmed} disabled={!!busy} onChange={e => setConfirmed(e.target.checked)}/>
            {missing ? '我已查看授權，並同意從 Hugging Face 下載上述權重' : '驗證現有權重的 SHA-256'}
          </label>}
          <div className="row section-note creation-actions">
            <button className="button" disabled={!confirmed || !!busy || current.conflict || current.needed > current.free}
              onClick={() => void finish(() => run('media-install', {kind, profile, confirmed: true}))}>
              {missing ? '一鍵安裝模型' : '驗證權重'}</button>
            {!ready && !missing && !info?.comfy_running && <button className="button" disabled={!!busy || current.conflict}
              onClick={() => void finish(() => run('comfy-start', {profile, port}))}>啟動所選 ComfyUI</button>}
          </div>
        </>}
    </>}
    {install && <p className="small pre" role={install.state === 'failed' ? 'alert' : 'status'}>{install.message}</p>}
    {downloading && install && <div className="row creation-actions">
      {!!install.total && <progress aria-label="模型安裝進度" value={install.received ?? 0} max={install.total}/>}
      <button className="button" onClick={() => cancel(install.id)}>取消模型安裝</button>
    </div>}
    {install?.retryable && <button className="button section-note" disabled={!!busy}
      onClick={() => void finish(() => retry(install.id))}>重試模型安裝</button>}
  </details>
}

export function CreationWorkspace({ kind, info, health, preset, works, tasks, run, cancel, retry, go, openWork }: {
  kind: MediaKind; info?: Info; health?: EngineHealth; preset?: Work; works: Work[]; tasks: Task[];
  run: Run; go: (page: 'runtime' | 'works') => void
  cancel: (id: string) => void; retry: (id: string) => Promise<void>
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
    const saved = workflows.find(item => item.id === work.workflow)
    if (!saved || (work.schema !== undefined && work.schema !== 1)) return
    const keys = new Set(saved.parameters.map(param => param.key))
    setId(saved.id); setPrompt(work.prompt ?? ''); setLyrics(work.lyrics ?? '')
    setOverrides(Object.fromEntries(Object.entries(work.options ?? {}).filter(([key]) => keys.has(key))))
  }
  useEffect(() => {
    if (preset?.kind === kind) apply(preset)
  }, [preset, kind, info?.registry.workflows.length])
  useEffect(() => {
    let mounted = true
    let timer = 0
    async function check(refresh: boolean) {
      try {
        const state = await rpc<Readiness>('media-readiness', {kind, port: servicePort, workflow: workflow?.id, refresh})
        if (!mounted) return
        setReadiness(state)
        if (state.state === 'checking') timer = window.setTimeout(() => void check(false), 320)
      } catch { if (mounted) setReadiness({state:'unavailable', port:servicePort}) }
    }
    setReadiness(undefined)
    timer = window.setTimeout(() => void check(true), 250)
    return () => {mounted = false; window.clearTimeout(timer)}
  }, [kind, servicePort, serviceState, recheck, workflow?.id])
  const busy = pending || active
  const ready = readiness?.state === 'ready'
  const parameter = (param: WorkflowParameter) => <label key={param.key}>{param.label}<input
    type={param.type === 'integer' ? 'number' : 'text'} min={param.min} max={param.max} step={param.step}
    maxLength={param.type === 'text' ? param.max : undefined}
    value={String(overrides[param.key] ?? param.default ?? '')}
    onChange={e => setOverrides(previous => ({...previous, [param.key]:
      param.type === 'text' ? e.target.value : e.target.value === '' ? param.default : Number(e.target.value)}))}/></label>
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
        <label>提示詞<textarea aria-label="提示詞" maxLength={12000} value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="描述想生成的作品…"/></label>
        {kind === 'music' && <label>歌詞（選填）<textarea maxLength={12000} value={lyrics} onChange={e => setLyrics(e.target.value)}/></label>}
        <div className="parameters">{workflow?.parameters.filter(param => param.basic).map(parameter)}</div>
        <details><summary>進階生成參數</summary><div className="parameters">
          {workflow?.parameters.filter(param => !param.basic).map(parameter)}
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
          readiness.state === 'missing' ? 'ComfyUI 已連線，但缺少必要權重或節點。' : 'ComfyUI 已連線，必要權重與節點齊備。'}</p>
        {readiness?.missing?.map(name => <p className="small pre" key={name}>{name}</p>)}
        {!!readiness?.missing_nodes?.length && <p className="small pre">缺少節點 {readiness.missing_nodes.join('、')}。請更新或啟動受管理的 ComfyUI。</p>}
        <div className="row section-note creation-actions">
          <button className="button" onClick={() => go('runtime')}>管理 ComfyUI</button>
          <button className="button" onClick={() => setRecheck(n => n+1)}>重新檢查</button>
        </div>
        <MediaSetup kind={kind} info={info} port={servicePort} ready={ready} tasks={tasks} run={run} cancel={cancel} retry={retry}
          refresh={() => setRecheck(n => n+1)}/>
        {active && <p className="pre" role="status">{task.message}</p>}
        {active && <button className="button section-note" onClick={() => cancel(task.id)}>停止生成</button>}
        {task?.state === 'failed' && <div className="pre creation-error" role="alert">
          <p>{task.message}</p>
          <p className="small">{/out of memory|memoryerror|cuda.*memory|顯存不足/i.test(task.message) ?
            '可降低尺寸、影片影格數或音樂秒數，再試一次。' : '請先重新檢查 ComfyUI、權重與節點，再用目前設定重試。'}</p>
        </div>}
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
