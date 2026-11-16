import {useEffect,useState} from 'react'
import {rpc,APP_VERSION} from './api'
import {isWeb} from './transport'
import type {Run} from './taskQueue'
import {Panel} from './ui'

type Trust={path?:string;resolved_image?:{path:string;sha256?:string;authenticode?:{status:string}};child_images?:{path:string;sha256?:string;authenticode?:{status:string}}[];sha256:string;source_confirmed:boolean;sha256_verified:boolean;authenticode:{status:string;signer?:string};launch_success:boolean;gpu_identified:boolean;inference_success:boolean;sac:string;version?:string;dependency_scan?:string;dependencies?:{name:string;sha256:string;authenticode:{status:string}}[];code_integrity?:{events:{id:number;files:string[];time:string}[];guidance:string}}
type Candidate={id:string;input_path:string;input_paths:string[];path:string|null;exists:boolean;state:'found'|'verifying'|'verified'|'unsupported'|'failed'|'selected'|'running';verified:boolean;selected:boolean;version:string|null;authenticode:{status:string;signer?:string};reason?:{code:string;message:string};sources:string[];trace:unknown[];probes:unknown[]}
type Status={schema?:number;candidates?:Candidate[];scan?:{state:string;searched:number;attempts:unknown[];errors:unknown[];error?:{code:string;message:string};truncated?:boolean};selected:string;selection:{path?:string;version?:string;devices?:{id:string;name:string;backend:string;available:boolean;memory_type:string;reported_total_mib:number;reported_free_mib:number}[]};discovered:string[];managed_installed:boolean;manifest:{id:string;version:string;sha256:string};trust?:Trust}
const labels={found:'已找到',verifying:'簽章／相容性驗證中',verified:'已驗證 · 尚未選取',unsupported:'不受支援',failed:'驗證失敗',selected:'已選取',running:'執行中'}
export function LlamaRuntimePanel({run,report,refresh}:{run:Run;report:(e:unknown)=>void;refresh:()=>Promise<void>}) {
 const [state,setState]=useState<Status>();const [path,setPath]=useState('');const [busy,setBusy]=useState(false)
 function apply(next:Status){setState(next);setPath(current=>current || next.selection.path || next.candidates?.find(row=>row.verified)?.path || next.discovered[0] || '')}
 async function load(auto=false){let next=await rpc<Status>('runtime-status');if(auto&&next.scan?.state==='not_detected')next=await rpc<Status>('runtime-discover');apply(next)}
 useEffect(()=>{void load(true).catch(report)},[])
 useEffect(()=>{if(state?.scan?.state!=='scanning')return;const timer=setInterval(()=>void load().catch(report),700);return()=>clearInterval(timer)},[state?.scan?.state])
 async function select(kind:string,selectedPath=path){setBusy(true);try{apply(await rpc<Status>('runtime-select',{kind,path:selectedPath,confirmed:true}));await refresh()}catch(e){report(e);await load().catch(report)}finally{setBusy(false)}}
 async function detect(){try{apply(await rpc<Status>('runtime-discover'))}catch(error){report(error)}}
 async function verify(selectedPath:string){setBusy(true);try{apply(await rpc<Status>('runtime-validate',{path:selectedPath}))}catch(error){report(error)}finally{setBusy(false)}}
 async function pick(){setBusy(true);try{const result=await rpc<{cancelled:boolean;status:Status}>('runtime-pick',{confirmed:true});apply(result.status);if(!result.cancelled){const row=result.status.candidates?.at(-1);if(row)setPath(row.path||row.input_path)}}catch(error){report(error)}finally{setBusy(false)}}
 async function install(){setBusy(true);try{const result=await run('runtime-install',{confirmed:true});if(result?.path)setPath(result.path);await load();await refresh()}catch(e){report(e)}finally{setBusy(false)}}
 const t=state?.trust
 return <Panel title="文字 Runtime" description="先偵測已安裝的官方 llama.exe；無需重新下載。驗證、選取與模型準備分開，模型、對話與作品會保留。">
  <div className="row"><span className="tag">{state?.selected==='llama-app' ? 'llama.app · serve' : isWeb?'請選擇官方 llama.exe':'相容引擎 · llama-server'}</span><small className="muted">{APP_VERSION} Development</small></div>
  <div className="row section-note"><button className="button primary" disabled={busy||state?.scan?.state==='scanning'} onClick={()=>void detect()}>偵測已安裝版本</button>
   <button className="button" disabled={busy} onClick={()=>void pick()}>選擇既有 llama.exe 檔案</button>
   <button className="button" disabled={busy} onClick={()=>void install()}>下載官方固定版本 · 約 13 MB</button></div>
  <section aria-label="已安裝的 Runtime" className="section-note">
   {state?.scan?.state==='scanning'&&<p role="status">正在偵測／驗證既有 Runtime；不下載檔案，也不載入模型。</p>}
   {(!state?.scan||state.scan.state==='not_detected')&&!state?.candidates?.length&&<p>尚未偵測。可偵測 PATH，或選擇已安裝的檔案。</p>}
   {state?.scan?.state==='complete'&&!state.candidates?.length&&<p role="status">未找到既有 llama.exe。已檢查 {state.scan.searched} 個位置；可選擇既有檔案，不必重新下載。</p>}
   {state?.scan?.error&&<p role="alert">{state.scan.error.code} · {state.scan.error.message}</p>}
   {state?.candidates?.map(row=><article className="runtime-candidate" aria-label={`Runtime 候選 ${row.id}`} key={row.id} aria-busy={row.state==='verifying'}>
    <div className="list-row"><span><b>llama.exe</b><small>{row.version||'尚未取得版本'}</small></span><span className="tag">{labels[row.state]}</span></div>
    <p className="small pre">{row.path||row.input_path}</p><p className="small">簽章：{row.authenticode.status} {row.authenticode.signer||''}</p>
    {row.reason&&<p role="alert">{row.reason.code} · {row.reason.message}</p>}
    <div className="row">{row.verified?<button className="button" disabled={busy||row.selected} aria-pressed={row.selected} onClick={()=>void select('llama-app',row.path||row.input_path)}>{row.selected?'已選取':'選取此 Runtime'}</button>:<button className="button" disabled={busy||row.state==='verifying'} onClick={()=>void verify(row.input_path)}>驗證此版本</button>}
    <details><summary>偵測路徑與驗證記錄</summary><pre className="small pre">{JSON.stringify({input_paths:row.input_paths,resolved_path:row.path,exists:row.exists,sources:row.sources,trace:row.trace},null,2)}</pre></details></div>
   </article>)}
   {state?.selected==='llama-app'&&<p>已選取：{state.selection.path}。Runtime 已設定；尚未下載模型時，請到模型庫準備 GGUF。硬體辨識與推理成功是另外的驗收。</p>}
   {state?.scan&&<details><summary>完整掃描診斷</summary><pre className="small pre">{JSON.stringify(state.scan,null,2)}</pre></details>}
  </section>
  {state?.selected==='llama-app' && state.selection.devices?.map(device=><div className="list-row" key={device.id}><span style={{overflowWrap:'anywhere'}}><b>{device.id} · {device.name}</b><small>{device.backend} · {device.available ? 'Runtime 已辨識' : '尚未通過實機驗證，不可用'}</small><small>偵測時可用 {device.reported_free_mib.toLocaleString()} / {device.reported_total_mib.toLocaleString()} MiB · {device.memory_type==='shared-or-unified' ? '共享／統一記憶體，非獨立顯存' : '需對照實體記憶體；不是可直接加總的顯存'}</small></span></div>)}
  <details><summary>選擇引擎與信任證據</summary>
   <label>已安裝的 llama.exe<input value={path} list="llama-installed" placeholder="偵測 PATH／Windows App Alias，或輸入實際位置" onChange={e=>setPath(e.target.value)}/></label>
   <datalist id="llama-installed">{state?.discovered.map(p=><option key={p} value={p}/>)}</datalist>
   <div className="row section-note"><button className="button" disabled={busy || !path} onClick={()=>void select('llama-app')}>檢查並切換新版</button>{!isWeb&&<button className="button" disabled={busy} onClick={()=>void select('legacy')}>使用舊版相容引擎</button>}
   <button className="button" disabled={busy || state?.selected!=='llama-app'} onClick={async()=>{try{await run('runtime-audit',{});await load()}catch(e){report(e)}}}>檢查已載入 EXE／DLL 與 3077</button></div>
   <button className="button" onClick={async()=>{try{const diagnostics=await rpc<{events:{id:number;files:string[];time:string}[];guidance:string}>('runtime-diagnostics');setState(current=>current ? {...current,trust:{...(current.trust || {sha256:'',source_confirmed:false,sha256_verified:false,authenticode:{status:'NOT VERIFIED'},launch_success:false,gpu_identified:false,inference_success:false,sac:'NOT VERIFIED'}),code_integrity:diagnostics}} : current)}catch(e){report(e)}}}>讀取近期 3077 診斷（不啟動 Runtime）</button>
   <p className="small muted">切換前請先完成或取消任務。固定套件 {state?.manifest.version}，不執行遠端 PowerShell 安裝腳本。主程式需有效 Hugging Face 簽章。</p>
   {t && <><p className="small pre">受檢檔案：{t.path || '受控測試資料'}</p><div className="runtime-trust-grid">{[['來源已確認',t.source_confirmed],['固定 SHA-256 已驗證',t.sha256_verified],['Authenticode Valid',t.authenticode.status==='Valid'],['模型服務啟動成功',t.launch_success],['GPU 裝置已辨識',t.gpu_identified],['實際推理成功',t.inference_success]].map(([label,value])=><div className="list-row" key={String(label)}><span>{label}</span><b>{value ? '已驗證' : '尚未驗證'}</b></div>)}</div>
    <p className="small">Smart App Control：尚未完成獨立實機驗證。簽章有效不代表 SAC 一定放行。</p><p className="small pre">{t.version || state?.selection.version}<br/>SHA-256：{t.sha256}<br/>{t.authenticode.signer}</p>
    {t.resolved_image && <p className="small pre">實際主程序：{t.resolved_image.path}<br/>SHA-256：{t.resolved_image.sha256 || 'NOT VERIFIED'} · {t.resolved_image.authenticode?.status || 'NOT VERIFIED'}</p>}
    {t.child_images?.map((child,i)=><p className="small pre" key={i}>子程序：{child.path}<br/>SHA-256：{child.sha256 || 'NOT VERIFIED'} · {child.authenticode?.status || 'NOT VERIFIED'}</p>)}
    <p className="small muted">{t.dependency_scan}</p>{t.dependencies?.map((d,i)=><div className="list-row" key={d.name+i}><span>{d.name}</span><small>{d.authenticode.status}</small></div>)}
    {!!t.code_integrity?.events.length && <div role="alert">近期 3077 事件（須核對是否屬於本 Runtime）：{t.code_integrity.events.map((event,i)=><p className="small pre" key={i}>{event.time}<br/>{event.files.join('\n')}</p>)}請勿停用 SAC 或 Defender。</div>}</>}
  </details>
 </Panel>
}
