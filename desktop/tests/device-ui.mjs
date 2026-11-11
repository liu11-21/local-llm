import assert from 'node:assert/strict'

// Controlled decision UI only; no mocked values enter the hardware evidence database.
export async function exerciseDevices(page,navigate) {
  let queries=0,runs=0
  const long='受控裝置 · '+ 'VeryLongDeviceAndModelName'.repeat(12)
  await page.route('**/__desktop_dev_rpc',async route=>{
    const {op,data}=route.request().postDataJSON()
    if(op==='info') {
      const response=await route.fetch();const result=await response.json()
      result.value.devices=[['Vulkan0',8*1024**3,false]]
      return route.fulfill({json:result})
    }
    if(op==='runtime-recommend') {
      queries++;assert.equal('prompt' in data,false)
      const base={runtime:'local',engine:'llama.cpp',model:data.model,availability:'ready',executable:true,network:false,cost:'no-api-fee',
        evidence_level:'capability-only',confidence:'unknown',reasons:['相容性建議，目前無法確定哪個設備最快。'],risks:[],uncertainty:['沒有此工作量的 Benchmark。'],
        resource:{ram_estimate:null,vram_estimate:null,memory_type:'unknown'},identity:{},evidence:[]}
      return route.fulfill({json:{ok:true,value:{recommended:'CPU',comparison:null,candidates:[
        {...base,id:'CPU',device:'CPU',label:long},
        {...base,id:'GPU',device:'Vulkan0',label:'受控 GPU',evidence:[{freshness:'stale',comparability:'partially_comparable',eligible_for_ranking:false,
          limitations:['驅動已更新，舊結果保留但不作目前排名。'],missing:[],changed:[],stale_reasons:['driver']}]},
        {...base,id:'NPU',device:'NPU',label:'受控 NPU 未實測',availability:'incompatible',executable:false,reasons:['無已驗證 Adapter 或相容硬體。']},
        {...base,id:'offline',runtime:'controlled-offline',device:'remote',label:'受控離線遠端',availability:'needs-setup',executable:false,network:true,cost:'unknown',needs_consent:true}
      ],explanation:'Controlled UI only'}}})
    }
    if(op==='run')runs++
    return route.fallback()
  })
  await page.setViewportSize({width:1280,height:900})
  await page.reload();await page.getByText('本機工作台已連線').waitFor()
  await navigate('文字聊天')
  const chat=page.getByRole('region',{name:'文字聊天'})
  await chat.getByLabel('運算環境',{exact:true}).selectOption('local')
  const card=chat.getByRole('region',{name:'運算建議',exact:true})
  assert.equal(queries,0,'Opening a page must not automatically run evidence probes or benchmarks')
  await card.getByRole('button',{name:'檢查運算建議',exact:true}).click()
  await card.getByRole('status').filter({hasText:/無法確定哪個設備最快/}).waitFor()
  await card.getByRole('button',{name:'採用此裝置',exact:true}).click()
  assert.equal(await card.getByLabel('執行裝置',{exact:true}).inputValue(),'CPU')
  await card.getByLabel('執行裝置',{exact:true}).selectOption('Vulkan0')
  assert.equal(await card.getByLabel('執行裝置',{exact:true}).inputValue(),'Vulkan0')
  await card.locator('summary').click()
  await card.getByText(/stale · partially_comparable/).waitFor()
  await card.getByText(/受控離線遠端/).waitFor()
  await card.getByText(/受控 NPU 未實測/).waitFor()
  for(const [width,height] of [[1280,900],[1024,768],[800,600],[650,720]]) {
    await page.setViewportSize({width,height})
    for(let i=0;i<2;i++) {
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Device recommendation overflow ${width}`)
      await page.getByTitle('切換主題').click()
    }
  }
  await card.getByLabel('執行裝置',{exact:true}).focus()
  await page.keyboard.press('Home');await page.keyboard.press('ArrowDown')
  assert.equal(await card.getByLabel('執行裝置',{exact:true}).inputValue(),'CPU')
  assert.equal(runs,0,'Recommendations and manual overrides must not submit tasks')
  await page.setViewportSize({width:1280,height:900})
  for(const name of ['AI 代理人','AI 團隊','圖片生成','影片生成','音樂生成','運算環境']) {
    await navigate(name)
    assert(await page.locator('.device-choice:visible').count()>0,`Missing shared picker on ${name}`)
  }
  await navigate('模型與應用')
  await page.locator('summary').filter({hasText:/模型運算建議/}).first().click()
  assert(await page.locator('.device-choice:visible').count()>0)
  console.log('PASS shared device recommendation across chat Agent Team media model/runtime centres, stale/missing/offline evidence, manual override, no auto-dispatch, keyboard and four sizes/both themes')
}
