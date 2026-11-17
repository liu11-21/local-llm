import {useEffect,useState} from 'react'
import {isWeb,webSession,webPost,logoutWeb} from './transport'

export function WebService(){
 const [state,setState]=useState('正在連線');const [install,setInstall]=useState<Event>()
 useEffect(()=>{
  if(!isWeb)return
  let stopped=false
  const check=()=>webSession().then(()=>{if(!stopped)setState('本機服務已連線')}).catch(()=>{if(!stopped)setState('連線中斷 · 請重新啟動，工作不會重送')})
  const change=(event:Event)=>setState((event as CustomEvent<boolean>).detail?'本機服務已連線':'連線中斷 · 請重新啟動，工作不會重送')
  const prompt=(event:Event)=>{event.preventDefault();setInstall(event)}
  window.addEventListener('workspace-connection',change);window.addEventListener('beforeinstallprompt',prompt)
  void check();const timer=setInterval(()=>void check(),15000)
  return()=>{stopped=true;clearInterval(timer);window.removeEventListener('workspace-connection',change);window.removeEventListener('beforeinstallprompt',prompt)}
 },[])
 if(!isWeb)return null
 return <div className="web-service" role="status"><span>{state}</span><details><summary>服務管理</summary>
  <p>關閉分頁後，背景任務仍可繼續。沒有開啟的分頁時，閒置模型約 90 秒後釋放；30 分鐘無連線會停止服務及未完成工作。</p>
  <p>也可執行 Stop-Web-Workspace.cmd 停止服務。更新請使用 ZIP 更新／回滾腳本。</p>
  <div className="row"><button className="button" onClick={()=>void document.documentElement.requestFullscreen().catch(()=>{})}>全螢幕</button>
   {install&&<button className="button" onClick={()=>{void (install as Event & {prompt:()=>Promise<void>}).prompt();setInstall(undefined)}}>安裝到瀏覽器</button>}
   <button className="button" onClick={()=>{if(confirm('登出目前瀏覽器工作階段？背景工作仍保留。'))void logoutWeb().catch(()=>setState('登出失敗，請確認服務狀態'))}}>登出工作階段</button>
   <button className="button" onClick={async()=>{if(!confirm('停止本機服務並取消未完成工作？'))return;try{await webPost('/api/shutdown',{confirmed:true});setState('本機服務已停止，請使用啟動器重新開啟')}catch{setState('無法連線，請使用 Stop-Web-Workspace.cmd')}}}>停止本機服務</button>
  </div></details></div>
}
