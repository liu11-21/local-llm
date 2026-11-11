import assert from 'node:assert/strict'
import { mkdir, mkdtemp, realpath, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { basename, dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'
import { createServer } from 'vite'
import { exerciseWorkflows } from './workflow-ui.mjs'

const desktop = fileURLToPath(new URL('../', import.meta.url))
const root = await realpath(tmpdir())
const profile = await mkdtemp(join(root, 'localllm-layout-'))
const port = process.env.LOCALLLM_LAYOUT_PORT || '1428'
const url = 'http://127.0.0.1:' + port
const model = 'Extremely-Long-Model-Name-' + 'ExtendedContextVersion'.repeat(5) + '-Q4_K_M.gguf'
const error = 'MODEL_CONNECTION_ERROR_'.repeat(45)
let browser, server

try {
  await mkdir(join(profile, 'models'))
  // Layout fixture only. Neither this file nor the task lifecycle below is used for inference.
  await writeFile(join(profile, 'models', model), 'layout only')
  await writeFile(join(profile, 'models', 'Protocol-Fixture-Q4_K_M.gguf'), 'protocol fixture only')
  process.env.LOCALLLM_PREVIEW_DATA = profile
  process.env.LOCALLLM_PREVIEW_PORT = port
  process.env.LOCALLLM_PREVIEW_WORKER = join(desktop,'tests','workflow_fixture.py')
  server = await createServer({root:desktop, mode:'preview-worker', logLevel:'warn'})
  await server.listen()
  browser = await chromium.launch({
    executablePath:process.env.LOCALLLM_BROWSER || join(process.env.ProgramFiles || 'C:\\Program Files',
      'Google', 'Chrome', 'Application', 'chrome.exe'),
  })
  const page = await browser.newPage({viewport:{width:1280,height:900}, colorScheme:'dark', reducedMotion:'reduce'})
  const exceptions = []
  page.on('pageerror', exception => exceptions.push(exception.message))
  let started = false
  let failed = false
  let chatSubmissions = 0
  const batch4 = process.env.LOCALLLM_BATCH4_SHOTS
  if (batch4) await mkdir(batch4,{recursive:true})
  const capture = async name => {
    if (!batch4) return
    await page.evaluate(() => window.scrollTo(0,0))
    await page.screenshot({path:join(batch4,'batch4-'+name+'.png'),fullPage:true})
  }
  await page.route('**/__desktop_dev_rpc', async route => {
    const {op, data} = route.request().postDataJSON()
    const reply = value => route.fulfill({json:{ok:true,value}})
    if (op === 'info') {
      const response = await route.fetch()
      const json = await response.json()
      assert(json.ok, json.error)
      return reply(json.value)
    }
    if (op === 'run' && data.action === 'team') {started = true; return reply({id:'layout-team'})}
    if (op === 'run' && data.action === 'chat') chatSubmissions++
    if (op === 'job' && data.id === 'layout-team') return reply({
      id:'layout-team', state:failed ? 'failed' : 'running', message:failed ? error : 'Layout fixture',
      members:['載入模型…', '等候可用資源…'],
    })
    return route.continue()
  })
  const button = name => page.getByRole('button', {name,exact:true})
  async function navigate(name) {
    const menu = page.getByTitle('導覽')
    if (await menu.isVisible()) await menu.click()
    await button(name).click()
  }
  async function noOverflow() {
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Horizontal overflow')
  }
  await page.goto(url)
  await page.getByText('本機工作台已連線').waitFor()
  await page.getByRole('region',{name:'本機資源'}).getByLabel('CPU 使用率').waitFor()
  await capture('home-dark')
  await button('收合側邊欄').click()
  assert.equal(await button('展開側邊欄').getAttribute('aria-expanded'),'false')
  await button('展開側邊欄').click()
  await page.setViewportSize({width:650,height:720})
  await page.getByTitle('切換主題').click()
  await noOverflow()
  await capture('home-light-narrow')
  await page.setViewportSize({width:1280,height:900})
  await page.getByTitle('切換主題').click()
  assert(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches &&
    getComputedStyle(document.querySelector('.workspace-head')).animationName === 'none'))
  await navigate('AI 團隊')
  for (const member of [1, 2]) await page.getByLabel('成員 ' + member + ' 模型').selectOption(model)
  await page.getByLabel('共同任務').fill('UI layout regression fixture')
  await button('執行團隊').click()
  await page.getByText('載入模型…',{exact:true}).waitFor()
  assert(started)

  for (const [width,height] of [[1280,900],[1024,768],[800,600],[650,720]]) {
    await page.setViewportSize({width,height})
    for (const theme of ['dark','light']) {
      if (await page.evaluate(() => document.documentElement.dataset.theme !== 'light') === (theme === 'light')) {
        await page.getByTitle('切換主題').click()
      }
      await page.waitForFunction(value => {
        const scheme = getComputedStyle(document.documentElement).colorScheme
        return scheme === value
      }, theme)
      await noOverflow()
      const geometry = await page.locator('.team-member').evaluateAll(rows => rows.map(row => {
        const title = row.querySelector('strong').getBoundingClientRect()
        const bounds = row.getBoundingClientRect()
        const action = row.querySelector('.team-member-actions').getBoundingClientRect()
        const selects = [...row.querySelectorAll('select')].map(select => select.getBoundingClientRect())
        return {titleHeight:title.height, titleWidth:title.width, overlap:title.right > action.left,
          controlsFit:selects.every(control => control.width >= 75 && control.right <= bounds.right + 1)}
      }))
      assert(geometry.every(item => item.titleHeight < 32 && item.titleWidth > 30 && !item.overlap && item.controlsFit),
        JSON.stringify({width,theme,geometry}))
      await page.locator('.top-tasks').focus()
      await page.keyboard.press('Tab')
      assert(await page.evaluate(() => document.activeElement.matches(':focus-visible')))
    }
  }
  failed = true
  const banner = page.getByRole('alert')
  await banner.getByText(error).waitFor()
  await noOverflow()
  await page.getByTitle('關閉訊息').click()
  await navigate('運算環境')
  await page.getByRole('heading',{name:'選擇運算來源'}).waitFor()
  assert.equal(await page.getByLabel('HTTPS 端點').count(), 0)
  const hardwareShots = process.env.LOCALLLM_HARDWARE_SHOTS
  if (hardwareShots) {
    await mkdir(hardwareShots,{recursive:true})
    await page.getByRole('heading',{name:'GPU 與 NPU',exact:true}).waitFor()
    await page.waitForTimeout(22000)
    await page.screenshot({path:join(hardwareShots,'hardware-runtime-real.png'),fullPage:true})
  }
  const hardwareMetric = (value,status='available') => ({value,source:value===null?'unknown':'detected',status})
  const hardwareFixture = {
    schema:1,state:'available',checked_at:Math.floor(Date.now()/1000),inventory_at:Math.floor(Date.now()/1000),
    npu_present:hardwareMetric(true),provider_state:'checked',provider_checked_at:null,providers:[],
    devices:[{id:'controlled-npu',kind:'npu',name:'受控 Intel NPU · '+model,vendor:'Intel',
      driver:hardwareMetric('test-driver'),driver_state:hardwareMetric(0),utilization:hardwareMetric(null,'unsupported'),
      vram_total:hardwareMetric(null,'unsupported'),vram_used:hardwareMetric(null,'unsupported'),
      vram_available:hardwareMetric(null,'unsupported'),verified_inference:false}],
  }
  await page.route('**/__desktop_dev_rpc',async route=>{
    const {op}=route.request().postDataJSON()
    if(op==='hardware-capabilities') return route.fulfill({json:{ok:true,value:hardwareFixture}})
    return route.fallback()
  })
  await button('使用本機').click()
  await page.getByText('NPU 推理待硬體驗收。一般聊天與創作可繼續使用既有 CPU／GPU 引擎。').waitFor()
  for (const [width,height] of [[1280,900],[1024,768],[800,600],[650,720]]) {
    await page.setViewportSize({width,height})
    for (const theme of ['dark','light']) {
      if (await page.evaluate(()=>getComputedStyle(document.documentElement).colorScheme)!==theme) await page.getByTitle('切換主題').click()
      await noOverflow()
      if (hardwareShots && width===650 && theme==='light') await page.screenshot({path:join(hardwareShots,'hardware-npu-controlled-light.png'),fullPage:true})
    }
  }
  hardwareFixture.npu_present=hardwareMetric(null,'unknown')
  hardwareFixture.devices=[]
  await button('連接另一台電腦').click()
  await button('使用本機').click()
  await page.getByText('NPU · 未知 · 裝置資料尚未取得',{exact:true}).waitFor()
  console.log('PASS controlled NPU presence, unknown monitoring, long names, four sizes and both themes')
  await button('連接另一台電腦').click()
  await page.getByRole('heading',{name:'將此電腦設為運算主機'}).waitFor()
  await page.getByText('尚未配對遠端電腦。').waitFor()
  await page.getByText('進階：外部 HTTPS 端點',{exact:true}).click()
  await page.getByLabel('HTTPS 端點').waitFor()
  await page.getByText('進階：外部 HTTPS 端點',{exact:true}).click()
  const remoteShots = process.env.LOCALLLM_REMOTE_SHOTS
  if (remoteShots) await mkdir(remoteShots,{recursive:true})
  for (const [width,height] of [[1280,900],[1024,768],[800,600],[650,720]]) {
    await page.setViewportSize({width,height})
    for (const theme of ['dark','light']) {
      if (await page.evaluate(() => getComputedStyle(document.documentElement).colorScheme) !== theme) {
        await page.getByTitle('切換主題').click()
      }
      await noOverflow()
      if (remoteShots && ((width === 1280 && theme === 'dark') || (width === 650 && theme === 'light'))) {
        await page.evaluate(() => window.scrollTo(0,0))
        await page.screenshot({path:join(remoteShots,'remote-'+width+'-'+theme+'.png'),fullPage:true})
      }
    }
  }
  await page.getByLabel('主機配對邀請').fill('invalid invitation')
  await button('配對主機').click()
  await page.getByRole('alert').getByText(/配對邀請無效/).waitFor()
  page.once('dialog', dialog => dialog.accept())
  await button('分享此電腦算力').click()
  const automaticInvite = page.getByLabel('複製配對邀請',{exact:true})
  await automaticInvite.waitFor()
  const identity = JSON.parse(Buffer.from(await automaticInvite.inputValue(),'base64').toString('utf-8'))
  assert.equal(identity.host,'127.0.0.1')
  await page.getByText('核對主機指紋',{exact:true}).click()
  await page.getByText(/SHA-256 [0-9A-F]{64}/).waitFor()
  await button('停止分享算力').click()
  await button('分享此電腦算力').waitFor()
  await capture('remote-sharing')
  const tls = await page.evaluate(async () => {
    const response = await fetch('/__desktop_dev_rpc',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({op:'fixture-host-credentials',data:{}})})
    return (await response.json()).value
  })
  const longHost = '家用遠端電腦'.repeat(12)
  await page.getByLabel('主機名稱',{exact:true}).fill(longHost)
  await page.getByText('進階：手動憑證與連接埠',{exact:true}).click()
  await page.getByLabel('本機私人 IPv4 位址').fill('127.0.0.1')
  await page.getByLabel('HTTPS 連接埠').fill(String(tls.port))
  await page.getByLabel('公開 PEM 憑證路徑').fill(tls.certificate)
  await page.getByLabel('PEM 私鑰路徑').fill(tls.key)
  page.once('dialog', dialog => dialog.accept())
  await button('啟用運算主機').click()
  await button('停止分享算力').waitFor()
  await page.getByText(/文字引擎 尚未載入模型/).waitFor()
  await noOverflow()
  if (remoteShots) {
    await page.evaluate(() => window.scrollTo(0,0))
    await page.screenshot({path:join(remoteShots,'remote-host-active.png'),fullPage:true})
  }
  await button('建立一次性配對邀請').click()
  const invitation = page.getByLabel('複製配對邀請',{exact:true})
  await invitation.waitFor()
  assert((await invitation.inputValue()).length > 100)
  await button('停止分享算力').click()
  await button('分享此電腦算力').waitFor()
  await page.locator('summary').filter({hasText:'比較運算環境'}).click()
  await page.getByLabel('比較任務').selectOption('notebook')
  await button('比較能力').click()
  await page.getByText(/Colab Enterprise · 需要設定/).waitFor()
  await noOverflow()
  if (remoteShots) {
    await page.setViewportSize({width:1280,height:900})
    await page.evaluate(() => window.scrollTo(0,0))
    await page.screenshot({path:join(remoteShots,'remote-compare.png'),fullPage:true})
  }
  await button('Google Colab／Notebook').click()
  await page.getByRole('heading',{name:'Google Colab Enterprise'}).waitFor()
  await noOverflow()
  await navigate('圖片生成')
  await page.getByText('生成完成後，作品會顯示在這裡。').waitFor()
  await noOverflow()
  const shots = process.env.LOCALLLM_BATCH3_SHOTS
  if (shots) await mkdir(shots,{recursive:true})
  const shot = name => shots && page.screenshot({path:join(shots,'batch3-'+name+'.png'),fullPage:true})
  for (const [width,height] of [[1280,900],[1024,768],[800,600],[650,720]]) {
    await page.setViewportSize({width,height})
    for (const theme of ['dark','light']) {
      if (await page.evaluate(() => getComputedStyle(document.documentElement).colorScheme) !== theme) {
        await page.getByTitle('切換主題').click()
      }
      await page.getByText(/Hugging Face · 固定版本/).waitFor()
      await button('下載並安裝 ComfyUI').waitFor()
      await noOverflow()
      if ((width === 1280 && theme === 'dark') || (width === 650 && theme === 'light')) {
        await shot('creation-' + width + '-' + theme)
      }
    }
  }
  assert(await page.evaluate(async () => {
    const response = await fetch('/__desktop_dev_rpc',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({op:'fixture-create-work',data:{}})})
    return (await response.json()).value
  }))
  await navigate('作品庫')
  await page.getByRole('img',{name:'生成作品'}).waitFor()
  await page.getByLabel('搜尋作品').fill('找不到這個字串')
  await page.getByText('找不到符合條件的作品。').waitFor()
  await page.getByLabel('搜尋作品').fill('雪松')
  await page.getByLabel('模型篩選').selectOption('Stable Diffusion 1.5')
  await page.getByLabel('類型',{exact:true}).selectOption('image')
  await page.getByLabel('日期排序').selectOption('oldest')
  await button('重新使用設定').waitFor()
  await noOverflow()
  await page.setViewportSize({width:1280,height:900})
  await shot('works')
  await button('重新使用設定').click()
  await page.getByRole('heading',{name:'建立圖片',exact:true}).waitFor()
  assert.equal(await page.getByLabel('提示詞',{exact:true}).inputValue(),'雪中的雪松')
  assert.equal(await page.getByLabel('寬度',{exact:true}).inputValue(),'256')
  await page.getByText('進階生成參數',{exact:true}).click()
  assert.equal(await page.getByLabel('種子（留白為隨機）').inputValue(),'417')
  console.log('PASS creation installation summary, work library filters, and saved settings replay')
  console.log('PASS workspace layout in both themes at 1280, 1024, 800, and 650 px')
  await exerciseWorkflows(page,navigate,noOverflow)
  const cloud = await page.evaluate(async () => {
    const response = await fetch('/__desktop_dev_rpc',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({op:'fixture-cloud',data:{}})})
    return (await response.json()).value
  })
  await page.setViewportSize({width:1280,height:900})
  await page.reload()
  await page.getByText('本機工作台已連線').waitFor()
  await navigate('設定')
  await page.getByLabel('預設政策').selectOption('manual')
  await navigate('文字聊天')
  await page.getByRole('region',{name:'文字聊天'}).getByLabel('運算環境',{exact:true}).selectOption(cloud)
  await page.getByLabel('訊息').fill('受控測試提示')
  await button('送出').click()
  const consent = page.getByRole('dialog',{name:'確認資料傳送'})
  await consent.getByText(/fixture.example:443 · 費用未知/).waitFor()
  await capture('transfer-review')
  await page.keyboard.press('Escape')
  await consent.waitFor({state:'hidden'})
  assert.equal(chatSubmissions,0)
  await button('送出').click()
  await consent.getByRole('button',{name:'同意並送出'}).click()
  await page.getByText('測試運算環境 · test-text',{exact:true}).waitFor()
  assert.equal(await page.getByText('受控測試回答',{exact:true}).count(),1)
  assert.equal(chatSubmissions,1)
  console.log('PASS workspace shell, resource monitor, TLS provisioning and destination consent')
  await page.evaluate(async () => {
    await fetch('/__desktop_dev_rpc',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({op:'fixture-first-use',data:{}})})
  })
  await page.reload()
  let guide = page.getByRole('dialog',{name:'開始使用 Local LLM'})
  await guide.getByRole('button',{name:'開始使用',exact:true}).click()
  await guide.getByText('CPU 執行緒',{exact:true}).waitFor()
  await page.reload()
  guide = page.getByRole('dialog',{name:'開始使用 Local LLM'})
  await guide.getByRole('button',{name:'選擇用途',exact:true}).click()
  await guide.getByRole('button',{name:'文字聊天',exact:true}).click()
  await guide.getByRole('button',{name:'一鍵準備',exact:true}).waitFor()
  const firstUseShots = process.env.LOCALLLM_FIRST_USE_SHOTS
  if (firstUseShots) {
    await mkdir(firstUseShots,{recursive:true})
    await page.screenshot({path:join(firstUseShots,'first-use-prepare.png')})
  }
  await guide.getByRole('button',{name:'一鍵準備',exact:true}).click()
  await guide.getByRole('alert').getByText('受控下載中斷').waitFor()
  await guide.getByRole('button',{name:'重試準備',exact:true}).click()
  await guide.getByRole('button',{name:'開始第一次聊天',exact:true}).click()
  await page.getByLabel('訊息').fill('第一次本機聊天')
  await button('送出').click()
  await page.getByRole('dialog',{name:'第一項任務已完成'}).waitFor()
  if(firstUseShots) await page.screenshot({path:join(firstUseShots,'first-use-complete.png')})
  await page.getByRole('dialog',{name:'第一項任務已完成'}).getByRole('button',{name:'完成',exact:true}).click()
  await page.getByText('首次對話已保存。',{exact:true}).waitFor()
  console.log('PASS first use resumes after reload, retries interrupted setup, and saves the first chat')
  const imageHost = await page.evaluate(async () => {
    const response = await fetch('/__desktop_dev_rpc',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({op:'fixture-remote-image',data:{}})})
    return (await response.json()).value
  })
  await page.reload()
  await page.getByText('本機工作台已連線').waitFor()
  await navigate('首頁')
  await button('新手引導').click()
  const completedGuide=page.getByRole('dialog',{name:'第一項任務已完成'})
  await completedGuide.getByRole('button',{name:'開始下一項任務'}).click()
  await page.getByRole('dialog',{name:'開始使用 Local LLM'}).getByRole('button',{name:'圖片生成',exact:true}).click()
  const remoteGuide=page.getByRole('dialog',{name:'開始使用 Local LLM'})
  await remoteGuide.getByRole('button',{name:'開始遠端創作',exact:true}).waitFor()
  assert.equal(await remoteGuide.getByLabel('入門推薦模型').inputValue(),imageHost+':sd15')
  if(hardwareShots) await page.screenshot({path:join(hardwareShots,'onboarding-remote-image.png')})
  await remoteGuide.getByRole('button',{name:'開始遠端創作',exact:true}).click()
  assert.equal(await page.locator('.creation').getByLabel('運算環境',{exact:true}).inputValue(),imageHost)
  await page.getByLabel('提示詞',{exact:true}).fill('受控遠端圖片')
  await page.locator('.creation').getByRole('button',{name:'生成圖片',exact:true}).click()
  await page.getByRole('dialog',{name:'確認資料傳送'}).getByText(/受控圖片主機/).waitFor()
  if(firstUseShots) await page.screenshot({path:join(firstUseShots,'remote-image-consent.png')})
  await page.getByRole('dialog',{name:'確認資料傳送'}).getByRole('button',{name:'同意並送出'}).click()
  await page.getByRole('dialog',{name:'第一項任務已完成'}).getByRole('button',{name:'完成',exact:true}).click()
  await page.getByRole('heading',{name:'本次作品'}).waitFor()
  await button('查看作品與參數').click()
  await page.getByText('受控圖片主機',{exact:true}).waitFor()
  if(firstUseShots) await page.screenshot({path:join(firstUseShots,'remote-image-library.png')})
  console.log('PASS remote image consent, verified transfer, and works-library provenance')
  await page.evaluate(async()=>{
    const response=await fetch('/__desktop_dev_rpc',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({op:'fixture-openvino',data:{}})})
    const reply=await response.json()
    if(!reply.ok) throw new Error(reply.error)
  })
  await page.reload()
  await page.getByText('本機工作台已連線').waitFor()
  await navigate('運算環境')
  await page.getByRole('heading',{name:'可選 OpenVINO 引擎',exact:true}).waitFor()
  await button('使用 OpenVINO 聊天').click()
  const openvinoChat=page.getByRole('region',{name:'文字聊天'})
  assert.equal(await openvinoChat.getByLabel('運算環境',{exact:true}).inputValue(),'openvino')
  await page.getByLabel('訊息').fill('受控本機 OpenVINO 提示詞')
  await button('送出').click()
  await page.getByText('受控 OpenVINO 回答。',{exact:true}).waitFor()
  await page.getByText(/OpenVINO ·/).waitFor()
  assert.equal(await page.getByRole('dialog',{name:'確認資料傳送'}).count(),0)
  console.log('PASS controlled OpenVINO Runtime selection, compute scheduling, local privacy and saved chat')
  assert.deepEqual(exceptions, [])
} finally {
  if (browser) await browser.close()
  if (server) await server.close()
  const target = await realpath(profile)
  if (dirname(target) === root && basename(target).startsWith('localllm-layout-')) {
    await rm(target, {recursive:true,force:true,maxRetries:4,retryDelay:250})
  }
}
