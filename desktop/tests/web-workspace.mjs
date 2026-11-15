import assert from 'node:assert/strict'
import {spawn,execFileSync} from 'node:child_process'
import {mkdtemp,readFile,mkdir,rm,writeFile,realpath} from 'node:fs/promises'
import {join,resolve,basename,sep} from 'node:path'
import {tmpdir} from 'node:os'
import {fileURLToPath} from 'node:url'
import {chromium} from 'playwright-core'

const root=resolve(fileURLToPath(new URL('../../',import.meta.url)))
const app=process.env.LOCALLLM_WEB_PACKAGE||root
const profile=process.env.LOCALLLM_WEB_TEST_DATA||await mkdtemp(join(tmpdir(),'localllm-web-test-'))
const port=Number(process.env.LOCALLLM_WEB_TEST_PORT||18771)
const python=process.env.LOCALLLM_PYTHON||'python'
const output=join(root,'build','v090-browser');await mkdir(output,{recursive:true})
let child;let serverLog='';const browsers=[];const errors=[];const results=[]
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms))
function launch(){
 child=spawn(python,['-I','-S','-B',join(app,'web_launcher.py'),'start','--data',profile,'--port',String(port),'--no-browser'],{windowsHide:true,stdio:['ignore','pipe','pipe']})
 for(const stream of [child.stdout,child.stderr])stream.on('data',data=>{serverLog+=data.toString('utf8')})
}
function state(){
 const source=`import sys,json;from pathlib import Path;sys.path.insert(0,${JSON.stringify(app)});from web_launcher import read_state;v=read_state(Path(${JSON.stringify(profile)}));print(json.dumps(v))`
 try{return JSON.parse(execFileSync(python,['-I','-S','-B','-c',source],{encoding:'utf8',windowsHide:true,stdio:['ignore','pipe','pipe']}))}catch{return null}
}
async function ready(){
 for(let i=0;i<90;i++){const value=state();if(value)return value;if(child.exitCode!==null)throw Error('Launcher exited: '+serverLog);await sleep(500)}
 throw Error('Launcher timeout: '+serverLog)
}
async function waitExit(){for(let i=0;i<60&&child.exitCode===null;i++)await sleep(250);assert.notEqual(child.exitCode,null,'Backend must exit after authenticated shutdown')}
try{
 launch();const record=await ready();const origin=`http://127.0.0.1:${port}`
 for(const [name,path] of [['Chrome',join(process.env.ProgramFiles||'C:\\Program Files','Google/Chrome/Application/chrome.exe')],['Edge',join(process.env['ProgramFiles(x86)']||'C:\\Program Files (x86)','Microsoft/Edge/Application/msedge.exe')]]){
  const browser=await chromium.launch({executablePath:path,headless:true,chromiumSandbox:true});browsers.push(browser)
  const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'})
  await context.addInitScript(()=>localStorage.setItem('localllm-onboarding-v1',JSON.stringify({stage:'skipped',task:'chat'})))
  const page=await context.newPage();page.on('pageerror',error=>errors.push(name+': '+error.message))
  await page.goto(origin+'/#bootstrap='+record.bootstrap)
  await page.getByText('本機服務已連線',{exact:true}).waitFor()
  assert(!page.url().includes(record.bootstrap),'Bootstrap credential must be removed before routing')
  assert((await context.cookies()).some(cookie=>cookie.name==='localllm_web_session'&&cookie.httpOnly&&cookie.sameSite==='Strict'))
  const anonymous=await browser.newContext();assert.equal((await anonymous.request.post(origin+'/api/rpc',{headers:{Origin:origin},data:{op:'info',data:{}}})).status(),401);await anonymous.close()
  for(const [width,height] of [[1280,900],[1024,768],[800,600],[650,720]]){
   await page.setViewportSize({width,height})
   for(const theme of ['dark','light']){
    if(await page.evaluate(()=>document.documentElement.dataset.theme)!==theme)await page.getByTitle('切換主題').click()
    for(const route of ['home','chat','agent','team','image','video','music','works','tasks','library','runtime','settings']){
     await page.evaluate(route=>location.hash='/'+route,route);await page.waitForTimeout(70)
     assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${name} overflow ${route}/${width}/${theme}`)
    }
    results.push({browser:name,width,height,theme,routes:12,status:'PASS'})
   }
  }
  await page.evaluate(()=>location.hash='/library')
  await page.getByLabel('匯入 GGUF 檔案',{exact:true}).waitFor()
  const other=await context.newPage();await other.goto(origin+'/#/library');await other.getByText('本機服務已連線',{exact:true}).waitFor()
  const fixture=Buffer.concat([Buffer.from('GGUF'),Buffer.from([3,0,0,0]),Buffer.alloc(24)])
  const filename=`Browser-Import-Fixture-${name}.gguf`
  await page.getByLabel('匯入 GGUF 檔案',{exact:true}).setInputFiles({name:filename,mimeType:'application/octet-stream',buffer:fixture})
  await page.getByText(filename.replace(/\.gguf$/,''),{exact:true}).filter({visible:true}).first().waitFor()
  await other.getByText(filename.replace(/\.gguf$/,''),{exact:true}).filter({visible:true}).first().waitFor()
  await page.setViewportSize({width:1280,height:900});await page.screenshot({path:join(output,name.toLowerCase()+'-library.png'),fullPage:true})
  await page.evaluate(()=>location.hash='/runtime');await page.getByText('文字 Runtime',{exact:true}).waitFor()
  assert.equal(await page.getByRole('button',{name:'使用舊版相容引擎',exact:true}).count(),0)
  const manifest=await (await context.request.get(origin+'/manifest.webmanifest')).json();assert.equal(manifest.display,'standalone')
  await page.evaluate(()=>navigator.serviceWorker.ready)
  await other.close();await page.close();await context.close();await browser.close()
 }
 assert.deepEqual(errors,[])
 // Exercise the command launcher, not a mocked stop callback; then restart the
 // same profile and verify sessions rotate while imported model bytes persist.
 execFileSync(python,['-I','-S','-B',join(app,'web_launcher.py'),'stop','--data',profile],{windowsHide:true,stdio:'pipe'})
 await waitExit();launch();const next=await ready();assert.notEqual(next.bootstrap,record.bootstrap)
 assert.equal((await readFile(join(profile,'models','Browser-Import-Fixture-Chrome.gguf'))).subarray(0,4).toString(),'GGUF')
 execFileSync(python,['-I','-S','-B',join(app,'web_launcher.py'),'stop','--data',profile],{windowsHide:true,stdio:'pipe'});await waitExit()
 const summary={status:'PASS',transport:'real same-origin HTTP, real SQLite; no inference in this browser layout test',
  matrix:results,upload:'controlled 32-byte GGUF header fixture; not a model inference test',
  multi_window:'real BroadcastChannel invalidation + shared core',restart:'PASS: rotated launch credential, preserved files',
  pwa:'manifest + service worker ready in Chrome/Edge; interactive OS installation not automated',self_built_exe_executed:false}
 await writeFile(join(output,'validation.json'),JSON.stringify(summary,null,2)+'\n')
 console.log('PASS real Chrome/Edge Web HTTP transport, 4 sizes x 2 themes x 12 routes, file upload, multi-window sync, PWA readiness and clean restart')
}catch(error){console.error(error);throw error}finally{
 for(const browser of browsers)await browser.close().catch(()=>{})
 if(child&&child.exitCode===null){try{execFileSync(python,['-I','-S','-B',join(app,'web_launcher.py'),'stop','--data',profile],{windowsHide:true,stdio:'pipe'})}catch{child.kill()}await waitExit()}
 if(!process.env.LOCALLLM_WEB_TEST_DATA){const target=await realpath(profile);const temporary=await realpath(tmpdir());assert(target.startsWith(temporary+sep)&&basename(target).startsWith('localllm-web-test-'));await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:200})}
}
