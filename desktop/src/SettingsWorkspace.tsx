import { useState,useEffect } from 'react'
import { rpc } from './api'
import { Panel } from './ui'
import { useWorkspaceUpdates } from './updates'
import type { Run } from './taskQueue'

export function SettingsWorkspace({theme,setTheme,policy,setPolicy,busy,run,report}: {
  theme: string; setTheme: (theme: string) => void; policy: string; setPolicy: (policy: string) => void
  busy: boolean; run: Run; report: (error: unknown) => void
}) {
  const updates = useWorkspaceUpdates()
  const [updateFile, setUpdateFile] = useState<string>()
  const [memory,setMemory]=useState(0)
  const [memoryStatus,setMemoryStatus]=useState('')
  useEffect(()=>{void rpc<{user_limit_mib:number}>('resource-policy').then(value=>setMemory(value.user_limit_mib),report)},[])
  return <div className="dashboard"><Panel title="外觀"><label>色彩模式<select value={theme} onChange={e=>setTheme(e.target.value)}><option value="system">依系統設定</option><option value="dark">深色</option><option value="light">淺色</option></select></label><p className="muted section-note">介面語言：繁體中文</p></Panel>
          <Panel title="運算政策"><label>預設政策<select value={policy} onChange={e=>setPolicy(e.target.value)}><option value="auto">自動（僅本機）</option><option value="local">只用本機</option>
            <option value="privacy">隱私優先</option><option value="manual">手動選擇</option><option value="performance">效能優先（僅本機）</option><option value="cost">成本優先（僅本機）</option></select></label>
            <p className="muted section-note">只有手動選擇已連線端點，並確認當次資料傳送後，才會呼叫外部模型。</p></Panel>
          <Panel title="本機任務記憶體">
            <label>每項隔離任務上限（MiB，0 為依實體 RAM 自動）<input type="number" min={0} max={1048576} value={memory} onChange={e=>setMemory(Number(e.target.value))}/></label>
            <p className="muted small">保留作業系統餘量，依模型與工作空間估計預留；目前資源不足會排隊。提高上限不保證模型能載入。</p>
            <button className="button" onClick={()=>void rpc('resource-policy',{user_limit_mib:memory}).then(()=>setMemoryStatus('已儲存記憶體策略。'),report)}>儲存記憶體上限</button>
            <p className="small" role="status">{memoryStatus}</p>
          </Panel>
          <Panel title="工作台更新">
            <p className="section-note muted">目前版本 {updates.status?.version || '—'} · {
              updates.status?.state === 'available' ? `可下載 ${updates.status.tag}` :
              updates.status?.state === 'current' ? '目前沒有新版' :
              updates.status?.state === 'error' ? updates.status.message : '正在檢查…'}</p>
            <div className="row"><button className="button" disabled={busy || updates.status?.state === 'checking'}
              onClick={() => void updates.check()}>檢查更新</button>
            {updates.status?.tag && <button className="button primary" disabled={busy}
              onClick={async () => setUpdateFile((await run('update-download', { tag: updates.status?.tag }))?.name)}>下載並驗證</button>}</div>
            {updateFile && <><p className="muted section-note">已驗證 {updateFile}。關閉工作台後可執行安裝程式。</p>
              <button className="button" onClick={() => void rpc('update-folder').catch(report)}>開啟更新資料夾</button></>}
          </Panel></div>
}
