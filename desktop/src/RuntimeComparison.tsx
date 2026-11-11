import { useEffect, useState } from 'react'
import { rpc, type Info } from './api'
import { Panel } from './ui'

type Comparison = {id:string; label:string; state:string; recommended:boolean; reasons:string[]; risks:string[]; unknown:string[]}
const labels: Record<string,string> = {incompatible:'不相容', 'needs-setup':'需要設定', uncertain:'待確認', compatible:'相容'}
const tasks = {chat:'文字聊天', agent:'AI 代理人', team:'AI 團隊', image:'圖片', video:'影片', music:'音樂', notebook:'Notebook'}

export function RuntimeComparison({info, policy}: {info?:Info; policy:string}) {
  const [task, setTask] = useState<keyof typeof tasks>('chat')
  const [model, setModel] = useState('')
  const [results, setResults] = useState<Comparison[]>()
  const [error, setError] = useState('')
  const [waiting, setWaiting] = useState(false)
  const options = task === 'notebook' ? [] : ['image','video','music'].includes(task) ?
    info?.registry.media_models?.filter(item=>item.kind===task).map(item=>item.id) :
    [...new Set([...(info?.models ?? []), ...(info?.providers.flatMap(item=>item.models) ?? [])])]
  useEffect(() => {setResults(undefined)}, [info, policy])
  return <details className="section-note"><summary>比較運算環境</summary>
    <Panel title="比較運算環境" description="比較使用目前已取得的能力資料。送出任務時仍由您選擇環境。">
      <form onSubmit={async event=>{
        event.preventDefault();setWaiting(true);setError('');setResults(undefined)
        try {setResults(await rpc('runtime-compare',{task, model, policy}))}
        catch (failure) {setError(failure instanceof Error ? failure.message : String(failure))}
        finally {setWaiting(false)}
      }}>
        <div className="parameters work-filters">
          <label>任務<select aria-label="比較任務" value={task} onChange={e=>{setTask(e.target.value as keyof typeof tasks);setModel('');setResults(undefined)}}>
            {Object.entries(tasks).map(([id,label])=><option value={id} key={id}>{label}</option>)}
          </select></label>
          <label>模型<select aria-label="比較模型" value={model} onChange={e=>{setModel(e.target.value);setResults(undefined)}}>
            <option value="">未選擇</option>{options?.map(id=><option key={id}>{id}</option>)}
          </select></label>
        </div>
        <button className="button" disabled={waiting}>{waiting?'比較中…':'比較能力'}</button>
      </form>
      {results?.map(result=><article className="remote-peer section-note pre" key={result.id}>
        <b>{result.label} · {labels[result.state]}</b>
        {[...result.reasons,...result.risks,...result.unknown].map(text=><p className="small" key={text}>{text}</p>)}
      </article>)}
      {error && <p role="alert" className="creation-error pre">{error}</p>}
    </Panel>
  </details>
}
