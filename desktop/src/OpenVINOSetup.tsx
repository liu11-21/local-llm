import { useEffect, useState } from 'react'
import { rpc, type Info, type Job, type Task } from './api'
import { activeTask, TaskProgress, type Run } from './taskQueue'
import { Panel, gb } from './ui'
import {DeviceChoice} from './DeviceRecommendation'

type RunRecord = {id:string;model:string;created:string;details:{status:string;requested_device?:string;
  execution_devices?:string[];verified_inference?:boolean;fallback?:string;latency_ms?:number}}

export function OpenVINOSetup({info,tasks,run,cancel,openChat}: {
  info?:Info;tasks:Task[];run:Run;cancel:(id:string)=>void;openChat:(id:string)=>void
}) {
  const adapter = info?.openvino
  const [plan,setPlan] = useState<{download_bytes:number;disk_required:number;version:string}>()
  const [confirmed,setConfirmed] = useState(false)
  const [directory,setDirectory] = useState('')
  const [chosen,setChosen] = useState('')
  const [device,setDevice] = useState('CPU')
  const [recommendation,setRecommendation]=useState<string>()
  const [inputs,setInputs] = useState('[[[1,2,3,4]]]')
  const [issue,setIssue] = useState('')
  const [result,setResult] = useState<Job['result']>()
  const [records,setRecords] = useState<RunRecord[]>([])
  const [pending,setPending] = useState(false)
  const active = tasks.find(task=>activeTask(task) && task.action.startsWith('openvino-'))
  const model = adapter?.models.find(model=>model.id===chosen) ?? adapter?.models[0]
  useEffect(()=>setRecommendation(undefined),[model?.id])
  const readRecords = async () => setRecords(await rpc<RunRecord[]>('openvino-runs'))
  useEffect(()=>{
    void rpc<NonNullable<typeof plan>>('openvino-install-plan').then(setPlan).catch(()=>setIssue('無法取得安裝摘要。'))
    void readRecords().catch(()=>setIssue('無法取得推理紀錄。'))
  },[])
  async function start(action:string,data:Record<string,unknown>) {
    setPending(true);setIssue('');setResult(undefined)
    try {setResult(await run(action,data));await readRecords()}
    catch {setIssue('工作尚未完成。請檢查任務中心的診斷。')}
    finally {setPending(false)}
  }
  return <Panel title="可選 OpenVINO 引擎" description="在獨立環境執行相容的 OpenVINO IR 模型。可指定 CPU、Intel GPU 或 Intel NPU，依所選裝置載入驗證。">
    <p className="small">{adapter?.installed ? `已安裝 ${adapter.version}` : '尚未安裝'} ·
      {adapter?.devices.length ? ` 後端回報 ${adapter.devices.join('、')}` : ' 尚未查詢獨立環境的裝置'}</p>
    {!adapter?.installed && plan && <>
      <p className="small">下載 {gb(plan.download_bytes)} · 建議保留 {gb(plan.disk_required)} 空間。模型另行匯入。</p>
      <label className="section-note"><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/>
        我確認下載固定版本的 Python、OpenVINO 與必要依賴</label>
      <button className="button primary section-note" disabled={!confirmed || pending || !!active}
        onClick={()=>void start('openvino-install',{confirmed:true})}>安裝選用 Runtime</button>
    </>}
    {adapter?.installed && <>
      <div className="row creation-actions section-note">
        <button className="button" disabled={pending || !!active} onClick={()=>void start('openvino-detect',{})}>檢查 OpenVINO 裝置</button>
        <button className="button primary" disabled={!adapter.models.some(model=>model.kind==='text') || pending}
          onClick={()=>openChat('openvino')}>使用 OpenVINO 聊天</button>
      </div>
      <details className="section-note"><summary>匯入相容模型</summary>
        <p className="small section-note">選擇既有 OpenVINO IR 資料夾。文字模型需要模型、Tokenizer 與 Detokenizer 的 XML／BIN，以及 config.json。模型會複製到應用程式管理的資料夾並記錄雜湊。</p>
        <label>模型資料夾<input value={directory} onChange={event=>setDirectory(event.target.value)} placeholder="例如 D:\Models\my-openvino-model"/></label>
        <button className="button section-note" disabled={!directory.trim() || pending || !!active}
          onClick={()=>void start('openvino-import',{directory:directory.trim()})}>匯入 OpenVINO IR</button>
      </details>
    </>}
    {!!adapter?.models.length && <details className="section-note"><summary>相容模型與進階推理</summary>
      <label className="section-note">OpenVINO 模型<select aria-label="OpenVINO 模型" value={model?.id} onChange={event=>setChosen(event.target.value)}>
        {adapter.models.map(model=><option value={model.id} key={model.id}>{model.label} · {model.kind==='text' ? '文字' : '張量'}</option>)}
      </select></label>
      <p className="small pre">{model?.architecture} · {model?.format} · {gb(model?.bytes)} · 實際相容性待所選裝置驗證</p>
      {model?.kind==='tensor' && <>
        <DeviceChoice info={info} task="tensor" runtime="openvino" model={model.id} device={device}
          onDevice={value=>{setDevice(value);setRecommendation(undefined)}} onRecommendation={setRecommendation}/>
        <label>推理裝置<select aria-label="推理裝置" value={device} onChange={event=>{setDevice(event.target.value);setRecommendation(undefined)}}>
          {[...new Set(['CPU',...adapter.devices])].map(device=><option key={device}>{device}</option>)}
        </select></label>
        <label>輸入張量 JSON<textarea aria-label="輸入張量 JSON" value={inputs} maxLength={200000} onChange={event=>setInputs(event.target.value)}/></label>
        <button className="button section-note" disabled={pending || !!active} onClick={()=>{
          try {void start('openvino-infer',{model:model.id,device,inputs:JSON.parse(inputs),execution:{device,confirmed:true,recommendation_id:recommendation}})}
          catch {setIssue('請輸入有效的 JSON 陣列。')}
        }}>執行張量推理</button>
      </>}
    </details>}
    {active && <div className="row creation-actions section-note">
      <TaskProgress message={active.message} received={active.received} total={active.total}/>
      <button className="button" onClick={()=>cancel(active.id)}>取消 OpenVINO 工作</button>
    </div>}
    {result?.inference && <pre className="pre section-note">{JSON.stringify(result.inference,null,2)}</pre>}
    <details className="section-note"><summary>實際執行紀錄</summary>
      <p className="small section-note">紀錄只含模型、裝置與執行證據。SQLite 為本機未加密儲存，備份可能保留歷史副本。</p>
      {records.map(record=><article className="remote-peer section-note pre" key={record.id}>
        <b>{record.details.requested_device || '未知裝置'} · {record.details.status}</b>
        <p className="small">實際裝置 {record.details.execution_devices?.join('、') || '未取得算子分配證據'} ·
          {record.details.verified_inference ? ' 指定裝置推理已驗證' : ' 裝置執行待驗證'}</p>
        <p className="small">{record.details.latency_ms!=null ? `${record.details.latency_ms.toFixed(2)} ms · ` : ''}{new Date(record.created).toLocaleString()}</p>
      </article>)}
      <button className="button section-note" onClick={async()=>{
        if(!window.confirm('清除本機 OpenVINO 執行紀錄？備份與磁碟歷史副本可能仍保留資料。')) return
        try {await rpc('openvino-clear-runs',{confirmed:true});await readRecords()}
        catch {setIssue('紀錄清理未完成。')}
      }}>清除推理紀錄</button>
    </details>
    {adapter?.installed && <details className="section-note"><summary>管理 Runtime</summary>
      <button className="button section-note" disabled={pending || !!active} onClick={()=>{
        if(window.confirm('移除 OpenVINO Runtime？已匯入的模型及對話會保留。')) void start('openvino-remove',{confirmed:true})
      }}>移除選用 Runtime</button>
    </details>}
    {issue && <p role="alert" className="small pre section-note">{issue}</p>}
  </Panel>
}
