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
export type SessionState='checking'|'ready'|'reauth'|'offline'|'logged-out'
let sessionState:SessionState='checking'
let authEpoch=0
let refreshRequest:Promise<any>|undefined
let launchRequest:Promise<void>|undefined
let listening=false
const snapshots=new Map<string,Reply<unknown>>()
const streams=new Map<string,EventSource>()
const wanted=new Set<string>()
const retries=new Map<string,ReturnType<typeof setTimeout>>()
const channel=isWeb&&typeof BroadcastChannel!=='undefined'?new BroadcastChannel('localllm-workspace-change'):undefined
export const currentSessionState=()=>sessionState
const notify=(state:boolean)=>{if(connected!==state){connected=state;window.dispatchEvent(new CustomEvent('workspace-connection',{detail:state}))}}
function sessionStatus(state:SessionState){sessionState=state;notify(state==='ready');window.dispatchEvent(new CustomEvent('workspace-session',{detail:state}))}
function clearStreams(){for(const stream of streams.values())stream.close();streams.clear();snapshots.clear();for(const timer of retries.values())clearTimeout(timer);retries.clear()}
function invalidate(state:SessionState){csrf='';clearStreams();sessionStatus(state)}
function canonicalOrigin(){if(location.protocol!=='http:'||location.hostname!=='127.0.0.1')throw Error('請使用啟動器提供的 http://127.0.0.1 網址，勿混用 localhost 或直接開啟 HTML。')}
export function webSession():Promise<any>{
 if(refreshRequest)return refreshRequest
 const epoch=authEpoch
 const request=(async()=>{
  canonicalOrigin()
  let response:Response
  try{response=await fetch('/api/session',{cache:'no-store',credentials:'same-origin'})}
  catch(error){if(epoch===authEpoch)sessionStatus('offline');throw error}
  const reply=await response.json()
  if(!response.ok||!reply.ok){if(epoch===authEpoch)invalidate(response.status===401?'reauth':'offline');throw Error(reply.error||'請再次執行 Start-Web-Workspace.cmd 重新驗證。')}
  if(epoch===authEpoch){const recovered=sessionState!=='ready';csrf=reply.value.csrf;sessionStatus('ready');if(recovered){window.dispatchEvent(new Event('workspace-change'));for(const id of wanted)streamJob(id)}}
  return reply.value
 })()
 refreshRequest=request
 void request.finally(()=>{if(refreshRequest===request)refreshRequest=undefined}).catch(()=>{})
 return request
}
async function consumeLaunch(){
 const fragment=new URLSearchParams(location.hash.slice(1))
 const bootstrap=fragment.get('bootstrap')
 if(!bootstrap)return
 // Consume the launch credential from the URL; never store, broadcast or log it.
 history.replaceState(null,'',location.pathname+location.search+'#/home')
 canonicalOrigin();authEpoch++;invalidate('checking')
 const previous=refreshRequest;refreshRequest=undefined
 if(previous)await previous.catch(()=>{})
 const response=await fetch('/api/session',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Workspace-Bootstrap':bootstrap},body:'{}'})
 if(!response.ok){invalidate('reauth');throw Error('登入連結已失效，請再次執行 Start-Web-Workspace.cmd。')}
 await webSession()
 channel?.postMessage('session-ready')
}
export async function initializeWeb(){
 if(!listening){listening=true;window.addEventListener('hashchange',()=>{
  if(new URLSearchParams(location.hash.slice(1)).has('bootstrap'))void initializeWeb().catch(()=>invalidate('reauth'))
 })}
 if(new URLSearchParams(location.hash.slice(1)).has('bootstrap')){
  if(!launchRequest){launchRequest=consumeLaunch().finally(()=>{launchRequest=undefined})}
  await launchRequest
 }else await webSession()
 if('serviceWorker' in navigator)void navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).catch(()=>{})
}
channel?.addEventListener('message',event=>{
 if(event.data==='session-logout'){authEpoch++;wanted.clear();invalidate('logged-out')}
 else if(event.data==='session-ready')void webSession().catch(()=>{})
 else window.dispatchEvent(new Event('workspace-change'))
})
export async function logoutWeb(){await webPost('/api/logout',{confirmed:true});authEpoch++;wanted.clear();invalidate('logged-out');channel?.postMessage('session-logout')}
function streamJob(id:string){
 if(!/^[a-f0-9]{32}$/.test(id)||streams.has(id)||streams.size>=12)return
 wanted.add(id)
 if(sessionState!=='ready')return
 const stream=new EventSource('/api/jobs/'+id+'/events');streams.set(id,stream)
 stream.addEventListener('snapshot',event=>{
  const reply=JSON.parse((event as MessageEvent).data) as Reply<{state:string}>
  snapshots.set(id,reply);notify(true)
  if(!reply.ok||!['queued','running','paused'].includes(reply.value.state)){stream.close();streams.delete(id);wanted.delete(id)}
  if(snapshots.size>128)snapshots.delete(snapshots.keys().next().value!)
 })
 stream.onerror=()=>{notify(false);snapshots.delete(id);stream.close();streams.delete(id)
  if(!retries.has(id))retries.set(id,setTimeout(()=>{retries.delete(id);void webSession().then(()=>streamJob(id)).catch(()=>{})},1500))
 }
}
export async function webPost(path:string,data:unknown){
 if(!csrf)await webSession()
 let response:Response
 try{response=await fetch(path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Workspace-CSRF':csrf},body:JSON.stringify(data)});notify(response.ok)}
 catch{notify(false);throw Error('本機服務未連線。請重新啟動；工作未自動重送。')}
 const reply=await response.json()
 if(response.status===401)invalidate('reauth')
 if(response.status===403&&reply.code==='CSRF_INVALID'){
  await webSession().catch(()=>{});throw Error('工作階段已更新，請重新操作；原要求沒有重送。')
 }
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
  const result=await webPost('/api/uploads/'+upload.id+'/finish',{});channel?.postMessage('changed');return result
 }catch(error){await webPost('/api/uploads/'+upload.id+'/cancel',{}).catch(()=>{});throw error}
}
