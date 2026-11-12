import assert from 'node:assert/strict'
import {mkdir,writeFile,readFile} from 'node:fs/promises'
import {join} from 'node:path'
import {fileURLToPath} from 'node:url'
import {chromium} from 'playwright-core'
import {createServer} from 'vite'

const desktop=fileURLToPath(new URL('../',import.meta.url))
process.env.LOCALLLM_PREVIEW_DATA=process.env.LOCALLLM_DEVICE_DATA
process.env.LOCALLLM_PREVIEW_WORKER=join(desktop,'tests','benchmark_native_worker.py')
process.env.LOCALLLM_PREVIEW_PORT='1434'
const evidence=process.env.LOCALLLM_MEDIA_EVIDENCE
const shots=process.env.LOCALLLM_E4_SHOTS
let server,browser
try {
  server=await createServer({root:desktop,mode:'preview-worker',logLevel:'warn'});await server.listen()
  browser=await chromium.launch({executablePath:join(process.env.ProgramFiles || 'C:\\Program Files','Google','Chrome','Application','chrome.exe')})
  const page=await browser.newPage({viewport:{width:1280,height:900},colorScheme:'dark',reducedMotion:'reduce'})
  const rpc=(op,data={})=>page.evaluate(async({op,data})=>{
    const reply=await (await fetch('/__desktop_dev_rpc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({op,data})})).json()
    if(!reply.ok)throw new Error(reply.error);return reply.value
  },{op,data})
  let adopted
  page.on('response',async response=>{
    if(response.url().includes('/__desktop_dev_rpc') && response.request().postDataJSON()?.op==='runtime-recommend')adopted=(await response.json()).value
  })
  await page.goto('http://127.0.0.1:1434');await page.getByText('本機工作台已連線').waitFor()
  const guide=page.getByRole('dialog',{name:'開始使用 Local LLM'});if(await guide.isVisible())await guide.getByRole('button',{name:'略過引導'}).click()
  await page.getByRole('button',{name:'運算環境',exact:true}).click()
  const oldTasks=await rpc('task-list')
  await page.getByRole('button',{name:'檢查 OpenVINO 裝置',exact:true}).click()
  let detection
  for(let attempt=0;attempt<240;attempt++) {
    detection=(await rpc('task-list')).find(task=>task.action==='openvino-detect' && !oldTasks.some(old=>old.id===task.id))
    if(detection && ['completed','failed'].includes(detection.state))break
    await page.waitForTimeout(250)
  }
  assert.equal(detection?.state,'completed',detection?.message)
  let explicitBenchmark,priorEvidence
  if(process.env.LOCALLLM_ACCEPTANCE_BENCHMARK==='1') {
    priorEvidence=await rpc('runtime-recommend',{task:'tensor',model:'2be7d6055f735f29',preference:'speed',workload:'input-1',reference:true})
    const job=await rpc('run',{action:'benchmark',engine:'openvino',model:'2be7d6055f735f29',devices:['CPU','GPU'],confirmed:true,
      warmup:3,iterations:10,timeout:180,memory_mib:4096,max_tokens:32,
      workloads:[{inputs:[[[...Array(512).fill(1)]]],expected:[[[...Array(512).fill(256)]]]}]})
    for(let attempt=0;attempt<720;attempt++) {
      explicitBenchmark=await rpc('job',job)
      if(['completed','failed'].includes(explicitBenchmark.state))break
      await page.waitForTimeout(250)
    }
    assert.equal(explicitBenchmark?.state,'completed',explicitBenchmark?.message)
  }
  await page.locator('summary').filter({hasText:'相容模型與進階推理'}).click()
  await page.getByLabel('OpenVINO 模型',{exact:true}).selectOption('2be7d6055f735f29')
  const choice=page.getByRole('region',{name:'運算建議',exact:true}).filter({has:page.getByLabel('執行裝置',{exact:true})}).last()
  await choice.locator('summary').click()
  await choice.getByLabel('推薦偏好',{exact:true}).selectOption('speed')
  await choice.getByLabel('推薦參考工作量',{exact:true}).selectOption('input-1')
  for(let attempt=0;attempt<30;attempt++) {
    await choice.getByRole('button',{name:'檢查運算建議',exact:true}).click()
    await choice.getByRole('button',{name:'檢查運算建議',exact:true}).waitFor()
    if(adopted?.comparison?.ordered_candidates.length>1)break
    await page.waitForTimeout(1000)
  }
  assert(adopted?.comparison?.ordered_candidates.length>1,'Need actual qualified CPU/GPU ordering, not a compatibility fallback')
  await choice.getByRole('button',{name:'採用此裝置',exact:true}).click()
  const before=await rpc('dispatch-runs')
  await page.getByLabel('輸入張量 JSON',{exact:true}).fill(JSON.stringify([[[...Array(512).fill(1)]]]))
  await page.getByRole('button',{name:'執行張量推理',exact:true}).click()
  let dispatch
  for(let attempt=0;attempt<240;attempt++) {
    dispatch=(await rpc('dispatch-runs')).find(item=>!before.some(old=>old.id===item.id))
    if(dispatch && ['failed','completed'].includes(dispatch.state))break
    await page.waitForTimeout(250)
  }
  assert.equal(dispatch?.state,'completed')
  assert.equal(dispatch.details.recommendation.recommendation_id,adopted.recommendation_id)
  assert.equal(dispatch.details.execution_device_verified,true)
  assert(dispatch.details.recommendation.benchmarks.length)
  const chosen=adopted.candidates.find(item=>item.id===adopted.recommended)
  for(const ref of dispatch.details.recommendation.benchmarks)assert(chosen.evidence.some(entry=>entry.session===ref.benchmark_id && entry.run===ref.benchmark_run_id && entry.eligible_for_ranking && entry.freshness==='current'))
  const task=await rpc('job',{id:dispatch.task})
  assert.equal(task.state,'completed')
  assert(task.result.inference.outputs.flat(3).every(value=>value===256))
  await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(button=>button.textContent==='執行張量推理' && !button.disabled))
  if(evidence){
    await mkdir(evidence,{recursive:true})
    let previous;try{previous=JSON.parse(await readFile(join(evidence,'recommendation-native-real.json'),'utf8'))}catch{}
    await writeFile(join(evidence,'recommendation-native-real.json'),JSON.stringify({status:'PASS',source:'real-react-adoption-and-native-openvino',recommender_started_benchmark:false,
      acceptance_explicit_benchmark:explicitBenchmark ?? previous?.acceptance_explicit_benchmark,prior_evidence:priorEvidence ?? previous?.prior_evidence,recommendation:adopted,dispatch,output_correct:true},null,2))
  }
  if(shots){
    await mkdir(shots,{recursive:true});await page.getByRole('button',{name:'任務中心',exact:true}).click()
    const card=page.locator('.task-card').filter({hasText:dispatch.task})
    await card.locator('summary').click();await card.scrollIntoViewIfNeeded()
    assert(await card.getByText('完成',{exact:true}).isVisible())
    await page.screenshot({path:join(shots,'recommendation-native-real.png')})
  }
  console.log('PASS real Benchmark CPU/GPU order -> UI adoption -> recommendation receipt -> TaskManager -> native OpenVINO -> matching output and Dispatch IDs')
} finally {if(browser)await browser.close();if(server)await server.close()}
