import assert from 'node:assert/strict'
import {mkdir} from 'node:fs/promises'
import {join} from 'node:path'
import {fileURLToPath} from 'node:url'
import {chromium} from 'playwright-core'
import {createServer} from 'vite'
import {exerciseBenchmarks} from './benchmark-ui.mjs'

const desktop=fileURLToPath(new URL('../',import.meta.url))
if(!process.env.LOCALLLM_BENCHMARK_DATA || !process.env.LOCALLLM_BENCHMARK_RUNTIME) throw new Error('Set benchmark data and Runtime paths')
process.env.LOCALLLM_PREVIEW_DATA=process.env.LOCALLLM_BENCHMARK_DATA
process.env.LOCALLLM_PREVIEW_WORKER=join(desktop,'tests','benchmark_native_worker.py')
process.env.LOCALLLM_PREVIEW_PORT='1432'
const shots=process.env.LOCALLLM_BENCHMARK_SHOTS
if(shots) await mkdir(shots,{recursive:true})
let server,browser
try {
  server=await createServer({root:desktop,mode:'preview-worker',logLevel:'warn'})
  await server.listen()
  browser=await chromium.launch({executablePath:process.env.LOCALLLM_BROWSER || join(process.env.ProgramFiles || 'C:\\Program Files','Google','Chrome','Application','chrome.exe')})
  const page=await browser.newPage({viewport:{width:1280,height:900},colorScheme:'dark',reducedMotion:'reduce'})
  const exceptions=[]
  page.on('pageerror',error=>exceptions.push(error.message))
  await page.goto('http://127.0.0.1:1432')
  await page.getByText('本機工作台已連線').waitFor()
  const guide=page.getByRole('dialog',{name:'開始使用 Local LLM'})
  if(await guide.isVisible()) await guide.getByRole('button',{name:'略過引導',exact:true}).click()
  if(process.env.LOCALLLM_BENCHMARK_CONTROLLED==='1') {
    const navigate=async name=>{
      const menu=page.getByTitle('導覽')
      if(await menu.isVisible()) await menu.click()
      await page.getByRole('button',{name,exact:true}).click()
    }
    await exerciseBenchmarks(page,navigate)
  } else {
  await page.getByRole('button',{name:'運算環境',exact:true}).click()
  const summary=page.locator('.benchmark-section > summary')
  await summary.focus();await page.keyboard.press('Enter')
  await page.getByRole('heading',{name:'Benchmark 歷史',exact:true}).waitFor()
  await page.getByLabel('依模型篩選').selectOption({index:1})
  await page.getByLabel('依模型篩選').selectOption('')
  const rows=page.locator('.benchmark-section .list-row')
  await rows.first().waitFor()
  const completed=rows.filter({hasText:/completed/})
  await completed.first().getByRole('button',{name:'檢視',exact:true}).click()
  await page.getByRole('region',{name:'Benchmark 結果'}).waitFor()
  await page.getByRole('region',{name:'Benchmark 結果'}).evaluate(element=>element.scrollIntoView({block:'start'}))
  if(shots) await page.screenshot({path:join(shots,'benchmark-real-history-dark.png')})
  await completed.nth(1).getByRole('button',{name:'比較',exact:true}).click()
  await page.getByRole('status').filter({hasText:/非完全等價比較|設定可比較/}).waitFor()
  for(const width of [1280,1024,800,650]) {
    await page.setViewportSize({width,height:width===800 ? 600 : width===650 ? 720 : width===1024 ? 768 : 900})
    for(const light of [false,true]) {
      if(light) await page.getByTitle('切換主題').click()
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width} ${light}`)
      if(shots && width===650 && light) {
        await page.locator('.benchmark-comparison').evaluate(element=>element.scrollIntoView({block:'start'}))
        await page.screenshot({path:join(shots,'benchmark-real-compare-light-650.png')})
      }
      if(light) await page.getByTitle('切換主題').click()
    }
  }
  await page.getByRole('button',{name:'匯出 JSON',exact:true}).click()
  await page.getByRole('status').filter({hasText:/已匯出至/}).waitFor()
  await page.getByRole('button',{name:'匯出 CSV',exact:true}).click()
  await page.getByRole('status').filter({hasText:/\.csv/}).waitFor()
  await page.getByRole('button',{name:'檢查 OpenVINO 裝置',exact:true}).click()
  await page.getByText(/後端回報 CPU、GPU/).waitFor()
  await page.getByLabel('測試模型',{exact:true}).selectOption('openvino:6801f654268e3090')
  await page.getByLabel('顯示進階參數',{exact:true}).check()
  await page.getByLabel('Warmup 次數').fill('0')
  await page.getByLabel('正式量測次數').fill('2')
  await page.getByLabel('總時間上限（秒）').fill('60')
  await page.getByLabel('文字輸出 Token').fill('8')
  await page.getByLabel('我確認以上測試負載及資源上限').check()
  await page.getByRole('button',{name:'開始 Benchmark',exact:true}).click()
  await page.getByRole('button',{name:'取消 Benchmark',exact:true}).waitFor()
  await page.getByRole('button',{name:'取消 Benchmark',exact:true}).waitFor({state:'hidden',timeout:90000})
  const verified=await page.evaluate(async()=>{
    const call=async(op,data={})=>(await (await fetch('/__desktop_dev_rpc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({op,data})})).json()).value
    const rows=await call('benchmark-list')
    return call('benchmark-get',{id:rows[0].id})
  })
  assert.equal(verified.state,'completed')
  assert.equal(verified.runs[0].measurements.length,6)
  assert.deepEqual(exceptions,[])
  console.log('PASS native Benchmark submission and 6 raw rows, SQLite history, comparison, JSON/CSV export, keyboard, four sizes and both themes')
  }
} finally {
  if(browser) await browser.close()
  if(server) await server.close()
}
