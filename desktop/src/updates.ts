import { useEffect, useState } from 'react'
import { rpc } from './api'

type UpdateStatus = { version: string; state: 'idle' | 'checking' | 'current' | 'available' | 'error'; tag?: string; message?: string }

export function useWorkspaceUpdates() {
  const [status, setStatus] = useState<UpdateStatus>()
  async function check() {
    try { setStatus(await rpc('update-check')) }
    catch { setStatus({ version: '', state: 'error', message: '無法連線至工作程序。' }) }
  }
  useEffect(() => { void check() }, [])
  useEffect(() => {
    if (status?.state !== 'checking') return
    const timer = setInterval(() => {
      void rpc<UpdateStatus>('update-status').then(setStatus, () => {
        setStatus({ version: '', state: 'error', message: '無法連線至工作程序。' })
      })
    }, 1500)
    return () => clearInterval(timer)
  }, [status?.state])
  return { status, check }
}
