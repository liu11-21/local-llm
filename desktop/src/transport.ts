import {invoke,isTauri} from '@tauri-apps/api/core'

type Data=Record<string,unknown>
export type Reply<T>={ok:true;value:T}|{ok:false;error:string}
interface Transport {request<T>(op:string,data:Data):Promise<Reply<T>>}
export const isWeb=import.meta.env.MODE==='web'
export class DesktopIPCAdapter implements Transport {
 request<T>(op:string,data:Data){return invoke<Reply<T>>('workspace',{op,data})}
}
export class PreviewWorkerAdapter implements Transport {
 async request<T>(op:string,data:Data){const response=await fetch('/__desktop_dev_rpc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({op,data})});if(!response.ok)throw Error('無法連線至本機開發工作程序。');return response.json() as Promise<Reply<T>>}
}
let csrf=''
let connected=false
const notify=(state:boolean)=>{if(connected!==state){connected=state;window.dispatchEvent(new CustomEvent('workspace-connection',{detail:state}))}}
export async function webSession(){
 const response=await fetch('/api/session',{cache:'no-store',credentials:'same-origin'})
 const reply=await response.json()
 if(!response.ok||!reply.ok){notify(false);throw Error(reply.error||'請從 Start-Web-Workspace.cmd 重新開啟工作台。')}
 csrf=reply.value.csrf;notify(true);return reply.value
}
export async function initializeWeb(){
 const fragment=new URLSearchParams(location.hash.slice(1))
 const bootstrap=fragment.get('bootstrap')
 if(bootstrap){
  // Remove the launch credential before React/router/links can observe it.
  history.replaceState(null,'',location.pathname+location.search+'#/home')
  const response=await fetch('/api/session',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Workspace-Bootstrap':bootstrap},body:'{}'})
  if(!response.ok)throw Error('登入失敗，請從啟動器重新開啟。')
 }
 await webSession()
}
const snapshots=new Map<string,Reply<unknown>>()
const streams=new Map<string,EventSource>()
const channel=isWeb&&typeof BroadcastChannel!=='undefined'?new BroadcastChannel('localllm-workspace-change'):undefined
channel?.addEventListener('message',()=>window.dispatchEvent(new Event('workspace-change')))
function streamJob(id:string){
 if(!/^[a-f0-9]{32}$/.test(id)||streams.has(id)||streams.size>=12)return
 const stream=new EventSource('/api/jobs/'+id+'/events');streams.set(id,stream)
 stream.addEventListener('snapshot',event=>{
  const reply=JSON.parse((event as MessageEvent).data) as Reply<{state:string}>
  snapshots.set(id,reply);notify(true)
  if(!reply.ok||!['queued','running','paused'].includes(reply.value.state)){stream.close();streams.delete(id)}
  if(snapshots.size>128)snapshots.delete(snapshots.keys().next().value!)
 })
 stream.onerror=()=>{notify(false);snapshots.delete(id);stream.close();streams.delete(id)}
}
export async function webPost(path:string,data:unknown){
 if(!csrf)await webSession()
 let response:Response
 try{response=await fetch(path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Workspace-CSRF':csrf},body:JSON.stringify(data)});notify(response.ok)}
 catch{notify(false);throw Error('本機服務未連線。請重新啟動；工作未自動重送。')}
 const reply=await response.json()
 if(!response.ok||!reply.ok)throw Error(reply.error||'本機請求失敗。')
 return reply.value
}
export class WebHTTPAdapter implements Transport {
 async request<T>(op:string,data:Data):Promise<Reply<T>>{
  if(op==='job'&&typeof data.id==='string'){
   const cached=snapshots.get(data.id);if(cached)return cached as Reply<T>
   streamJob(data.id)
  }
  try{
   const value=await webPost('/api/rpc',{op,data})
   if(!['info','job','task-list','engine-health','works','system-resources','home-summary','history','build-info'].includes(op))channel?.postMessage('changed')
   return {ok:true,value}
  }catch(error){return {ok:false,error:error instanceof Error?error.message:String(error)}}
 }
}
export const currentTransport:Transport=isTauri()?new DesktopIPCAdapter():isWeb?new WebHTTPAdapter():new PreviewWorkerAdapter()

export async function uploadModel(file:File,progress:(percent:number)=>void){
 const upload=await webPost('/api/uploads/start',{name:file.name,size:file.size})
 try{
  for(let offset=0;offset<file.size;offset+=4*1024**2){
   const chunk=file.slice(offset,offset+4*1024**2)
   const response=await fetch('/api/uploads/'+upload.id,{method:'PUT',credentials:'same-origin',headers:{'Content-Type':'application/octet-stream','X-Workspace-CSRF':csrf,'X-Upload-Offset':String(offset)},body:chunk})
   if(!response.ok)throw Error('匯入中斷；請重試，未覆蓋既有模型。')
   progress(Math.round((offset+chunk.size)/file.size*100))
  }
  return await webPost('/api/uploads/'+upload.id+'/finish',{})
 }catch(error){await webPost('/api/uploads/'+upload.id+'/cancel',{}).catch(()=>{});throw error}
}
