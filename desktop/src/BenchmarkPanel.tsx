import { useEffect, useState } from 'react'
import { rpc, type Info, type Task } from './api'
import { activeTask, TaskProgress, type Run } from './taskQueue'
import { Panel, gb } from './ui'
import {DeviceChoice} from './DeviceRecommendation'

type Model = {id:string;label:string;engine:string;kind:string;npu_candidate?:boolean}
type Plan = {models:Model[];devices:Record<string,string[]>}
type Summary = {count:number;mean_ms:number;p50_ms:number;p95_ms:number;stddev_ms:number;requests_per_second:number|null}
type Sample = {workload:string;phase:string;latency_ms:number;ttft_ms?:number|null;decode_tokens_per_s?:number|null;
  prefill_tokens_per_s?:number|null;first_text_callback_ms?:number|null;
  input_tokens?:number|null;output_tokens?:number|null;peak_ram_bytes?:number|null;output_correct?:boolean|null;session_cold?:boolean}
type RecordRow = {id:string;model:string;engine:string;state:string;created:string;message?:string}
type Detail = RecordRow & {config:{comparison_key?:string;kind?:string};runs:{id:string;device:string;state:string;error?:string;
  summary:Record<string,Summary>|null;measurements:Sample[];
  environment:{preparation?:{read_model_ms?:number|null;compile_ms?:number|null;pipeline_load_ms?:number|null};
    environment?:{backend_version?:string;mapping?:{state:string;windows_id?:string;driver?:string}}};
  evidence?:{verified_inference?:boolean;execution_devices?:string[];fallback?:string;verification_limit?:string}}[]}
const display = (value:number|null|undefined,unit='ms') => value==null ? '未知' : `${value.toFixed(2)} ${unit}`
const average = (samples:Sample[],key:'ttft_ms'|'decode_tokens_per_s'|'prefill_tokens_per_s'|'first_text_callback_ms') => {
  const values = samples.map(sample=>sample[key]).filter((value):value is number=>typeof value==='number')
  return values.length ? values.reduce((a,b)=>a+b,0)/values.length : null
}
function Results({detail}:{detail:Detail}) {
  return <section className="benchmark-results" aria-label="Benchmark 結果">
    <p className="small pre">{detail.model} · {detail.engine} · {new Date(detail.created).toLocaleString()} · {detail.state}</p>
    {detail.message && <p className="small">{detail.message}</p>}
    {detail.runs.map(run=><div className="benchmark-run" key={run.id}>
      <h3>{run.device} <span className="tag">{run.state}</span></h3>
      {run.error && <p role="alert">{run.error}</p>}
      <p className="small">讀取 {display(run.environment.preparation?.read_model_ms)} · 編譯 {display(run.environment.preparation?.compile_ms)} ·
        Pipeline 載入 {display(run.environment.preparation?.pipeline_load_ms)}</p>
      <p className="small">實際裝置 {run.evidence?.execution_devices?.join('、') || '未知'} ·
        {run.evidence?.verified_inference ? '已驗證推理' : '裝置分配未完整驗證'} · Fallback {run.evidence?.fallback || '未知'}</p>
      <p className="small muted">{run.evidence?.verification_limit} Backend {run.environment.environment?.backend_version || '未知'} · 裝置映射 {run.environment.environment?.mapping?.state || 'unknown'} ·
        驅動 {run.environment.environment?.mapping?.driver || '未知'} · VRAM 峰值未知</p>
      {Object.entries(run.summary ?? {}).map(([workload,summary])=>{
        const samples = run.measurements.filter(sample=>sample.workload===workload && sample.phase==='measured')
        const peaks = samples.flatMap(sample=>sample.peak_ram_bytes==null ? [] : [sample.peak_ram_bytes])
        const first = run.measurements.find(sample=>sample.workload===workload && sample.phase==='first')
        return <div key={workload} className="benchmark-workload">
          <h4>{workload} · {summary?.count ?? 0} 次正式量測</h4>
          {summary && <dl className="benchmark-metrics">
            <div><dt>Warm 平均</dt><dd>{display(summary.mean_ms)}</dd></div>
            <div><dt>P50 / P95</dt><dd>{display(summary.p50_ms)} / {display(summary.p95_ms)}</dd></div>
            <div><dt>標準差</dt><dd>{display(summary.stddev_ms)}</dd></div>
            <div><dt>Throughput</dt><dd>{display(summary.requests_per_second,'req/s')}</dd></div>
            {detail.config.kind!=='tensor' && <>
              <div><dt>TTFT 平均</dt><dd>{display(average(samples,'ttft_ms'))}</dd></div>
              <div><dt>首段文字延遲</dt><dd>{display(average(samples,'first_text_callback_ms'))}</dd></div>
              <div><dt>Prefill 平均</dt><dd>{display(average(samples,'prefill_tokens_per_s'),'token/s')}</dd></div>
              <div><dt>Decode 平均</dt><dd>{display(average(samples,'decode_tokens_per_s'),'token/s')}</dd></div>
            </>}
            <div><dt>程序 RAM 峰值</dt><dd>{peaks.length ? gb(Math.max(...peaks)) : '未知'}</dd></div>
            <div><dt>{first?.session_cold ? 'Cold 首次推理' : '此工作量首次推理'}</dt><dd>{display(first?.latency_ms)}</dd></div>
          </dl>}
          <p className="small">{detail.config.kind!=='tensor' && <>Token 輸入 / 輸出 {samples[0]?.input_tokens ?? '未知'} / {samples[0]?.output_tokens ?? '未知'} · </>}
            正確性 {samples.some(sample=>sample.output_correct===false) ? '不符' : samples.length && samples.every(sample=>sample.output_correct===true) ? '通過參考輸出' : '未提供正確性判準'}</p>
        </div>
      })}
    </div>)}
    <p className="small muted">Cold 使用新程序與空 OpenVINO 編譯快取，作業系統檔案快取未清空。Warm 重用同一模型實例。Prefill 未能分離時保留未知，RAM 為程序工作集峰值，共享記憶體與 VRAM 不相加。</p>
  </section>
}

export function BenchmarkPanel({info,tasks,run,cancel}:{info?:Info;tasks:Task[];run:Run;cancel:(id:string)=>void}) {
  const [plan,setPlan] = useState<Plan>()
  const [chosen,setChosen] = useState('')
  const [devices,setDevices] = useState<string[]>(['CPU'])
  const [advanced,setAdvanced] = useState(false)
  const [warmup,setWarmup] = useState(3)
  const [iterations,setIterations] = useState(10)
  const [timeout,setTimeoutValue] = useState(180)
  const [memory,setMemory] = useState(4096)
  const [tokens,setTokens] = useState(32)
  const [inputs,setInputs] = useState('[{"inputs": [[[1, 2, 3, 4]]]}]')
  const [confirmed,setConfirmed] = useState(false)
  const [pending,setPending] = useState(false)
  const [issue,setIssue] = useState('')
  const [history,setHistory] = useState<RecordRow[]>([])
  const [filter,setFilter] = useState('')
  const [deviceFilter,setDeviceFilter] = useState('')
  const [offset,setOffset] = useState(0)
  const [detail,setDetail] = useState<Detail>()
  const [other,setOther] = useState<Detail>()
  const [comparison,setComparison] = useState<{comparable:boolean;reasons:string[]}>()
  const [exportPath,setExportPath] = useState('')
  const active = tasks.find(task=>task.action==='benchmark' && activeTask(task))
  const model = plan?.models.find(item=>`${item.engine}:${item.id}`===chosen) ?? plan?.models[0]
  const available = model?.engine==='llama.cpp' ? ['CPU',...(info?.devices.map(item=>item[0]) ?? [])] : plan?.devices['openvino'] ?? []
  const load = async () => setPlan(await rpc<Plan>('benchmark-plan'))
  const readHistory = async () => setHistory(await rpc<RecordRow[]>('benchmark-list',{model:filter,device:deviceFilter,offset}))
  const report = (error:unknown) => setIssue(error instanceof Error ? error.message : '無法讀取 Benchmark 資料。')
  useEffect(()=>{void load().catch(report)},[info?.openvino?.detection,info?.openvino?.models.length,info?.models.length])
  useEffect(()=>{void readHistory().catch(report)},[filter,deviceFilter,offset,active?.state])
  useEffect(()=>{setDevices(['CPU']);setConfirmed(false)},[model?.id,model?.engine])
  async function begin() {
    if (!model) return
    setPending(true);setIssue('')
    try {
      await run('benchmark',{engine:model.engine,model:model.id,devices,confirmed,warmup,iterations,timeout,memory_mib:memory,
        max_tokens:tokens,...(model.kind==='tensor' ? {workloads:JSON.parse(inputs)} : {})})
      await readHistory()
    } catch(error) {report(error)} finally {setPending(false)}
  }
  async function inspect(id:string,compare=false) {
    try {
      const record = await rpc<Detail>('benchmark-get',{id})
      if(compare && detail) {
        setOther(record);setComparison(await rpc('benchmark-compare',{left:detail.id,right:id}))
      } else {setDetail(record);setOther(undefined);setComparison(undefined);setExportPath('')}
    } catch(error) {report(error)}
  }
  return <details className="benchmark-section"><summary>進階 · 模型效能測試與歷史</summary>
    <Panel title="測試此模型適合使用哪個設備" description="手動執行固定工作量，保存可追溯的實測結果。不同工作量分開比較，缺少數據時無法確定哪個設備最快。">
      {issue && <p role="alert">{issue}</p>}
      {!plan?.models.length ? <p className="empty">請先下載 GGUF 模型，或在上方匯入 OpenVINO IR。</p> : <>
        <label>測試模型<select aria-label="測試模型" value={model ? `${model.engine}:${model.id}` : ''} disabled={pending} onChange={event=>setChosen(event.target.value)}>
          {plan.models.map(item=><option key={`${item.engine}:${item.id}`} value={`${item.engine}:${item.id}`}>{item.label} · {item.engine}</option>)}
        </select></label>
        <DeviceChoice info={info} task="benchmark" runtime={model?.engine==='openvino' ? 'openvino' : 'local'} model={model?.id ?? ''}/>
        {!available.length && <p className="small">尚未取得可用裝置。請先按上方「檢查 OpenVINO 裝置」。</p>}
        <fieldset className="benchmark-devices"><legend>明確選擇測試裝置</legend>{available.map(device=><label key={device}>
          <input type="checkbox" checked={devices.includes(device)} disabled={pending || device.startsWith('NPU') && model?.kind==='text' && !model.npu_candidate}
            onChange={event=>{setConfirmed(false);setDevices(event.target.checked ? [...devices,device] : devices.filter(item=>item!==device))}}/>{device}
        </label>)}</fieldset>
        <label className="check-row"><input type="checkbox" checked={advanced} onChange={event=>setAdvanced(event.target.checked)}/>顯示進階參數</label>
        {advanced && <div className="benchmark-options">
          {([['Warmup 次數',warmup,setWarmup,0,5],['正式量測次數',iterations,setIterations,2,50],['總時間上限（秒）',timeout,setTimeoutValue,15,600],
            ['程序記憶體上限（MiB）',memory,setMemory,512,8192],['文字輸出 Token',tokens,setTokens,8,128]] as const).map(([label,value,set,min,max])=>
            <label key={label}>{label}<input type="number" value={value} min={min} max={max} disabled={pending} onChange={event=>{setConfirmed(false);set(Number(event.target.value))}}/></label>)}
        </div>}
        {model?.kind==='tensor' && <label>張量工作量 JSON（依模型輸入形狀提供 inputs，可加 expected 參考輸出）
          <textarea value={inputs} rows={4} disabled={pending} onChange={event=>{setInputs(event.target.value);setConfirmed(false)}}/></label>}
        <p className="small">{devices.length} 個裝置依序測試 · 每組工作量 1 次首次推理 + {warmup} 次 Warmup + {iterations} 次正式量測。
          文字使用長、短兩組固定內容。總上限 {timeout} 秒，記憶體上限 {memory} MiB，實際耗時依編譯與模型而變。開始後會排隊等待本機工作結束。</p>
        <p className="small muted">本機執行，不傳送測試內容。溫度、功耗及程序 VRAM 無可靠讀值時顯示未知。請先停止閒置的 ComfyUI 服務。</p>
        <label className="check-row"><input type="checkbox" checked={confirmed} disabled={pending} onChange={event=>setConfirmed(event.target.checked)}/>我確認以上測試負載及資源上限</label>
        <button className="button primary" disabled={!confirmed || pending || !!active || !devices.length || devices.some(device=>!available.includes(device))} onClick={()=>void begin()}>開始 Benchmark</button>
      </>}
      {active && <div className="section-note"><TaskProgress {...active} label="Benchmark 量測進度"/>
        <button className="button" onClick={()=>cancel(active.id)}>取消 Benchmark</button></div>}
    </Panel>
    <Panel title="Benchmark 歷史" description="依日期由新到舊。可比較相同模型、參數與工作量的結果。">
      <div className="benchmark-options"><label>依模型篩選<select value={filter} onChange={event=>{setOffset(0);setFilter(event.target.value)}}><option value="">全部模型</option>
        {plan?.models.map(item=><option key={`${item.engine}:${item.id}`} value={item.id}>{item.label}</option>)}</select></label>
        <label>依設備篩選<input value={deviceFilter} placeholder="例如 CPU、GPU" onChange={event=>{setOffset(0);setDeviceFilter(event.target.value)}}/></label></div>
      {!history.length && <p className="empty">目前沒有符合條件的測試紀錄。</p>}
      {history.map(item=><div className="list-row" key={item.id}><span className="grow"><b>{item.model}</b><small>{new Date(item.created).toLocaleString()} · {item.engine} · {item.state}</small></span>
        <button className="button" onClick={()=>void inspect(item.id)}>檢視</button>
        {detail && <button className="button" disabled={detail.id===item.id} onClick={()=>void inspect(item.id,true)}>比較</button>}
        <button className="button" disabled={['running','queued'].includes(item.state)} onClick={async()=>{
          if(!window.confirm('刪除此 Benchmark 紀錄及原始量測？')) return
          try {await rpc('benchmark-delete',{id:item.id,confirmed:true});await readHistory();if(detail?.id===item.id)setDetail(undefined);setOther(undefined);setComparison(undefined)}catch(error){report(error)}
        }}>刪除</button></div>)}
      <div className="row"><button className="button" disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-20))}>上一頁</button>
        <button className="button" disabled={history.length<20} onClick={()=>setOffset(offset+20)}>下一頁</button></div>
      {comparison && <p role="status">{comparison.comparable ? '設定可比較，請分別核對每組工作量與裝置證據。' : `非完全等價比較 · ${comparison.reasons.join(' ')}`}</p>}
      <div className={other ? 'benchmark-comparison' : ''}>{detail && <Results detail={detail}/>} {other && <Results detail={other}/>}</div>
      {detail && <div className="row">{(['json','csv'] as const).map(format=><button className="button" key={format} onClick={async()=>{
        try {const result = await rpc<{path:string}>('benchmark-export',{id:detail.id,format});setExportPath(result.path)}catch(error){report(error)}
      }}>匯出 {format.toUpperCase()}</button>)}</div>}
      {exportPath && <p className="small pre" role="status">已匯出至 {exportPath}</p>}
    </Panel>
  </details>
}
