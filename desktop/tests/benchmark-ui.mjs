import assert from 'node:assert/strict'

// Controlled UI data only. These numbers are never exported as hardware evidence.
export async function exerciseBenchmarks(page,navigate) {
  const model='Controlled-Benchmark-Model-'+ 'VeryLongName'.repeat(12)
  const records=[{id:'a'.repeat(32),model,engine:'openvino',state:'completed',created:'2026-11-11T00:00:00Z'},
    {id:'b'.repeat(32),model,engine:'openvino',state:'failed',created:'2026-11-11T00:00:01Z'}]
  let state='none'
  await page.route('**/__desktop_dev_rpc',async route=>{
    const {op,data}=route.request().postDataJSON()
    const reply=value=>route.fulfill({json:{ok:true,value}})
    if(op==='benchmark-plan') return reply({models:[{id:model,label:model,engine:'openvino',kind:'text'}],devices:{openvino:['CPU']}})
    if(op==='benchmark-list') return reply(data.device==='absent' ? [] : records)
    if(op==='benchmark-get') return reply({...records.find(item=>item.id===data.id),config:{},runs:[{
      id:'controlled-run',device:'CPU · '+ 'LongDeviceName'.repeat(10),state:data.id===records[0].id ? 'completed' : 'failed',
      error:data.id===records[0].id ? null : 'CONTROLLED_BACKEND_FAILURE',environment:{},evidence:{verified_inference:false},
      measurements:[{workload:'short',phase:'measured',latency_ms:25,input_tokens:null,output_tokens:null}],
      summary:{short:{count:1,mean_ms:25,p50_ms:25,p95_ms:25,stddev_ms:0,requests_per_second:40}}}]})
    if(op==='benchmark-compare') return reply({comparable:false,reasons:['受控不同量化，不可等價比較。']})
    if(op==='benchmark-export') return reply({path:`C:\\Controlled-UI-Only\\benchmark.${data.format}`})
    if(op==='run' && data.action==='benchmark') {
      assert.equal(data.confirmed,true);assert.deepEqual(data.devices,['CPU'])
      state='running';return reply({id:'controlled-benchmark'})
    }
    if(op==='job' && data.id==='controlled-benchmark') return reply({id:data.id,state,message:'Controlled Benchmark only'})
    if(op==='cancel' && data.id==='controlled-benchmark') {state='cancelled';return reply({id:data.id,state})}
    if(op==='task-list' && state!=='none') {
      const response=await route.fetch();const result=await response.json()
      return reply([{id:'controlled-benchmark',action:'benchmark',kind:'benchmark',state,message:'受控 Benchmark 進行中',created:'2026-11-11T00:00:00Z'},...result.value])
    }
    return route.fallback()
  })
  await page.reload()
  await page.getByText('本機工作台已連線').waitFor()
  await navigate('運算環境')
  const summary=page.locator('.benchmark-section > summary')
  await summary.focus();await page.keyboard.press('Enter')
  await page.getByLabel('測試模型',{exact:true}).selectOption('openvino:'+model)
  assert.equal(await page.locator('.benchmark-devices input').count(),1)
  assert(await page.getByRole('button',{name:'開始 Benchmark',exact:true}).isDisabled())
  await page.getByLabel('依設備篩選').fill('absent')
  await page.getByText('目前沒有符合條件的測試紀錄。',{exact:true}).waitFor()
  await page.getByLabel('依設備篩選').fill('')
  const rows=page.locator('.benchmark-section .list-row')
  await rows.first().getByRole('button',{name:'檢視',exact:true}).click()
  await page.getByText(/Token 輸入 \/ 輸出 未知 \/ 未知/).waitFor()
  await rows.nth(1).getByRole('button',{name:'比較',exact:true}).click()
  await page.getByText(/非完全等價比較 · 受控不同量化/).waitFor()
  await page.getByText('CONTROLLED_BACKEND_FAILURE',{exact:true}).waitFor()
  for(const [width,height] of [[1280,900],[1024,768],[800,600],[650,720]]) {
    await page.setViewportSize({width,height})
    for(let i=0;i<2;i++) {
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Benchmark overflow ${width}`)
      await page.getByTitle('切換主題').click()
    }
  }
  await page.getByRole('button',{name:'匯出 CSV',exact:true}).click()
  await page.getByRole('status').filter({hasText:/Controlled-UI-Only/}).waitFor()
  await page.getByLabel('我確認以上測試負載及資源上限').check()
  await page.getByRole('button',{name:'開始 Benchmark',exact:true}).click()
  await page.getByRole('button',{name:'取消 Benchmark',exact:true}).click()
  await page.getByRole('button',{name:'取消 Benchmark',exact:true}).waitFor({state:'hidden'})
  console.log('PASS controlled Benchmark empty/failed/unknown states, non-equivalence, long names, no GPU/NPU, consent, cancel, keyboard and four sizes in both themes')
}
