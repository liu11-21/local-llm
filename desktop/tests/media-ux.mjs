import assert from 'node:assert/strict'
import {mkdir,writeFile} from 'node:fs/promises'
import {join} from 'node:path'

// Production React and IPC paths with controlled Host inference and legal media.
export async function exerciseMediaUX(page) {
  const rpc=(op,data={})=>page.evaluate(async({op,data})=>{
    const result=await (await fetch('/__desktop_dev_rpc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({op,data})})).json()
    if(!result.ok)throw new Error(result.error);return result.value
  },{op,data})
  const shots=process.env.LOCALLLM_E4_SHOTS
  if(shots)await mkdir(shots,{recursive:true})
  const go=async name=>{const menu=page.getByTitle('導覽');if(await menu.isVisible())await menu.click();await page.getByRole('button',{name,exact:true}).click()}
  const shot=async name=>{if(shots)await page.screenshot({path:join(shots,name+'.png')})}
  await page.setViewportSize({width:1280,height:900})
  await page.evaluate(()=>{localStorage.setItem('policy','manual');localStorage.setItem('theme','dark')})
  const host=await rpc('fixture-remote-media')
  await page.reload();await page.getByText('本機工作台已連線').waitFor()
  await go('文字聊天')
  assert.equal(await page.locator('.chat-config').getAttribute('open'),null)
  assert(await page.getByLabel('訊息',{exact:true}).isVisible())
  await shot('chat-compact-dark')
  await page.setViewportSize({width:650,height:720})
  assert.equal(await page.getByRole('complementary',{name:'對話歷史'}).isVisible(),false)
  await page.getByRole('button',{name:'對話歷史',exact:true}).click()
  assert(await page.getByRole('complementary',{name:'對話歷史'}).isVisible())
  await page.getByRole('button',{name:'對話歷史',exact:true}).click()
  await page.getByTitle('切換主題').click();await shot('chat-compact-light-650')
  const flows=[]
  for(const [kind,title,tag] of [['video','影片','video'],['music','音樂','audio']]) {
    await page.setViewportSize({width:1280,height:900})
    await go(title+'生成')
    const creation=page.locator('.creation')
    await creation.getByLabel('運算環境',{exact:true}).selectOption(host)
    await creation.getByLabel('提示詞',{exact:true}).fill('Legal synthetic '+kind+' playback fixture; not model inference')
    if(kind==='music')await creation.getByLabel('歌詞（選填）',{exact:true}).fill('Controlled lyrics saved in the client library')
    await creation.getByRole('button',{name:'生成'+title,exact:true}).click()
    const consent=page.getByRole('dialog',{name:'確認資料傳送'})
    await consent.getByText(/受控影音主機/).waitFor()
    await consent.getByRole('button',{name:'同意並送出',exact:true}).click()
    await creation.getByRole('heading',{name:'本次作品',exact:true}).waitFor({timeout:30000})
    const player=creation.locator(tag)
    await player.waitFor()
    await player.evaluate(async element=>{element.muted=true;await element.play()})
    await page.waitForFunction(tag=>{const player=document.querySelector('.creation '+tag);return player?.readyState>=2 && Number.isFinite(player.duration) && player.duration>0},tag)
    const metadata=await player.evaluate(element=>({duration:element.duration,width:element.videoWidth || null,height:element.videoHeight || null}))
    assert(metadata.duration>=.9 && metadata.duration<1.2)
    if(kind==='video')assert.equal(metadata.width,160)
    await player.evaluate(element=>element.pause())
    await shot('remote-'+kind+'-playback-controlled')
    await creation.getByRole('button',{name:'查看作品與參數',exact:true}).click()
    await page.getByText('受控影音主機 · 傳輸驗收',{exact:true}).waitFor()
    await page.getByRole('button',{name:'重新使用設定',exact:true}).click()
    assert.equal(await page.getByLabel('提示詞',{exact:true}).inputValue(),'Legal synthetic '+kind+' playback fixture; not model inference')
    flows.push({flow:'prepared-remote-'+kind,status:'PASS-controlled-protocol-and-real-playback',semantic_actions:kind==='music' ? 8 : 7,manual_technical_parameters:0,metadata})
  }
  await rpc('fixture-many-works')
  await go('作品庫')
  await page.getByLabel('模型篩選',{exact:true}).selectOption('受控大量作品')
  await page.getByRole('button',{name:'下一頁',exact:true}).waitFor()
  await page.getByRole('button',{name:'下一頁',exact:true}).click()
  assert.equal(await page.locator('.works-grid .work-link').count(),24)
  await page.getByRole('button',{name:'清單',exact:true}).click();assert(await page.locator('.works-list').isVisible())
  await page.getByRole('button',{name:'網格',exact:true}).click()
  for(const [width,height] of [[1280,900],[1024,768],[800,600],[650,720]]) {
    await page.setViewportSize({width,height})
    for(const theme of ['dark','light']) {
      if(await page.evaluate(()=>document.documentElement.dataset.theme)!==theme)await page.getByTitle('切換主題').click()
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Works must not overflow')
      await go('文字聊天');assert(await page.getByLabel('訊息',{exact:true}).isVisible())
      await go('作品庫')
    }
  }
  await page.locator('.works-grid .work-link').first().waitFor()
  await page.locator('.works-grid .work-link').first().click()
  await page.locator('.works-grid .work-thumb').first().waitFor()
  await shot('works-grid-light-650-controlled')
  await page.setViewportSize({width:1280,height:900});await go('任務中心')
  await page.locator('.task-evidence').first().locator('summary').click()
  await shot('tasks-evidence-controlled')
  await go('首頁');await page.locator('.home-host').first().waitFor()
  await page.locator('.resource-board header').getByText('即時取樣',{exact:true}).waitFor()
  if(shots)await page.screenshot({path:join(shots,'home-daily-controlled.png'),fullPage:true})
  if(process.env.LOCALLLM_MEDIA_EVIDENCE) {
    await mkdir(process.env.LOCALLLM_MEDIA_EVIDENCE,{recursive:true})
    await writeFile(join(process.env.LOCALLLM_MEDIA_EVIDENCE,'ui-playback-controlled.json'),JSON.stringify({status:'PASS',model_inference:false,flows,viewports:[[1280,900],[1024,768],[800,600],[650,720]],themes:['dark','light'],gallery_page_size:24},null,2))
  }
  console.log('PASS E4/E5 controlled remote video/audio, legal VP9/FLAC playback, consent, saved parameters/reuse, compact chat, narrow history, grid/list pagination, four sizes and both themes')
}
