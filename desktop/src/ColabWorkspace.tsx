import { useEffect, useState, type FormEvent } from 'react'
import { rpc } from './api'

type Colab = {
  available: boolean; project: string; region: string
  templates: { name: string; label: string; machine: string; gpu: string; count: number }[]
}
type NotebookJob = { name: string; label: string; state: string; output: string; created: string }

const states: Record<string, string> = {
  QUEUED: '排隊中', PENDING: '準備中', RUNNING: '執行中', SUCCEEDED: '完成', FAILED: '失敗',
  CANCELLING: '取消中', CANCELLED: '已取消', PAUSED: '已暫停', EXPIRED: '已過期', PARTIALLY_SUCCEEDED: '部分完成',
}

export function ColabWorkspace({ policy, report, onConnectionChange }: {
  policy: string; report: (error: unknown) => void; onConnectionChange: () => Promise<void>
}) {
  const [session, setSession] = useState<Colab>()
  const [project, setProject] = useState('')
  const [region, setRegion] = useState('us-central1')
  const [token, setToken] = useState('')
  const [template, setTemplate] = useState('')
  const [source, setSource] = useState('')
  const [output, setOutput] = useState('')
  const [account, setAccount] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [jobs, setJobs] = useState<NotebookJob[]>([])
  const [accepted, setAccepted] = useState<string>()

  useEffect(() => {
    void rpc<Colab>('colab').then(setSession, report)
  }, [])

  async function connect(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    try {
      const connected = await rpc<Colab>('colab-connect', { project, region, token })
      setSession(connected)
      setToken('')
      setJobs([])
      await onConnectionChange()
    } catch (error) { report(error) }
    finally { setBusy(false) }
  }

  async function refresh() {
    setBusy(true)
    try { setJobs(await rpc('colab-jobs')) }
    catch (error) { report(error) }
    finally { setBusy(false) }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!confirmed) return
    setBusy(true)
    setConfirmed(false)
    setAccepted(undefined)
    try {
      const response = await rpc<{id: string}>('colab-submit', { template, source, output, account, confirmed, policy })
      setAccepted(response.id)
      setJobs(await rpc('colab-jobs'))
    } catch (error) { report(error) }
    finally { setBusy(false) }
  }

  return <section className="panel">
    <h2>Google Colab Enterprise</h2>
    <p className="muted section-note">在自己的 Google Cloud 專案執行既有 Notebook。需要已啟用的 API、執行範本、服務帳戶及 Cloud Storage。</p>
    {!session?.available ? <form onSubmit={connect}>
      <label>Google Cloud 專案 ID<input required value={project} onChange={e => setProject(e.target.value)}/></label>
      <label>區域<input required value={region} onChange={e => setRegion(e.target.value)}/></label>
      <label>OAuth 存取權杖<input required type="password" autoComplete="off" value={token}
        onChange={e => setToken(e.target.value)}/></label>
      <p className="small muted">可使用自己帳戶取得的 `gcloud auth print-access-token`。權杖只保留在這次工作階段。</p>
      <button className="button section-note" disabled={busy}>連線並讀取範本</button>
    </form> : <>
      <div className="row section-note"><span>{session.project} · {session.region}</span>
        <button className="button" disabled={busy} onClick={refresh}>重新整理工作</button>
        <button className="button" disabled={busy} onClick={async () => {
          try {
            setSession(await rpc('colab-disconnect'))
            await onConnectionChange()
            setJobs([]); setTemplate(''); setConfirmed(false); setAccepted(undefined)
          } catch (error) { report(error) }
        }}>中斷連線</button>
      </div>
      <form onSubmit={submit}>
        <label>執行範本<select required value={template} onChange={e => { setTemplate(e.target.value); setConfirmed(false) }}>
          <option value="">選擇範本</option>
          {session.templates.map(item => <option key={item.name} value={item.name}>
            {item.label} · {item.machine || '未標示機型'}{item.count ? ` · ${item.count} × ${item.gpu}` : ''}
          </option>)}
        </select></label>
        {!session.templates.length && <p className="empty">這個區域沒有可讀取的執行範本。</p>}
        <label>Notebook 網址<input required placeholder="gs://bucket/notebook.ipynb" value={source}
          onChange={e => { setSource(e.target.value); setConfirmed(false) }}/></label>
        <label>輸出 bucket<input required placeholder="gs://bucket" value={output}
          onChange={e => { setOutput(e.target.value); setConfirmed(false) }}/></label>
        <label>服務帳戶<input required placeholder="runner@project.iam.gserviceaccount.com" value={account}
          onChange={e => { setAccount(e.target.value); setConfirmed(false) }}/></label>
        <label className="check section-note"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/>
          我核准用此身分執行 Notebook，並同意可能產生的 Google Cloud 費用。</label>
        {policy !== 'manual' && <p className="muted section-note">請先在設定把運算政策切換為手動選擇。</p>}
        <button className="button primary" disabled={busy || !confirmed || !template || policy !== 'manual'}>
          提交 Notebook（執行上限 15 分鐘）</button>
      </form>
      {accepted && <p className="section-note" role="status">Google 已接受提交：{accepted}。可重新整理查詢狀態。</p>}
      {jobs.map(job => <div key={job.name} className="list-row"><span>
        <strong>{job.label || job.name}</strong><small>{job.output}</small></span>
        <span>{states[job.state?.replace('JOB_STATE_', '')] || job.state || '未知'}</span>
      </div>)}
      <p className="small muted section-note">已提交的工作在 Google Cloud 執行；關閉或中斷工作台不會停止它。可在 Google Cloud 主控台查看結果。</p>
    </>}
  </section>
}
