import {useEffect,useId,useState} from 'react'
import {rpc,type Info} from './api'
import {gb} from './ui'

type Evidence={freshness:string;comparability:string;eligible_for_ranking:boolean;limitations:string[];missing:string[];changed:string[];stale_reasons:string[]}
type Candidate={id:string;runtime:string;device:string;engine:string;model:string;label:string;availability:string;executable:boolean;
  evidence_level:string;confidence:string;network:boolean;needs_consent:boolean;cost:string;reasons:string[];risks:string[];uncertainty:string[];
  resource:{ram_estimate:number|null;vram_estimate:number|null;memory_type:string};performance?:{mean_ms:number;model_start_ms?:number|null;load_ms?:number|null;ttft_ms?:number|null;decode_tokens_per_s?:number|null};
  identity:{driver?:string;backend_version?:string;format?:string;quantization?:string;mapping?:{state:string}};evidence:Evidence[]}
type Result={recommendation_id?:string;recommended:string|null;comparison:unknown;candidates:Candidate[];explanation:string}
const availability:Record<string,string>={ready:'可執行',uncertain:'待確認','needs-setup':'需要準備',incompatible:'不相容'}
const levels:Record<string,string>={'capability-only':'能力資料','verified-benchmark':'已量測並驗證裝置','backend-benchmark-limited':'已量測 Backend，裝置分配有限'}
const preferences={auto:'自動建議',speed:'速度優先','low-memory':'低記憶體',energy:'省電優先',privacy:'隱私優先','local-first':'本機優先',cost:'節省費用'}

export function DeviceChoice({info,task,runtime,model,policy='auto',device='',onDevice,onRuntime,onRecommendation,disabled=false,title='運算建議'}:{
  info?:Info;task:string;runtime:string;model:string;policy?:string;device?:string;onDevice?:(device:string)=>void;
  onRuntime?:(runtime:string)=>void;onRecommendation?:(id:string|undefined)=>void;disabled?:boolean;title?:string
}) {
  const id=useId()
  const [result,setResult]=useState<Result>()
  const [preference,setPreference]=useState('auto')
  const [objective,setObjective]=useState('latency')
  const [workload,setWorkload]=useState('')
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const media=['image','video','music'].includes(task)
  const local=runtime==='local' || runtime==='openvino'
  const devices=runtime==='openvino' ? info?.openvino?.devices ?? [] : ['CPU',...(info?.devices.map(item=>item[0]) ?? [])]
  const npuAllowed=info?.openvino?.models.find(item=>item.id===model)?.npu_candidate
  useEffect(()=>{setResult(undefined);setError('')},[task,runtime,model,policy])
  const selected=result?.candidates.find(item=>item.id===result.recommended)
  async function check() {
    setBusy(true);setError('')
    try {setResult(await rpc('runtime-recommend',{task,model,policy,preference,objective,workload,reference:!!workload}))}
    catch(error){setError(error instanceof Error ? error.message : '推薦資料暫時無法取得。')}
    finally{setBusy(false)}
  }
  function apply(candidate:Candidate) {
    if(candidate.runtime!==runtime && !onRuntime)return
    onRuntime?.(candidate.runtime)
    onDevice?.(candidate.device)
    onRecommendation?.(candidate.id===result?.recommended ? result.recommendation_id : undefined)
  }
  return <section className="device-choice" aria-label={title}>
    {local && !media && onDevice && <label htmlFor={id+'-device'}>執行裝置<select aria-label="執行裝置" id={id+'-device'} value={device} disabled={disabled}
      onChange={event=>onDevice(event.target.value)}>
      <option value="">既有單工作模式</option>{devices.map(value=><option key={value} disabled={value.startsWith('NPU') && task!=='tensor' && task!=='benchmark' && !npuAllowed}>{value}</option>)}
    </select></label>}
    <div className="row section-note"><button type="button" className="button" disabled={disabled || busy || !model} onClick={()=>void check()}>
      {busy ? '檢查證據中…' : '檢查運算建議'}</button>
      <small className="muted">{local ? media ? 'ComfyUI 依已啟動的配置執行，與本機資源預留共用排程。' : '明確選擇設備後，資源允許時可與其他設備任務並行。' : '外部資料傳送仍需本次任務確認。'}</small></div>
    {error && <p role="alert" className="small pre">{error}</p>}
    {selected && <div className="device-suggestion" role="status"><b>{selected.label} · {availability[selected.availability]}</b>
      <p className="small">{selected.reasons.join(' ')}</p><p className="small muted">{levels[selected.evidence_level]} · {selected.uncertainty.slice(0,1).join(' ')}</p>
      {onDevice && selected.executable && !selected.network && <button type="button" className="button" disabled={disabled || selected.runtime!==runtime && !onRuntime}
        onClick={()=>apply(selected)}>採用此裝置</button>}
    </div>}
    {result && !selected && <p role="status" className="small">目前沒有可立即執行的候選，請檢查準備項目或重新選擇模型。</p>}
    <details><summary>推薦偏好與完整證據</summary><div className="device-options">
      <label htmlFor={id+'-preference'}>偏好<select aria-label="推薦偏好" id={id+'-preference'} value={preference} onChange={event=>{setPreference(event.target.value);setResult(undefined)}}>
        {Object.entries(preferences).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      <label htmlFor={id+'-objective'}>效能指標<select aria-label="推薦效能指標" id={id+'-objective'} value={objective} onChange={event=>{setObjective(event.target.value);setResult(undefined)}}>
        <option value="latency">Warm 整體回應延遲</option><option value="cold">模型載入＋首次推理</option><option value="ttft">原生 TTFT</option><option value="decode">Decode Token/s</option></select></label>
      <label htmlFor={id+'-workload'}>參考工作量<select aria-label="推薦參考工作量" id={id+'-workload'} value={workload} onChange={event=>{setWorkload(event.target.value);setResult(undefined)}}>
        <option value="">本次任務條件未知</option><option value="short">固定短文字 · 32 Token</option><option value="long">固定長文字 · 32 Token</option></select></label>
    </div><p className="small muted">固定 Benchmark 只比較指定模型與條件，不能代表您的提示詞、長篇生成或其他模型。選擇參考工作量不會重跑 Benchmark。省電沒有可靠功耗時保留未知。</p>
    {result?.candidates.map(candidate=><article key={candidate.id} className="device-alternative pre">
      <b>{candidate.label} · {availability[candidate.availability]}</b>
      <p className="small">{candidate.reasons.join(' ')} {candidate.risks.join(' ')}</p>
      <p className="small muted">{candidate.uncertainty.join(' ')}</p>
      <p className="small">{candidate.engine} · {candidate.identity.backend_version || '版本未知'} · {candidate.identity.format || '格式未知'} ·
        {candidate.identity.quantization || '量化未知'} · 驅動 {candidate.identity.driver || '未知'} · 映射 {candidate.identity.mapping?.state || 'unknown'}</p>
      <p className="small">RAM 估計 {candidate.resource.ram_estimate==null ? '未知' : gb(candidate.resource.ram_estimate)} ·
        VRAM 估計 {candidate.resource.vram_estimate==null ? '未知' : gb(candidate.resource.vram_estimate)} · {candidate.resource.memory_type} ·
        {candidate.network ? '需傳送確認' : '本機資料'} · {candidate.cost==='unknown' ? '費用未知' : candidate.cost==='may-charge' ? '可能計費' : '無 API 計費'}</p>
      {candidate.performance && <p className="small">固定工作量 Warm 平均 {candidate.performance.mean_ms.toFixed(2)} ms · 載入 {candidate.performance.load_ms?.toFixed(2) ?? '未知'} ms ·
        模型載入＋首推 {candidate.performance.model_start_ms?.toFixed(2) ?? '未知'} ms · TTFT {candidate.performance.ttft_ms?.toFixed(2) ?? '未知'} ms · Decode {candidate.performance.decode_tokens_per_s?.toFixed(2) ?? '未知'} token/s</p>}
      {candidate.evidence.slice(0,3).map((entry,index)=><p className="small" key={index}>{entry.freshness} · {entry.comparability} ·
        {[...entry.changed,...entry.stale_reasons,...entry.missing].join('、')} {entry.limitations.join(' ')}</p>)}
      {onDevice && candidate.executable && !candidate.network && <button type="button" className="button" disabled={disabled || candidate.runtime!==runtime && !onRuntime}
        onClick={()=>apply(candidate)}>改用 {candidate.device}</button>}
    </article>)}</details>
  </section>
}
