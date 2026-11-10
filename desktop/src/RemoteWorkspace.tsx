import { useEffect, useState } from 'react'
import { rpc, type Info } from './api'
import { Empty, Panel, gb } from './ui'

type Host = {
  state: 'stopped' | 'starting' | 'ready' | 'busy' | 'unhealthy' | 'stopping' | 'failed'
  error?: string; label?: string; address?: string; port?: number; models?: string[]
  peers: {id:string; label:string}[]
  engine?: {installed:boolean; accepting:boolean; busy:boolean; error?:string; engine_state:string}
}
const states = {stopped:'已停止', starting:'啟動中', ready:'分享中', busy:'忙碌', unhealthy:'異常',
  stopping:'停止中', failed:'啟動失敗'}

export function RemoteWorkspace({info, refresh, openChat}: {info?:Info; refresh:()=>Promise<void>; openChat:(id:string)=>void}) {
  const [host, setHost] = useState<Host>()
  const [issue, setIssue] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [name, setName] = useState('我的運算主機')
  const [address, setAddress] = useState('')
  const [port, setPort] = useState(9443)
  const [certificate, setCertificate] = useState('')
  const [keyFile, setKeyFile] = useState('')
  const [invite, setInvite] = useState('')
  const [code, setCode] = useState('')
  const [device, setDevice] = useState('我的筆電')
  const [recoveryHost, setRecoveryHost] = useState('')
  const [request, setRequest] = useState('')
  const [recovered, setRecovered] = useState<{state:string; answer?:string; message?:string}>()
  const peers = info?.providers.filter(item => item.kind === 'paired') ?? []
  const running = !!host?.address

  useEffect(() => {
    let mounted = true
    const check = () => void rpc<Host>('remote-host-status').then(
      value => {if (mounted) setHost(value)},
      error => {if (mounted) setIssue(error instanceof Error ? error.message : String(error))},
    )
    check()
    const timer = window.setInterval(check, 2200)
    return () => { mounted = false; window.clearInterval(timer) }
  }, [])

  async function change(action: () => Promise<void>) {
    setBusy(true); setIssue(''); setNote('')
    try { await action() }
    catch (error) {setIssue(error instanceof Error ? error.message : String(error))}
    finally {setBusy(false)}
  }

  return <div className="dashboard">
    <Panel title="連接我的遠端電腦" description="在高效能電腦建立邀請，再透過信任的管道複製到這台電腦。">
      <form className="runtime-endpoint" onSubmit={event => {
        event.preventDefault()
        if (!window.confirm('確認邀請由您信任的運算主機直接提供？')) return
        void change(async () => {
          await rpc('remote-client-pair', {invite:code, label:device, confirmed:true})
          setCode(''); setNote('已配對。請在聊天選擇這台主機。'); await refresh()
        })
      }}>
        <label>這台裝置的名稱<input required value={device} maxLength={80} onChange={e=>setDevice(e.target.value)}/></label>
        <label>主機配對邀請<textarea aria-label="主機配對邀請" required autoComplete="off" spellCheck={false} value={code}
          maxLength={24576} onChange={e=>setCode(e.target.value)} placeholder="貼上主機提供的完整邀請"/></label>
        <button className="button primary" disabled={busy}>{busy ? '處理中…' : '配對主機'}</button>
      </form>
      {!peers.length && <Empty>尚未配對遠端電腦。</Empty>}
      {peers.map(peer => {
        const cap = peer.capability
        return <article key={peer.id} className="section-note remote-peer">
          <strong className="pre">{peer.label}</strong>
          <p className="small pre">{peer.host}:{peer.port} · {peer.connected ? '已連線' : '尚未連線'} · 文字聊天 · {peer.models.length} 個模型</p>
          <p className="small pre">RAM 可用 {cap?.resources.ram_available?.value != null ? gb(Number(cap.resources.ram_available.value)) : '未知'} ·
            GPU {Array.isArray(cap?.resources.gpus?.value) ? cap.resources.gpus.value.join('、') : '未知'} · 無 API 計費</p>
          {cap?.error && <p className="small pre creation-error">{cap.error}</p>}
          {!!peer.models.length && <details><summary>可用模型</summary><ul className="pre">{peer.models.map(model => <li key={model}>{model}</li>)}</ul></details>}
          <div className="row creation-actions section-note">
            <button className="button" disabled={busy} onClick={() => void change(async () => {
              try {await rpc('remote-client-refresh',{id:peer.id});setNote('已更新主機能力。')}
              finally {await refresh()}
            })}>重新連線</button>
            <button className="button" disabled={!peer.connected || !peer.models.length || busy} onClick={()=>openChat(peer.id)}>開始聊天</button>
            <button className="button" disabled={busy} onClick={() => {
              if (!window.confirm('移除此主機的配對？')) return
              void change(async () => {
                const result = await rpc<{revoked:boolean}>('remote-client-remove',{id:peer.id})
                setNote(result.revoked ? '已解除配對。' : '已移除本機設定。請在主機撤銷該裝置。');await refresh()
              })
            }}>移除配對</button>
          </div>
        </article>
      })}
      {!!peers.length && <details className="section-note"><summary>查詢中斷的遠端任務</summary>
        <form onSubmit={event => {
          event.preventDefault()
          setRecovered(undefined)
          void change(async () => setRecovered(await rpc('remote-client-job',{id:recoveryHost || peers[0].id, request})))
        }}>
          <label>主機<select value={recoveryHost || peers[0].id} onChange={e=>setRecoveryHost(e.target.value)}>
            {peers.map(peer=><option key={peer.id} value={peer.id}>{peer.label}</option>)}
          </select></label>
          <label>遠端任務識別碼<input required maxLength={32} value={request} onChange={e=>setRequest(e.target.value)}/></label>
          <button className="button section-note" disabled={busy}>查詢任務</button>
        </form>
        {recovered && <div role="status" className="pre"><p>{recovered.state} · {recovered.message}</p><p>{recovered.answer}</p></div>}
      </details>}
    </Panel>
    <Panel title="將此電腦設為運算主機" description="允許已配對裝置在私人網路使用這台電腦的文字模型。">
      <p className="section-note" role="status">{host ? states[host.state] : '正在讀取主機狀態…'}</p>
      {host?.error && <p className="pre creation-error">{host.error}</p>}
      {!running && <form onSubmit={event => {
        event.preventDefault()
        if (!window.confirm('允許在指定私人網路位址分享本機文字模型？')) return
        void change(async () => {
          setHost(await rpc('remote-host-start',{label:name, address, port, certificate, key_file:keyFile, confirmed:true}))
          setKeyFile('')
        })
      }}>
        <label>主機名稱<input required maxLength={100} value={name} onChange={e=>setName(e.target.value)}/></label>
        <label>本機私人 IPv4 位址<input required value={address} placeholder="192.168.1.20" onChange={e=>setAddress(e.target.value)}/></label>
        <details open className="section-note"><summary>進階 TLS 設定</summary>
          <label>HTTPS 連接埠<input required type="number" min={1024} max={65535} value={port} onChange={e=>setPort(+e.target.value)}/></label>
          <label>公開 PEM 憑證路徑<input required value={certificate} onChange={e=>setCertificate(e.target.value)}/></label>
          <label>PEM 私鑰路徑<input required value={keyFile} onChange={e=>setKeyFile(e.target.value)}/></label>
          <p className="small pre">憑證必須包含上面的私人 IP。由您信任的管理者配置憑證與私鑰。</p>
        </details>
        <button className="button primary section-note" disabled={busy || !host}>啟用運算主機</button>
      </form>}
      {running && <div className="section-note">
        <p className="pre">{host.label} · {host.address}:{host.port}</p>
        <p className="small pre">{host.engine?.accepting ? '可接收文字任務' : host.engine?.error} · {host.models?.length ?? 0} 個模型</p>
        <div className="row creation-actions">
          <button className="button primary" disabled={busy} onClick={()=>void change(async()=>{
            setInvite(await rpc('remote-host-invite',{confirmed:true}))
          })}>建立一次性配對邀請</button>
          <button className="button" disabled={busy} onClick={()=>void change(async()=>{
            setHost(await rpc('remote-host-stop'));setInvite('')
          })}>停止分享算力</button>
        </div>
        {invite && <label className="section-note">複製邀請給受信任的裝置（5 分鐘有效）
          <textarea aria-label="複製配對邀請" value={invite} readOnly onFocus={event=>event.currentTarget.select()}/></label>}
      </div>}
      {!!host?.peers.length && <details open className="section-note"><summary>已配對裝置</summary>
        {host.peers.map(peer=><div className="list-row pre" key={peer.id}><span>{peer.label}</span>
          <button className="button" disabled={busy} onClick={()=>void change(async()=>{
            setHost(await rpc('remote-host-revoke',{id:peer.id}))
          })}>撤銷</button></div>)}
      </details>}
      {issue && <p role="alert" className="pre creation-error">{issue}</p>}
      {note && <p role="status" className="pre">{note}</p>}
    </Panel>
  </div>
}
