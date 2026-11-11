import assert from 'node:assert/strict'
import {mkdir} from 'node:fs/promises'
import {join} from 'node:path'
import {fileURLToPath} from 'node:url'
import {chromium} from 'playwright-core'
import {createServer} from 'vite'

const desktop=fileURLToPath(new URL('../',import.meta.url))
if(!process.env.LOCALLLM_DEVICE_DATA || !process.env.LOCALLLM_BENCHMARK_RUNTIME) throw new Error('Set native device data and Runtime paths')
process.env.LOCALLLM_PREVIEW_DATA=process.env.LOCALLLM_DEVICE_DATA
process.env.LOCALLLM_PREVIEW_WORKER=join(desktop,'tests','benchmark_native_worker.py')
process.env.LOCALLLM_PREVIEW_PORT='1434'
const shots=process.env.LOCALLLM_DEVICE_SHOTS
if(shots) await mkdir(shots,{recursive:true})
let server,browser
try {
  server=await createServer({root:desktop,mode:'preview-worker',logLevel:'warn'})
  await server.listen()
  browser=await chromium.launch({executablePath:process.env.LOCALLLM_BROWSER || join(process.env.ProgramFiles || 'C:\\Program Files','Google','Chrome','Application','chrome.exe')})
  const page=await browser.newPage({viewport:{width:1280,height:900},colorScheme:'dark',reducedMotion:'reduce'})
  const errors=[];page.on('pageerror',error=>errors.push(error.message))
  await page.goto('http://127.0.0.1:1434')
  await page.getByText('本機工作台已連線').waitFor()
  const guide=page.getByRole('dialog',{name:'開始使用 Local LLM'})
  if(await guide.isVisible())await guide.getByRole('button',{name:'略過引導',exact:true}).click()
  await page.getByRole('button',{name:'文字聊天',exact:true}).click()
  const chat=page.getByRole('region',{name:'文字聊天'})
  await chat.getByLabel('模型',{exact:true}).selectOption('SmolLM2-135M-Instruct-Q4_K_M.gguf')
  const choice=chat.getByRole('region',{name:'運算建議'})
  await choice.locator('summary').click()
  await choice.getByLabel('推薦偏好',{exact:true}).selectOption('speed')
  await choice.getByLabel('推薦參考工作量',{exact:true}).selectOption('short')
  const end=Date.now()+50000
  while(Date.now()<end) {
    await choice.getByRole('button',{name:'檢查運算建議',exact:true}).click()
    await choice.getByRole('button',{name:'檢查運算建議',exact:true}).waitFor()
    if((await choice.locator('.device-suggestion').textContent()).includes('Vulkan0'))break
    await page.waitForTimeout(1000)
  }
  assert((await choice.locator('.device-suggestion').textContent()).includes('Vulkan0'),'Expected actual same-recipe Vulkan latency evidence')
  await choice.getByRole('button',{name:'採用此裝置',exact:true}).click()
  assert.equal(await choice.getByLabel('執行裝置',{exact:true}).inputValue(),'Vulkan0')
  await choice.locator('summary').click()
  const existing=await page.evaluate(async()=>{
    const response=await fetch('/__desktop_dev_rpc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({op:'dispatch-runs',data:{}})})
    return (await response.json()).value.map(item=>item.id)
  })
  await page.getByLabel('訊息',{exact:true}).fill('Say hello in one short sentence.')
  await page.getByRole('button',{name:'送出',exact:true}).click()
  const until=Date.now()+90000
  let execution
  while(Date.now()<until) {
    execution=await page.evaluate(async existing=>{
      const response=await fetch('/__desktop_dev_rpc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({op:'dispatch-runs',data:{}})})
      const reply=await response.json()
      return reply.value?.find(item=>!existing.includes(item.id))
    },existing)
    if(execution && ['completed','failed'].includes(execution.state))break
    await page.waitForTimeout(250)
  }
  assert.equal(execution?.state,'completed')
  assert.equal(execution.details.requested_device,'Vulkan0')
  assert.equal(execution.details.execution_device_verified,false)
  await page.getByRole('button',{name:'送出',exact:true}).waitFor()
  await page.locator('.message.assistant .markdown').last().waitFor()
  assert((await page.locator('.message.assistant .markdown').last().textContent()).trim().length>0)
  await page.evaluate(()=>{window.scrollTo(0,0);document.querySelector('.content')?.scrollTo(0,0)})
  if(shots)await page.screenshot({path:join(shots,'device-chat-vulkan-real-dark.png')})
  await page.setViewportSize({width:650,height:720});await page.getByTitle('切換主題').click()
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))
  if(shots)await page.screenshot({path:join(shots,'device-chat-vulkan-real-light-650.png')})
  await page.setViewportSize({width:1280,height:900})
  const menu=page.getByTitle('導覽');if(await menu.isVisible())await menu.click()
  await page.getByRole('button',{name:'任務中心',exact:true}).click()
  await page.getByText(/指定 Vulkan0 · 實際 unknown/).first().waitFor()
  if(shots)await page.screenshot({path:join(shots,'device-task-evidence-real-light.png')})
  assert.deepEqual(errors,[])
  console.log('PASS real shared recommendation -> user adopts Vulkan -> isolated chat -> persisted execution -> task evidence, dark/light and 650px')
} finally {
  if(browser)await browser.close()
  if(server)await server.close()
}
