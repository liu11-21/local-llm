import {useEffect,useState,type ReactNode} from 'react'
import {currentSessionState,initializeWeb,isWeb,webSession,type SessionState} from './transport'

export function WebSessionGate({children}:{children:ReactNode}){
 const [state,setState]=useState<SessionState>(isWeb?currentSessionState():'ready')
 const [opened,setOpened]=useState(!isWeb)
 useEffect(()=>{
  if(!isWeb)return
  const change=(event:Event)=>{const next=(event as CustomEvent<SessionState>).detail;setState(next);if(next==='ready')setOpened(true)}
  window.addEventListener('workspace-session',change)
  void initializeWeb().catch(()=>setState('reauth'))
  return()=>window.removeEventListener('workspace-session',change)
 },[])
 return <>{opened&&children}{isWeb&&state!=='ready'&&<div className="session-recovery" role="dialog" aria-modal="true" aria-label="恢復工作階段">
  <h2>{state==='logged-out'?'已登出工作階段':state==='checking'?'正在驗證工作階段':'工作階段需要重新連線'}</h2>
  <p>服務重啟或登入逾期後，需要重新驗證。請再次執行 Start-Web-Workspace.cmd；啟動器會開啟目前服務的登入連結，不必清除 Cookie。</p>
  <p>請使用啟動器提供的 127.0.0.1 網址。模型、Runtime、聊天與工作紀錄會保留；未完成的要求不會自動重送。</p>
  <button className="button primary" onClick={()=>void webSession().catch(()=>{})}>重新檢查工作階段</button>
  <p className="small">其他分頁重新登入後，本分頁也會恢復。若服務尚未啟動，請先執行啟動器。</p>
 </div>}</>
}
