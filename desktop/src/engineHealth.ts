import { useEffect, useState } from 'react'
import { rpc, type EngineHealth, type EngineStatus } from './api'

export const engineLabels: Record<EngineStatus['state'], string> = {
  not_installed:'尚未安裝', installed:'已安裝 · 待啟動', starting:'正在啟動', ready:'已就緒',
  busy:'執行中', stopping:'正在停止', stopped:'已停止', unhealthy:'API 無回應', failed:'引擎發生錯誤',
}

export function useEngineHealth() {
  const [health, setHealth] = useState<EngineHealth>()
  useEffect(() => {
    let running = false
    let mounted = true
    async function check() {
      if (running) return
      running = true
      try {
        const state = await rpc<EngineHealth>('engine-health')
        if (mounted) setHealth(state)
      } catch { if (mounted) setHealth(undefined) }
      finally { running = false }
    }
    void check()
    const timer = window.setInterval(check, 1800)
    return () => { mounted = false; window.clearInterval(timer) }
  }, [])
  return health
}
