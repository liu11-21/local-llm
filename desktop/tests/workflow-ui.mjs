import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { join } from 'node:path'

export async function exerciseWorkflows(page, navigate, noOverflow) {
  const shots = process.env.LOCALLLM_WORKFLOW_SHOTS
  if (shots) await mkdir(shots, {recursive:true})
  const shot = name => shots && page.screenshot({path:join(shots,'batch2-'+name+'.png'), fullPage:true})
  const button = name => page.getByRole('button',{name,exact:true})
  const heading = name => page.getByRole('heading',{name,exact:true})
  const timeline = page.getByRole('region',{name:'執行時間軸'})
  const fixture = 'Protocol-Fixture-Q4_K_M.gguf'

  async function theme(name) {
    if (await page.evaluate(() => getComputedStyle(document.documentElement).colorScheme) !== name) {
      await page.getByTitle('切換主題').click()
    }
    await page.waitForFunction(value => getComputedStyle(document.documentElement).colorScheme === value,name)
  }
  async function closeNotice() {
    const close = page.getByTitle('關閉訊息')
    if (await close.isVisible()) await close.click()
  }
  async function plan(prompt, mode = 'structured') {
    await page.getByLabel('代理人模式').selectOption(mode)
    await page.getByRole('combobox',{name:'本機模型',exact:true}).selectOption(fixture)
    const models = page.getByRole('checkbox',{name:'已安裝模型清單',exact:true})
    await models.check()
    await page.getByLabel('任務描述').fill(prompt)
    await button('預覽執行計畫').click()
    await button('核准並執行').waitFor()
  }

  await page.setViewportSize({width:1280,height:900})
  await theme('dark')
  await navigate('AI 代理人')
  await plan('請整理工作台已安裝的模型。')
  await shot('agent-plan')
  await button('核准並執行').click()
  await heading('核准這次工具調用').waitFor()
  await shot('agent-approval')
  await button('允許這一次').click()
  await heading('最終回答').waitFor()
  await page.getByText('協定測試完成，已讀取並保存模型清單。',{exact:true}).waitFor()
  await closeNotice()
  await page.setViewportSize({width:1024,height:768})
  await theme('light')
  await shot('agent-timeline')

  await plan('確認原生工具協定。','native')
  await button('核准並執行').click()
  await heading('核准這次工具調用').waitFor()
  await button('允許這一次').click()
  await page.getByText('原生協定測試已取得本機工具資料。',{exact:true}).waitFor()

  await plan('FAIL · 模型格式錯誤')
  await button('核准並執行').click()
  await timeline.getByRole('alert').waitFor()
  assert.match(await timeline.getByRole('alert').textContent(),/AGENT_FORMAT/)
  await closeNotice()
  await shot('agent-error')
  await plan('取消等待工具核准的工作。')
  await button('核准並執行').click()
  await heading('核准這次工具調用').waitFor()
  await button('取消代理人任務').click()
  await timeline.getByText('取消',{exact:true}).waitFor()
  assert.equal(await heading('核准這次工具調用').count(),0)

  await page.setViewportSize({width:1280,height:900})
  await theme('dark')
  await navigate('AI 團隊')
  await button('角色與工作流程').click()
  await page.getByLabel('團隊範本').selectOption('code')
  await page.getByLabel('角色 1 模型').selectOption(fixture)
  await page.getByLabel('角色 2 模型').selectOption(fixture)
  await page.getByText('角色設定 · m1',{exact:true}).click()
  await page.locator('.team-profile').first().getByLabel('顯示名稱').fill('程式碼撰寫者')
  await page.locator('.team-profile').first().getByLabel('角色目標').fill('保留需求與驗收步驟')
  await shot('team-roles')
  await page.getByText('角色設定 · m1',{exact:true}).click()
  await page.getByLabel('工作模式').selectOption('delegated')
  await button('預覽依賴').click()
  await page.getByText('分工規劃',{exact:true}).waitFor()
  await page.getByLabel('工作模式').selectOption('review')
  await button('保存設定').click()
  await heading('已驗證的工作流程').waitFor()
  await shot('team-workflow')
  await page.getByLabel('團隊共同任務').fill('審查登入流程並整理修正版。')
  await button('執行角色流程').click()
  await heading('最終整合結果').waitFor()
  await page.getByText('查看交叉審查輸出',{exact:true}).click()
  await page.getByText('測試審查：補上可驗證依據，並說明尚存限制。',{exact:true}).waitFor()
  await page.setViewportSize({width:1024,height:768})
  await theme('light')
  await shot('team-review')

  await page.getByLabel('團隊共同任務').fill('FAIL · 審查節點錯誤')
  await button('執行角色流程').click()
  await page.getByText(/controlled reviewer failure/).waitFor()
  await heading('最終整合結果').waitFor()
  await page.setViewportSize({width:650,height:720})
  await noOverflow()
  await shot('team-error')

  await page.getByLabel('團隊共同任務').fill('CANCEL · 等候審查')
  await button('執行角色流程').click()
  await page.getByText('交叉審查 · 審查者 執行中',{exact:true}).waitFor()
  await button('取消角色流程').click()
  await page.getByRole('heading',{name:/程式碼審查 · 已取消/}).waitFor()
  await noOverflow()
  console.log('PASS Agent approval, SSE tool protocol, timeline, format error and cancellation; Team roles, modes, review, partial failure and cancellation')
}
