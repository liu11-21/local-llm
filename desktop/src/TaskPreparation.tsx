import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { rpc } from './api'

type Target = {runtime: string; model: string}
type Transfer = {runtime: string; model: string; destination: string; cost: string}
type Match = {reasons: string[]; risks: string[]; unknown: string[]}
type Check = {blockers: string[]; transfers: Transfer[]; matches?: Match[]}
type Prepare = (task: string, targets: Target[], policy: string, contents?: string) => Promise<'local'|'confirmed'|'cancelled'>
const Preparation = createContext<Prepare>(async () => 'cancelled')

const prices: Record<string,string> = {'no-api-fee':'無 API 計費', 'may-charge':'可能產生費用', unknown:'費用未知，可能計費'}

export function TaskPreparationProvider({children}: {children: ReactNode}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const decision = useRef<((allow:boolean)=>void) | undefined>(undefined)
  const pending = useRef(false)
  const [review,setReview] = useState<{transfers:Transfer[]; contents:string}>()

  const finish = (allow: boolean) => {
    const resolve = decision.current
    decision.current = undefined
    dialog.current?.close()
    setReview(undefined)
    resolve?.(allow)
  }
  useEffect(() => {
    if (review && dialog.current && !dialog.current.open) dialog.current.showModal()
  }, [review])
  const prepare: Prepare = async (task, targets, policy, contents = '本次任務內容') => {
    if (pending.current) return 'cancelled'
    pending.current = true
    try {
      const check = await rpc<Check>('task-preflight', {task, targets, policy})
      if (check.blockers.length) throw new Error(check.blockers.join(' '))
      if (!check.transfers.length) return 'local'
      return await new Promise<boolean>(resolve => {
        decision.current = resolve
        setReview({transfers:check.transfers, contents})
      }) ? 'confirmed' : 'cancelled'
    } finally {pending.current = false}
  }
  return <Preparation.Provider value={prepare}>
    {children}
    <dialog ref={dialog} className="transfer-dialog" aria-labelledby="transfer-title"
      onCancel={event=>{event.preventDefault();finish(false)}}>
      {review && <>
        <h2 id="transfer-title">確認資料傳送</h2>
        <p className="section-note">將透過網路傳送{review.contents}。請核對模型、目的地和費用。</p>
        {review.transfers.map((item,index) => <div className="transfer-target pre" key={index}>
          <b>{item.runtime} · {item.model}</b><div>{item.destination} · {prices[item.cost] ?? prices.unknown}</div>
        </div>)}
        <div className="row creation-actions section-note">
          <button className="button" autoFocus onClick={()=>finish(false)}>返回編輯</button>
          <button className="button primary" onClick={()=>finish(true)}>同意並送出</button>
        </div>
      </>}
    </dialog>
  </Preparation.Provider>
}

export const useTaskPreparation = () => useContext(Preparation)

export function TaskFit({task, runtime, model, policy}: Target & {task: string; policy: string}) {
  const [check,setCheck] = useState<Check>()
  const [issue,setIssue] = useState('')
  const [waiting,setWaiting] = useState(false)
  if (!model) return null
  const match = check?.matches?.[0]
  return <details className="task-fit">
    <summary>相容性與資源</summary>
    <button className="button section-note" disabled={waiting} onClick={async()=>{
      setWaiting(true);setIssue('')
      try {setCheck(await rpc('task-preflight',{task,targets:[{runtime,model}],policy}))}
      catch (error) {setIssue(error instanceof Error ? error.message : String(error))}
      finally {setWaiting(false)}
    }}>{waiting ? '檢查中…' : '檢查此組合'}</button>
    {(check || issue) && <div role="status" className="small pre">
      {check?.blockers.map(item=><p key={item}>{item}</p>)}
      {match && [...match.reasons,...match.risks,...match.unknown].map(item=><p key={item}>{item}</p>)}
      {issue}
    </div>}
  </details>
}
