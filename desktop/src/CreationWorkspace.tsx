import { useEffect, useState } from 'react'
import { convertFileSrc, isTauri } from '@tauri-apps/api/core'
import { Film, Image, Music2 } from 'lucide-react'
import type { Info, MediaKind, Params, Work } from './api'
import type { Run } from './taskQueue'
import { Empty, Panel, gb } from './ui'

const titles = { image: '圖片', video: '影片', music: '音樂' }
const icons = { image: Image, video: Film, music: Music2 }

function previewPath(info: Info | undefined, work: Work) {
  return info && isTauri() ? convertFileSrc(info.output_folder + '/' + work.name) : undefined
}

export function Works({ info, works, selected, choose, reuse }: {
  info?: Info; works: Work[]; selected?: Work; choose: (work: Work) => void; reuse: (work: Work) => void
}) {
  const work = selected ?? works[0]
  const asset = work ? previewPath(info, work) : undefined
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
      {asset && (work.kind === 'image' ? <img className="media-output" alt="生成作品" src={asset}/> :
        work.kind === 'video' ? <video className="media-output" src={asset} controls/> : <audio src={asset} controls/>)}
      {!asset && <p className="muted section-note">作品可在原生工作台預覽。</p>}
      <p className="section-note">{work.model || titles[work.kind]} · {gb(work.bytes)}</p>
      <p className="small">{info?.output_folder}/{work.name}</p>
      {work.prompt && <details><summary>提示詞和生成設定</summary><p className="pre">{work.prompt}</p>
        <dl>{Object.entries(work.options || {}).filter(([, value]) => value !== null && value !== '').map(([key, value]) =>
          <div className="list-row" key={key}><dt>{key}</dt><dd>{String(value)}</dd></div>)}</dl></details>}
      {work.workflow && <button className="button section-note" onClick={() => reuse(work)}>重新使用設定</button>}
    </>}
  </Panel></div>
}

export function CreationWorkspace({ kind, info, preset, run, go, openWork }: {
  kind: MediaKind; info?: Info; preset?: Work; run: Run; go: (page: 'runtime' | 'works') => void
  openWork: (name: string) => void
}) {
  const [id, setId] = useState('')
  const [prompt, setPrompt] = useState('')
  const [lyrics, setLyrics] = useState('')
  const [overrides, setOverrides] = useState<Params>({})
  const [port, setPort] = useState(8188)
  const [pending, setPending] = useState(false)
  const [result, setResult] = useState<string>()
  const workflows = info?.registry.workflows.filter(item => item.kind === kind) || []
  const workflow = workflows.find(item => item.id === id) ?? workflows[0]
  useEffect(() => {
    if (preset?.kind === kind) {
      setId(preset.workflow ?? ''); setPrompt(preset.prompt ?? ''); setLyrics(preset.lyrics ?? '')
      setOverrides(preset.options ?? {})
    }
  }, [preset, kind])
  return <div className="dashboard creation">
    <Panel title={'建立' + titles[kind]} description="依所選工作流程調整設定。生成工作會加入任務中心。">
      <label>工作流程<select value={workflow?.id ?? ''} disabled={!workflow || pending} onChange={e => {setId(e.target.value);setOverrides({})}}>
        {workflows.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
      </select></label>
      <form onSubmit={async event => {
        event.preventDefault()
        if (!workflow || pending || !prompt.trim()) return
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
          {!info?.comfy_running && <label>本機 ComfyUI 連接埠<input type="number" min={1024} max={65535} value={port} onChange={e => setPort(+e.target.value)}/></label>}
          <ul>{workflow?.models.map(model => <li key={model}>{model}</li>)}</ul>
          <button type="button" className="button section-note" onClick={() => go('runtime')}>管理 ComfyUI</button>
        </details>
        <button className="button primary section-note" disabled={!workflow || pending || !prompt.trim()}>{pending ? '已提交 · 見任務中心' : '生成' + titles[kind]}</button>
      </form>
    </Panel>
    <Panel title="作品預覽">
      {result ? <><p className="section-note">{result}</p><button className="button" onClick={() => openWork(result)}>查看已保存作品</button></> :
        <Empty>作品完成後會加入作品庫。</Empty>}
      <button className="button section-note" onClick={() => go('works')}>開啟作品庫</button>
    </Panel>
  </div>
}
