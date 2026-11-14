import {useEffect,useState} from 'react'
import {rpc} from './api'
import type {Run} from './taskQueue'
import {Panel} from './ui'

type Trust={sha256:string;source_confirmed:boolean;sha256_verified:boolean;authenticode:{status:string;signer?:string};launch_success:boolean;gpu_identified:boolean;inference_success:boolean;sac:string;version?:string;dependency_scan?:string;dependencies?:{name:string;sha256:string;authenticode:{status:string}}[];code_integrity?:{events:{id:number;files:string[];time:string}[];guidance:string}}
type Status={selected:string;selection:{path?:string;version?:string};discovered:string[];managed_installed:boolean;manifest:{id:string;version:string;sha256:string};trust?:Trust}
export function LlamaRuntimePanel({run,report,refresh}:{run:Run;report:(e:unknown)=>void;refresh:()=>Promise<void>}) {
 const [state,setState]=useState<Status>();const [path,setPath]=useState('');const [busy,setBusy]=useState(false)
 async function load(){const next=await rpc<Status>('runtime-status');setState(next);if(!path)setPath(next.selection.path || next.discovered[0] || '')}
 useEffect(()=>{void load().catch(report)},[])
 async function select(kind:string){setBusy(true);try{await rpc('runtime-select',{kind,path,confirmed:true});await load();await refresh()}catch(e){report(e)}finally{setBusy(false)}}
 async function install(){setBusy(true);try{const result=await run('runtime-install',{confirmed:true});if(result?.path)setPath(result.path);await load();await refresh()}catch(e){report(e)}finally{setBusy(false)}}
 const t=state?.trust
 return <Panel title="文字 Runtime" description="新版 llama.app 與舊版 llama-server 可獨立切換。模型、對話與作品會保留。">
  <div className="row"><span className="tag">{state?.selected==='llama-app' ? 'llama.app · serve' : '相容引擎 · llama-server'}</span><small className="muted">0.8.0 Development</small></div>
  <div className="row section-note"><button className="button primary" disabled={busy} onClick={()=>void install()}>下載官方固定版本 · 約 13 MB</button>
   <button className="button" disabled={busy} onClick={()=>void load().catch(report)}>偵測已安裝版本</button></div>
  <details><summary>選擇引擎與信任證據</summary>
   <label>已安裝的 llama.exe<input value={path} list="llama-installed" placeholder="偵測 PATH／Windows App Alias，或輸入實際位置" onChange={e=>setPath(e.target.value)}/></label>
   <datalist id="llama-installed">{state?.discovered.map(p=><option key={p} value={p}/>)}</datalist>
   <div className="row section-note"><button className="button" disabled={busy || !path} onClick={()=>void select('llama-app')}>檢查並切換新版</button><button className="button" disabled={busy} onClick={()=>void select('legacy')}>使用舊版相容引擎</button>
   <button className="button" disabled={busy || state?.selected!=='llama-app'} onClick={async()=>{try{await run('runtime-audit',{});await load()}catch(e){report(e)}}}>檢查已載入 EXE／DLL 與 3077</button></div>
   <button className="button" onClick={async()=>{try{const diagnostics=await rpc<{events:{id:number;files:string[];time:string}[];guidance:string}>('runtime-diagnostics');setState(current=>current ? {...current,trust:{...(current.trust || {sha256:'',source_confirmed:false,sha256_verified:false,authenticode:{status:'NOT VERIFIED'},launch_success:false,gpu_identified:false,inference_success:false,sac:'NOT VERIFIED'}),code_integrity:diagnostics}} : current)}catch(e){report(e)}}}>讀取近期 3077 診斷（不啟動 Runtime）</button>
   <p className="small muted">切換前請先完成或取消任務。固定套件 {state?.manifest.version}，不執行遠端 PowerShell 安裝腳本。主程式需有效 Hugging Face 簽章。</p>
   {t && <><div className="runtime-trust-grid">{[['來源已確認',t.source_confirmed],['固定 SHA-256 已驗證',t.sha256_verified],['Authenticode Valid',t.authenticode.status==='Valid'],['模型服務啟動成功',t.launch_success],['GPU 裝置已辨識',t.gpu_identified],['實際推理成功',t.inference_success]].map(([label,value])=><div className="list-row" key={String(label)}><span>{label}</span><b>{value ? '已驗證' : '尚未驗證'}</b></div>)}</div>
    <p className="small">Smart App Control：尚未完成獨立實機驗證。簽章有效不代表 SAC 一定放行。</p><p className="small pre">{t.version || state?.selection.version}<br/>SHA-256：{t.sha256}<br/>{t.authenticode.signer}</p>
    <p className="small muted">{t.dependency_scan}</p>{t.dependencies?.map((d,i)=><div className="list-row" key={d.name+i}><span>{d.name}</span><small>{d.authenticode.status}</small></div>)}
    {!!t.code_integrity?.events.length && <div role="alert">近期 3077 事件（須核對是否屬於本 Runtime）：{t.code_integrity.events.map((event,i)=><p className="small pre" key={i}>{event.time}<br/>{event.files.join('\n')}</p>)}請勿停用 SAC 或 Defender。</div>}</>}
  </details>
 </Panel>
}
