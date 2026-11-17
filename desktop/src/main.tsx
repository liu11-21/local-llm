import { createRoot } from 'react-dom/client'
import { App } from './App'
import { TaskPreparationProvider } from './TaskPreparation'
import './style.css'
import './workspace.css'
import {WebSessionGate} from './WebSessionGate'

async function start(){
 createRoot(document.getElementById('root')!).render(<WebSessionGate><TaskPreparationProvider><App/></TaskPreparationProvider></WebSessionGate>)
}
void start().catch(error=>{const root=document.getElementById('root')!;const p=document.createElement('p');p.className='section-note';p.textContent=String(error)+' 請以 Start-Web-Workspace.cmd 啟動，勿直接開啟 HTML 檔案。';root.append(p)})
