import { useEffect, useState } from 'react'
import { rpc, type HardwareCapabilities } from './api'
import { Panel, gb } from './ui'

export function HardwarePanel() {
  const [hardware,setHardware] = useState<HardwareCapabilities>()
  const [probing,setProbing] = useState(false)
  const [issue,setIssue] = useState('')
  useEffect(()=>{
    let mounted = true
    let pending = false
    const sample = async () => {
      if (document.hidden || pending) return
      pending = true
      try {
        const value = await rpc<HardwareCapabilities>('hardware-capabilities')
        if (mounted) {setHardware(value);setIssue('')}
      } catch {if(mounted)setIssue('目前無法取得硬體資料。')}
      finally {pending=false}
    }
    void sample()
    const timer = window.setInterval(sample,5000)
    return ()=>{mounted=false;window.clearInterval(timer)}
  },[])
  return <Panel title="GPU 與 NPU" description="依 Windows 裝置與效能計數器顯示。硬體存在時，模型仍需符合推理後端的要求。">
    <p className="small">NPU · {hardware?.npu_present.value===true ? '已偵測' :
      hardware?.npu_present.value===false ? '未偵測到 NPU' : '未知 · 裝置資料尚未取得'}</p>
    {hardware?.devices.map(device=><article key={device.id} className="remote-peer section-note">
      <h3 className="pre">{device.name}</h3>
      <p className="small">{device.vendor} · {device.kind.toUpperCase()} · Windows 偵測
        {device.driver.value ? ` · 驅動 ${device.driver.value}` : ' · 驅動版本未知'}</p>
      {device.kind==='gpu' && <p className="small muted">記憶體架構 · {device.memory_type==='unified' ? '統一記憶體' :
        device.memory_type==='dedicated' ? '獨立顯存' : '尚未確認'}。模型可分配容量仍需由推理後端確認。</p>}
      {device.driver_state.value!==null && <p className="small">{device.driver_state.value===0 ? '裝置管理員未回報錯誤' :
        `裝置管理員錯誤碼 ${device.driver_state.value}`}</p>}
      <dl className="hardware-readings">
        <div><dt>使用率</dt><dd>{device.utilization.value===null ? device.utilization.status==='unsupported' ? '尚無支援的監控介面' : '未知' : `${device.utilization.value}%`}</dd></div>
        <div><dt>專用顯存</dt><dd>{device.vram_total.value===null ? '未知' : gb(device.vram_total.value)}</dd></div>
        <div><dt>已用專用顯存</dt><dd>{device.vram_used.value===null ? '未知' : gb(device.vram_used.value)}</dd></div>
        <div><dt>可用專用顯存</dt><dd>{device.vram_available.value===null ? '未知' : gb(device.vram_available.value)}</dd></div>
        {device.shared_used && <div><dt>已用共享記憶體</dt><dd>{device.shared_used.value===null ? '未知' : gb(device.shared_used.value)}</dd></div>}
      </dl>
      {device.kind!=='gpu' && <p className="small muted">NPU 推理待硬體驗收。一般聊天與創作可繼續使用既有 CPU／GPU 引擎。</p>}
    </article>)}
    {!hardware?.devices.length && <p className="small muted">{hardware?.state==='unsupported' ? '此作業系統尚未支援裝置監控。' :
      '尚未取得 GPU 或 NPU 清單。缺少的資訊會保留為未知。'}</p>}
    <details className="section-note"><summary>進階 · 推理 Provider 與模型格式</summary>
      <p className="small section-note">可檢查此工作程序環境已安裝的 OpenVINO 與 ONNX Runtime。可用 Provider 由後端回報，模型與算子分配仍需獨立驗證。</p>
      <button className="button" disabled={probing} onClick={async()=>{
        setProbing(true);setIssue('')
        try {setHardware(await rpc<HardwareCapabilities>('hardware-provider-probe'))}
        catch {setIssue('Provider 查詢未完成。可稍後重試。')}
        finally {setProbing(false)}
      }}>{probing ? '正在檢查…' : '檢查已安裝的 Provider'}</button>
      {hardware?.provider_state==='failed' && <p className="small" role="status">後端查詢失敗或逾時。可繼續使用既有引擎。</p>}
      {hardware?.providers.map(provider=><article className="section-note pre" key={provider.id}>
        <b>{provider.id} {provider.version}</b>
        <p className="small">{provider.state==='missing' ? '此工作程序環境未安裝' :
          provider.state==='reported' ? '後端回報' : '初始化失敗'}</p>
        {provider.state==='reported' && <>
          <p className="small">裝置 {provider.devices.join('、') || '尚未驗證'} · Provider {provider.providers.join('、') || '未知'}</p>
          <p className="small">候選格式 {provider.formats.join('、')} · 量化支援待模型驗證</p>
        </>}
        <p className="small muted">{provider.limitations}</p>
      </article>)}
    </details>
    {hardware && <p className="small muted section-note">取樣 {new Date(hardware.checked_at*1000).toLocaleTimeString()} ·
      裝置清單 {hardware.inventory_at ? new Date(hardware.inventory_at*1000).toLocaleTimeString() : '等待偵測'}</p>}
    {issue && <p role="status" className="small">{issue}</p>}
  </Panel>
}
