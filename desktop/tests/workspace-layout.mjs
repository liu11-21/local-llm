import assert from 'node:assert/strict'
import { mkdir, mkdtemp, realpath, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { basename, dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'
import { createServer } from 'vite'

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
  process.env.LOCALLLM_PREVIEW_DATA = profile
  process.env.LOCALLLM_PREVIEW_PORT = port
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
  await page.route('**/__desktop_dev_rpc', async route => {
    const {op, data} = route.request().postDataJSON()
    const reply = value => route.fulfill({json:{ok:true,value}})
    if (op === 'info') {
      const response = await route.fetch()
      const json = await response.json()
      assert(json.ok, json.error)
      return reply({...json.value, engine:true})
    }
    if (op === 'run' && data.action === 'team') {started = true; return reply({id:'layout-team'})}
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
  await button('連接另一台電腦').click()
  await page.getByLabel('HTTPS 端點').waitFor()
  await button('Google Colab／Notebook').click()
  await page.getByRole('heading',{name:'Google Colab Enterprise'}).waitFor()
  await noOverflow()
  await navigate('圖片生成')
  await page.getByText('生成完成後，作品會顯示在這裡。').waitFor()
  await noOverflow()
  assert.deepEqual(exceptions, [])
  console.log('PASS workspace layout in both themes at 1280, 1024, 800, and 650 px')
} finally {
  if (browser) await browser.close()
  if (server) await server.close()
  const target = await realpath(profile)
  if (dirname(target) === root && basename(target).startsWith('localllm-layout-')) {
    await rm(target, {recursive:true,force:true,maxRetries:4,retryDelay:250})
  }
}
