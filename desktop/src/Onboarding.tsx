import { useEffect, useRef, useState } from 'react'
import { ArrowRight, Bot, Film, Image, MessageSquare, Music, Users } from 'lucide-react'
import { rpc, type Info, type Job, type Params } from './api'
import { TaskProgress, type Run } from './taskQueue'
import { gb } from './ui'

const uses = [
  ['chat','文字聊天',MessageSquare], ['agent','AI 代理人',Bot], ['team','AI 團隊',Users],
  ['image','圖片生成',Image], ['video','影片生成',Film], ['music','音樂生成',Music],
] as const
export type Use = typeof uses[number][0]
type Stage = 'welcome'|'hardware'|'choose'|'prepare'|'launched'|'completed'|'skipped'
export type Guide = {stage:Stage; task:Use; model?:string; runtime?:string; prepared?:boolean}
type Choice = {runtime:string; label:string; model:string; reason:string; bytes?:number; ram?:number;
  actions:{action:string; data:Params}[]}
const key = 'localllm-onboarding-v1'

export function readGuide(): Guide {
  try {
    const data = JSON.parse(localStorage.getItem(key) || 'null')
    if (uses.some(([id])=>id===data?.task) &&
      ['welcome','hardware','choose','prepare','launched','completed','skipped'].includes(data.stage)) return data
  } catch { /* Treat invalid preferences like first run. */ }
  return {stage:'welcome',task:'chat'}
}

export function saveGuide(guide:Guide) {localStorage.setItem(key,JSON.stringify(guide))}

export function Onboarding({guide, update, close, info, policy, run, cancel, launch, openModels}: {
  guide:Guide; update:(guide:Guide)=>void; close:()=>void; info:Info; policy:string; run:Run;
  cancel:(id:string)=>void; launch:(task:Use, runtime:string, model:string)=>void; openModels:()=>void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [options,setOptions] = useState<Choice[]>()
  const [selected,setSelected] = useState('')
  const [media,setMedia] = useState(false)
  const [busy,setBusy] = useState(false)
  const [job,setJob] = useState<Job>()
  const [error,setError] = useState('')
  const [prepared,setPrepared] = useState(false)
  const [reload,setReload] = useState(0)
  const stop = useRef(false)
  const {stage,task} = guide
  const choice = options?.find(item=>`${item.runtime}:${item.model}`===selected) ?? options?.[0]
  const advance = (next:Stage) => update({...guide,stage:next})
  useEffect(()=>{dialog.current?.showModal()},[])
  useEffect(()=>{
    if (stage!=='prepare') return
    let mounted = true
    setOptions(undefined)
    void rpc<{choices:Choice[];media:boolean}>('onboarding-plan',{task,policy}).then(
      plan=>{if(mounted){setOptions(plan.choices);setMedia(plan.media)}},
      failure=>{if(mounted)setError(failure instanceof Error ? failure.message : String(failure))},
    )
    return ()=>{mounted=false}
  },[stage,task,policy,reload])

  async function prepare() {
    if (!choice || busy) return
    setBusy(true);setError('');stop.current=false
    try {
      for (const step of choice.actions) {
        if (stop.current) return
        setJob(undefined)
        let final: Job | undefined
        let requested = false
        const result = await run(step.action,step.data,next=>{
          final=next;setJob(next)
          if (stop.current && !requested && ['queued','running'].includes(next.state)) {
            requested=true;cancel(next.id)
          }
        })
        if (!result) {
          if (!stop.current) setError(final?.message || '準備尚未完成。請檢查網路與磁碟後重試。')
          setReload(value=>value+1)
          return
        }
      }
      if (!stop.current) {
        setPrepared(true)
        update({...guide,runtime:choice.runtime,model:choice.model,prepared:true})
      }
    } finally {setBusy(false)}
  }

  const ready = prepared || !!choice && choice.actions.length===0
  return <dialog className="transfer-dialog onboarding" ref={dialog} aria-labelledby="guide-title"
    onCancel={event=>{event.preventDefault();if(!busy)close()}}>
    <p className="eyebrow">LOCAL LLM / START</p>
    <h2 id="guide-title">{stage==='completed' ? '第一項任務已完成' : '開始使用 Local LLM'}</h2>
    {stage==='welcome' && <>
      <p className="section-note">先選一項想完成的工作。工作台會檢查這台電腦，並帶你準備模型。</p>
      <button className="button primary" onClick={()=>advance('hardware')}>開始使用 <ArrowRight size={16}/></button>
    </>}
    {stage==='hardware' && <>
      <dl className="guide-hardware">
        <div><dt>CPU 執行緒</dt><dd>{info.hardware.cpu_threads ?? '未知'}</dd></div>
        <div><dt>可用 RAM</dt><dd>{info.hardware.ram_available == null ? '未知' : gb(info.hardware.ram_available)}</dd></div>
        <div><dt>GPU</dt><dd>{info.devices.map(([name])=>name).join('、') || '未取得資料'}</dd></div>
        <div><dt>可用 VRAM</dt><dd>{info.dedicated_vram_available == null ? '未知' : gb(info.dedicated_vram_available)}</dd></div>
        <div><dt>可用磁碟</dt><dd>{info.hardware.disk_available == null ? '未知' : gb(info.hardware.disk_available)}</dd></div>
        <div><dt>文字引擎</dt><dd>{info.engine ? '已安裝' : '待準備'}</dd></div>
      </dl>
      <p className="small section-note">可用 CPU 執行輕量模型。模型需求是估計值，實際載入仍取決於當時可用資源。</p>
      <button className="button primary" onClick={()=>advance('choose')}>選擇用途</button>
    </>}
    {stage==='choose' && <div className="guide-uses">{uses.map(([id,label,Icon])=>
      <button className="button" key={id} onClick={()=>{setSelected('');setPrepared(false);setError('');update({stage:'prepare',task:id})}}>
        <Icon size={17}/>{label}</button>)}</div>}
    {stage==='prepare' && <>
      <p className="section-note">{uses.find(([id])=>id===task)?.[1]} · 選擇模型與運算環境</p>
      {!options && !error && <p role="status">正在檢查可用模型…</p>}
      {options?.length===0 && <p className="small">尚未找到符合目前資源的模型。可檢查空間、瀏覽模型，或先設定遠端電腦。</p>}
      {choice && <>
        <label>推薦模型<select aria-label="入門推薦模型" disabled={busy} value={`${choice.runtime}:${choice.model}`}
          onChange={event=>{setSelected(event.target.value);setPrepared(false);setError('')}}>
          {options?.map(item=><option key={`${item.runtime}:${item.model}`} value={`${item.runtime}:${item.model}`}>{item.label}</option>)}
        </select></label>
        <p className="small section-note">{choice.reason} {choice.bytes && <>權重 {gb(choice.bytes)}。</>}
          {choice.ram && <> RAM 估計 {gb(choice.ram)}。</>}</p>
        {choice.actions.length>0 && !prepared && <p className="small">準備會下載官方引擎或固定版本模型，需要網路。已有本機模型仍可離線使用。</p>}
        {busy && <TaskProgress message={job?.message || '正在準備…'} received={job?.received} total={job?.total}/>}
        <div className="row creation-actions section-note">
          {!ready && <button className="button primary" disabled={busy} onClick={()=>void prepare()}>{error ? '重試準備' : '一鍵準備'}</button>}
          {ready && <button className="button primary" disabled={busy} onClick={()=>launch(task,choice.runtime,choice.model)}>
            {media ? '前往創作並準備權重' : task==='chat' ? '開始第一次聊天' : '開始第一項任務'}</button>}
          {busy && <button className="button" onClick={()=>{stop.current=true;if(job)cancel(job.id)}}>取消準備</button>}
        </div>
      </>}
      {error && <p role="alert" className="pre creation-error">{error}</p>}
      {!busy && <button className="button" onClick={()=>advance('choose')}>更換用途</button>}
    </>}
    {stage==='completed' && <div className="row creation-actions section-note">
      <button className="button primary" onClick={()=>advance('choose')}>開始下一項任務</button>
      <button className="button" onClick={openModels}>查看模型</button>
    </div>}
    <div className="row creation-actions section-note">
      {!busy && <button className="button" onClick={()=>{if(stage!=='completed')advance('skipped');close()}}>
        {stage==='completed' ? '完成' : '略過引導'}</button>}
    </div>
  </dialog>
}
