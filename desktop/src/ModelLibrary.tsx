import { useState, type FormEvent } from 'react'
import { ArrowDownToLine, Check, LoaderCircle, Search, X } from 'lucide-react'
import { rpc, type Info, type Plan, type Task } from './api'
import { activeTask, type Run } from './taskQueue'
import { Empty, Estimate, Panel, gb } from './ui'
import {DeviceChoice} from './DeviceRecommendation'

const verification = {verified: '下載時已核對來源與 SHA-256', known: '已知來源 · 無上游校驗值', imported: '手動匯入', unknown: '來源未知'}

export function ModelLibrary({ info, tasks, run, report, go, refresh }: {
  info?: Info; tasks: Task[]; run: Run; report: (error: unknown) => void; go: (page: 'runtime') => void; refresh: () => Promise<void>
}) {
  const [query, setQuery] = useState('')
  const [found, setFound] = useState<[string, number | null][]>()
  const [repo, setRepo] = useState('')
  const [files, setFiles] = useState<[string, number | null, string][]>()
  const [reading, setReading] = useState(false)
  const [workers, setWorkers] = useState(4)
  const [plan, setPlan] = useState<Plan>()
  const models = info?.models ?? []
  const recommendations = info?.recommended ?? []
  const downloading = (name: string) => tasks.some(task => task.action === 'download' && activeTask(task) && task.title === name.split('/').at(-1))
  const installing = tasks.some(task => task.action === 'engine-install' && activeTask(task))
  const search = async (event: FormEvent) => {
    event.preventDefault(); setReading(true); setFiles(undefined); setRepo(''); setFound(undefined)
    try { setFound(await rpc('search', { query })) } catch (error) { report(error) } finally { setReading(false) }
  }
  const showFiles = async (name: string) => {
    setRepo(name); setFiles(undefined); setReading(true)
    try { setFiles(await rpc('files', {repo: name})) } catch (error) { report(error) } finally { setReading(false) }
  }
  return <>
          <div className="dashboard"><Panel title="本機模型" description={info ? `${info.model_folder} · 可用空間 ${gb(info.hardware.disk_available ?? 0)}` : '正在讀取資料夾'}>
            {!models.length && <Empty>尚未安裝 GGUF。可以從下方推薦或 Hugging Face 搜尋下載。</Empty>}
            {(info?.registry.models ?? []).map(entry => <div key={entry.id}>
              <details><summary>模型運算建議 · {entry.label}</summary><DeviceChoice info={info} task="chat" runtime="local" model={entry.id}/></details>
              <div className="list-row"><span><b>{entry.label}</b><small>{[entry.format, entry.quantization, gb(entry.bytes),entry.context_length ? `Context ${entry.context_length.toLocaleString()}` : null].filter(Boolean).join(" · ")}</small>
                <small>{verification[entry.verification]}</small></span>
                <button className="button" disabled={!info?.engine || reading} onClick={async()=>{setReading(true);try{setPlan(await rpc('plan',{model:entry.id}))}catch(e){report(e)}finally{setReading(false)}}}>估算</button><button className="button" disabled={reading || tasks.some(activeTask)} onClick={async()=>{if(!window.confirm(`永久刪除 ${entry.label}（${gb(entry.bytes)}）？對話與作品將保留。`))return;setReading(true);try{await rpc('model-remove',{model:entry.id,confirmed:true});await refresh()}catch(e){report(e)}finally{setReading(false)}}}>刪除模型</button></div>
              <details className="source-details"><summary>來源與授權</summary>
                <dl>{Object.entries({倉庫:entry.repository, 版本:entry.version, 'SHA-256':entry.sha256,
                  '模型卡授權':entry.license, 下載時間:entry.downloaded}).map(([label,value]) =>
                  <div key={label}><dt>{label}</dt><dd>{value || '未知'}</dd></div>)}</dl>
                {entry.verification === 'unknown' && <button className="button" onClick={async()=> {
                  try {await rpc('model-imported',{model:entry.id}); await refresh()} catch(e) {report(e)}
                }}>標記為手動匯入</button>}
              </details>
            </div>)}
            {plan && <Estimate plan={plan}/>}</Panel>
            <Panel title="引擎與應用"><div className="list-row"><span>llama.cpp <small>{info?.registry.engines.find(engine => engine.id === "llama")?.installed ? '已安裝' : '尚未安裝'}</small></span><button className="button" disabled={!info || installing || info.engine} onClick={()=>run('engine-install',{})}><ArrowDownToLine size={15}/>安裝</button></div>
              <div className="list-row"><span>ComfyUI<small>{info?.comfy_running ? '運行中' : '按需安裝'}</small></span><button className="button" onClick={()=>go('runtime')}>管理</button></div>
              <label>下載執行緒<select value={workers} onChange={e=>setWorkers(Number(e.target.value))}>{[1,2,4,8].map(n=><option key={n}>{n}</option>)}</select></label>
            </Panel></div>
          {!!info?.recoverable_downloads.length && <Panel title="中斷的下載" description="續傳會重新核對來源和已保存的區段。若來源變更，會從頭下載。">
            {info.recoverable_downloads.map(item => <div className="list-row" key={item.url}><span><b>{item.name}</b>
              <small>{Math.floor(item.received / item.total * 100)}% 已保存</small></span>
              <button className="button" disabled={downloading(item.name)} onClick={()=>run('download',{url:item.url,workers})}>續傳</button></div>)}
          </Panel>}
          <Panel title="硬體推薦"><div className="download-list">{recommendations.map(item => <div className="list-row" key={item.repo}><span><b>{item.repo}</b><small>{item.description} · {gb(item.size)}</small></span>
            <span className="tag">{item.fit}</span><button className="button" disabled={downloading(item.name) || models.includes(item.name)} onClick={()=>run('download',{url:item.url,workers})}>
            {models.includes(item.name) ? <Check size={16}/> : <ArrowDownToLine size={16}/>} {models.includes(item.name) ? '已安裝' : '下載'}</button></div>)}</div></Panel>
          <Panel title="Hugging Face 搜尋" description="搜尋公開 GGUF 模型，從固定版本選擇檔案。">
            <form className="row" onSubmit={search}><input className="grow" value={query} onChange={e=>setQuery(e.target.value)} placeholder="輸入模型或作者名稱" aria-label="搜尋模型"/><button className="button primary" disabled={reading}><Search size={16}/>搜尋</button></form>
            {reading && <p className="section-note" role="status"><LoaderCircle className="spin inline" size={16}/> 正在讀取 Hugging Face…</p>}
            {found?.length === 0 && <Empty>沒有符合的公開 GGUF 模型。</Empty>}
            {repo && <p className="section-note"><b>{repo}</b><button className="icon" title="關閉檔案清單" onClick={()=>setRepo('')}><X size={14}/></button></p>}
            {repo && files?.length === 0 && <Empty>沒有可下載的 GGUF 檔案。</Empty>}
            {repo && files?.map(([name,size,url]) => <div className="list-row" key={url}><span>{name}<small>{gb(size)}</small></span><button className="button" disabled={downloading(name) || models.includes(name.split('/').at(-1) || '')} onClick={()=>run('download',{url,workers})}>下載</button></div>)}
            {!repo && found?.map(([name,count]) => <div className="list-row" key={name}><span>{name}<small>{count?.toLocaleString() || '—'} 次下載</small></span><button className="button" disabled={reading} onClick={()=>showFiles(name)}>選擇檔案</button></div>)}
          </Panel>
        </>
}
