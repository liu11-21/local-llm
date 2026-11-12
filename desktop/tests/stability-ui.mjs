import assert from 'node:assert/strict'
import {mkdir,writeFile} from 'node:fs/promises'
import {join} from 'node:path'

export async function exerciseStability(page) {
  const shots=process.env.LOCALLLM_070_SHOTS
  if(shots)await mkdir(shots,{recursive:true})
  const rpc=(op,data={})=>page.evaluate(async({op,data})=>{
    const reply=await(await fetch('/__desktop_dev_rpc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({op,data})})).json()
    if(!reply.ok)throw Error(reply.error)
    return reply.value
  },{op,data})
  const go=async name=>{const menu=page.getByTitle('導覽');if(await menu.isVisible())await menu.click();await page.getByRole('button',{name,exact:true}).click()}
  await page.setViewportSize({width:1280,height:900})
  await go('設定')
  await page.getByText('Local LLM Workspace 0.7.0 · Development',{exact:true}).waitFor()
  await page.getByText('建置詳情',{exact:true}).click()
  await page.getByText(/Worker：0.7.0/).waitFor()
  if(shots)await page.screenshot({path:join(shots,'settings-version.png'),fullPage:true})
  const timings={home_render_ms:[],runtime_selector_ms:[]}
  for(let n=0;n<3;n++){
    await go('文字聊天');let started=performance.now();await go('首頁')
    await page.getByRole('heading',{name:'繼續你的工作',exact:true}).waitFor()
    timings.home_render_ms.push(performance.now()-started)
    const monitor=page.getByRole('button',{name:'硬體監控 · 展開',exact:true})
    assert.equal(await monitor.getAttribute('aria-expanded'),'false')
    assert.equal(await page.getByRole('region',{name:'本機資源'}).count(),0)
    await monitor.click();await page.locator('.resource-board header').getByText('即時取樣',{exact:true}).waitFor()
    await page.getByRole('button',{name:'硬體監控 · 收合',exact:true}).click()
    assert.equal(await page.getByRole('region',{name:'本機資源'}).count(),0)
    await go('文字聊天')
    if(await page.locator('.chat-config').getAttribute('open')===null)await page.locator('.chat-config > summary').click()
    const select=page.locator('.chat-config').getByLabel('運算環境',{exact:true})
    started=performance.now();await select.selectOption('openvino');await page.waitForFunction(()=>!document.querySelector('.chat-config select[aria-label="運算環境"]').disabled)
    timings.runtime_selector_ms.push(performance.now()-started)
    await select.selectOption('local');await page.waitForFunction(()=>!document.querySelector('.chat-config select[aria-label="運算環境"]').disabled)
  }
  await rpc('fixture-many-chats')
  await go('首頁');await go('文字聊天')
  const history=page.getByRole('complementary',{name:'對話歷史'})
  await history.getByLabel('搜尋對話',{exact:true}).fill('Volume history')
  await page.waitForFunction(()=>document.querySelectorAll('.history-item').length===50)
  await history.locator('.history-item').first().waitFor();assert.equal(await history.locator('.history-item').count(),50)
  const original=await history.locator('.history-item').first().getAttribute('title')
  await history.getByRole('button',{name:'下一頁',exact:true}).click()
  await page.waitForFunction(original=>document.querySelector('.history-item')?.title!==original,original)
  assert.equal(await history.locator('.history-item').count(),50)
  await history.getByLabel('搜尋對話',{exact:true}).fill('Volume history 134')
  await history.getByRole('button',{name:'Volume history 134',exact:true}).waitFor()
  assert.equal(await history.locator('.history-item').count(),1)
  await history.getByLabel('搜尋對話',{exact:true}).fill('')
  await page.waitForFunction(()=>document.querySelectorAll('.history-item').length===50)
  if(shots)await page.screenshot({path:join(shots,'chat-history-paged.png')})
  await go('首頁');await page.getByRole('heading',{name:'繼續你的工作',exact:true}).waitFor()
  if(shots)await page.screenshot({path:join(shots,'home-monitor-collapsed.png'),fullPage:true})
  const forwarded=[]
  const mismatch=async route=>{
    const request=route.request().postDataJSON();forwarded.push(request.op)
    if(request.op==='build-info')return route.fulfill({json:{ok:true,value:{version:'0.6.2',channel:'Development',commit:'old'}}})
    return route.continue()
  }
  const isolated=await page.context().browser().newContext()
  const probe=await isolated.newPage()
  await probe.route('**/__desktop_dev_rpc',mismatch)
  await probe.goto(page.url());await probe.getByRole('alert').getByText(/介面與工作程序版本不一致/).waitFor()
  assert(forwarded.every(op=>op==='build-info'),'Mixed frontend/worker must block all product operations')
  await isolated.close()
  if(process.env.LOCALLLM_070_EVIDENCE){
    await mkdir(process.env.LOCALLLM_070_EVIDENCE,{recursive:true})
    await writeFile(join(process.env.LOCALLLM_070_EVIDENCE,'ui-stability.json'),JSON.stringify({status:'PASS',model_inference:false,
      version:'0.7.0',channel:'Development',mixed_worker_operations_blocked:true,chat_page_size:50,chat_search:true,
      collapsed_monitor_unmounted:true,timings,scope:'Real React and production RPC; controlled Runtime, not model load/remote hardware performance'},null,2))
  }
  console.log('PASS 0.7.0 settings identity, mixed-worker rejection, paged searchable history, collapsed monitoring and repeated UI baselines')
}
