import assert from 'node:assert/strict'
import {mkdir} from 'node:fs/promises'
import {join} from 'node:path'
import {fileURLToPath} from 'node:url'
import {chromium} from 'playwright-core'
import {createServer} from 'vite'

const desktop=fileURLToPath(new URL('../',import.meta.url))
if(!process.env.LOCALLLM_OV_ACCEPTANCE_DATA) throw new Error('Set LOCALLLM_OV_ACCEPTANCE_DATA to an existing acceptance profile')
process.env.LOCALLLM_PREVIEW_DATA=process.env.LOCALLLM_OV_ACCEPTANCE_DATA
process.env.LOCALLLM_PREVIEW_PORT='1430'
delete process.env.LOCALLLM_PREVIEW_WORKER
const shots=process.env.LOCALLLM_OV_SHOTS
if(shots) await mkdir(shots,{recursive:true})
let server,browser
try {
  server=await createServer({root:desktop,mode:'preview-worker',logLevel:'warn'})
  await server.listen()
  browser=await chromium.launch({executablePath:process.env.LOCALLLM_BROWSER ||
    join(process.env.ProgramFiles || 'C:\\Program Files','Google','Chrome','Application','chrome.exe')})
  const page=await browser.newPage({viewport:{width:1280,height:900},colorScheme:'dark',reducedMotion:'reduce'})
  await page.goto('http://127.0.0.1:1430')
  await page.getByText('本機工作台已連線').waitFor()
  const guide=page.getByRole('dialog',{name:'開始使用 Local LLM'})
  if(await guide.isVisible()) await guide.getByRole('button',{name:'略過引導',exact:true}).click()
  await page.getByRole('button',{name:'運算環境',exact:true}).click()
  await page.getByRole('button',{name:'檢查 OpenVINO 裝置',exact:true}).click()
  await page.getByText(/後端回報 CPU、GPU/).waitFor()
  if(shots) await page.screenshot({path:join(shots,'openvino-runtime-real.png'),fullPage:true})
  await page.getByRole('button',{name:'使用 OpenVINO 聊天',exact:true}).click()
  const region=page.getByRole('region',{name:'文字聊天'})
  await region.getByLabel('模型',{exact:true}).selectOption(process.env.LOCALLLM_OV_MODEL || '6801f654268e3090')
  await page.getByLabel('訊息').fill('Say hello in one short sentence.')
  await page.getByRole('button',{name:'送出',exact:true}).click()
  await page.getByText('Hello! How can I assist you today?',{exact:true}).waitFor({timeout:90000})
  await page.locator('.message .small').filter({hasText:/OpenVINO ·/}).waitFor()
  await page.getByRole('button',{name:'送出',exact:true}).waitFor()
  assert.equal(await page.getByText('需要重新連線',{exact:true}).count(),0)
  await page.evaluate(()=>{window.scrollTo(0,0);document.querySelector('.content')?.scrollTo(0,0)})
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))
  if(shots) await page.screenshot({path:join(shots,'openvino-chat-cpu-real-dark.png')})
  await page.setViewportSize({width:650,height:720})
  await page.getByTitle('切換主題').click()
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))
  if(shots) await page.screenshot({path:join(shots,'openvino-chat-cpu-real-light.png')})
  console.log('PASS real OpenVINO CPU chat through React, IPC, TaskManager and persisted history')
} finally {
  if(browser) await browser.close()
  if(server) await server.close()
}
