// Opt-in acceptance using an already-existing signed binary, never downloads it.
// A manually supplied SDK is NOT evidence of installed PATH discovery or SAC.
import assert from 'node:assert/strict'
import {spawn,execFileSync} from 'node:child_process'
import {mkdtemp,readFile,mkdir,rm,writeFile,realpath} from 'node:fs/promises'
import {join,resolve,basename,sep} from 'node:path'
import {tmpdir} from 'node:os'
import {fileURLToPath} from 'node:url'
import {chromium} from 'playwright-core'

const root=resolve(fileURLToPath(new URL('../../',import.meta.url)))
assert(process.env.LOCALLLM_RUNTIME_EXISTING,'Provide an existing llama.exe; this test never installs one')
const executable=await realpath(process.env.LOCALLLM_RUNTIME_EXISTING)
const temporary=await realpath(tmpdir()),profile=await realpath(await mkdtemp(join(temporary,'localllm-runtime-qa-')))
const python=process.env.LOCALLLM_PYTHON||'python',port=18779,origin=`http://127.0.0.1:${port}`
const output=join(root,'build/runtime-detection-real');await mkdir(output,{recursive:true})
let child,browser,log=''
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
function state(){
 const source=`import sys,json;from pathlib import Path;sys.path.insert(0,${JSON.stringify(root)});from web_launcher import read_state;print(json.dumps(read_state(Path(${JSON.stringify(profile)}))))`
 try{return JSON.parse(execFileSync(python,['-I','-S','-B','-c',source],{encoding:'utf8',windowsHide:true,stdio:'pipe'}))}catch{return null}
}
async function start(){
 child=spawn(python,['-I','-S','-B',join(root,'web_launcher.py'),'start','--data',profile,'--port',String(port),'--no-browser'],{windowsHide:true,stdio:['ignore','pipe','pipe']})
 for(const stream of [child.stdout,child.stderr])stream.on('data',data=>{log+=data.toString('utf8')})
 for(let i=0;i<90;i++){const value=state();if(value)return value;if(child.exitCode!==null)throw Error('Launcher exited: '+log);await sleep(500)}
 throw Error('Launcher timeout: '+log)
}
async function stop(){
 execFileSync(python,['-I','-S','-B',join(root,'web_launcher.py'),'stop','--data',profile],{windowsHide:true,stdio:'pipe'})
 for(let i=0;i<60&&child.exitCode===null;i++)await sleep(250)
 assert.notEqual(child.exitCode,null)
}
try{
 let launch=await start()
 browser=await chromium.launch({executablePath:join(process.env.ProgramFiles||'C:\\Program Files','Google/Chrome/Application/chrome.exe'),headless:true})
 const context=await browser.newContext({viewport:{width:1280,height:900}})
 await context.addInitScript(()=>{if(location.protocol==='http:')localStorage.setItem('localllm-onboarding-v1',JSON.stringify({stage:'skipped',task:'chat'}))})
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message))
 await page.goto(origin+'/#bootstrap='+launch.bootstrap);await page.getByText('本機服務已連線',{exact:true}).waitFor()
 const rpc=(op,data={})=>page.evaluate(async({op,data})=>{
  const session=await (await fetch('/api/session')).json()
  return (await fetch('/api/rpc',{method:'POST',headers:{'Content-Type':'application/json','X-Workspace-CSRF':session.value.csrf},body:JSON.stringify({op,data})})).json()
 },{op,data})
 await page.evaluate(()=>location.hash='/runtime')
 for(let i=0;i<200;i++){const s=await rpc('runtime-status');if(s.value.scan.state==='complete')break;await sleep(400)}
 const discovered=(await rpc('runtime-status')).value
 assert.equal(discovered.scan.state,'complete')
 await page.getByText('選擇引擎與信任證據',{exact:true}).click()
 await page.getByLabel('已安裝的 llama.exe',{exact:true}).fill(executable)
 await page.getByRole('button',{name:'檢查並切換新版',exact:true}).click()
 await page.getByRole('region',{name:'已安裝的 Runtime',exact:true}).getByRole('button',{name:'已選取',exact:true}).waitFor({timeout:90000})
 await page.reload();await page.getByText('本機服務已連線',{exact:true}).waitFor()
 await page.evaluate(()=>location.hash='/runtime')
 await page.getByRole('region',{name:'已安裝的 Runtime',exact:true}).getByRole('button',{name:'已選取',exact:true}).waitFor({timeout:90000})
 const selected=(await rpc('runtime-status')).value,info=(await rpc('info')).value
 assert.equal(selected.selection.path.toLowerCase(),executable.toLowerCase())
 assert.equal(selected.selection.validation.authenticode.status,'Valid')
 assert.equal(info.llama_runtime.selection.path,selected.selection.path);assert.equal(info.models.length,0)
 await page.evaluate(()=>location.hash='/chat')
 assert(await page.getByRole('button',{name:'送出',exact:true}).isDisabled())
 await page.screenshot({path:join(output,'no-model-chat.png'),fullPage:true})
 await stop();launch=await start()
 await page.goto('about:blank')
 await page.goto(origin+'/#bootstrap='+launch.bootstrap);await page.getByText('本機服務已連線',{exact:true}).waitFor()
 const restored=(await rpc('runtime-status')).value
 assert.equal(restored.selection.sha256,selected.selection.sha256);assert.deepEqual(errors,[])
 const scrub=value=>JSON.parse(JSON.stringify(value).replaceAll(root.replaceAll('\\','/'),'[REPOSITORY]').replaceAll(root.replaceAll('/','\\').replaceAll('\\','\\\\'),'[REPOSITORY]'))
 await writeFile(join(output,'validation.json'),JSON.stringify(scrub({status:'PASS',scope:'manual existing SDK only; not installed PATH or target RTX/SAC acceptance',
  installed_candidates:discovered.candidates.length,selected: selected.candidates.find(c=>c.selected),
  browser_reload:'PASS',backend_restart:'PASS',chat_reads_selection:'PASS',models:info.models.length,
  runtime_downloads:0,model_downloads:0,inference:false,target_RTX_SAC:'BLOCKED',interactive_file_picker:'NOT VERIFIED'}),null,2)+'\n')
 await stop();console.log('PASS real manual existing signed Runtime, CLI, browser selection/reload, backend restart, shared chat config and no-model state; no inference/downloads; target PATH/RTX/SAC remains BLOCKED')
}finally{
 if(browser)await browser.close().catch(()=>{})
 if(child&&child.exitCode===null)try{await stop()}catch{child.kill()}
 const target=await realpath(profile);assert(target.startsWith(temporary+sep)&&basename(target).startsWith('localllm-runtime-qa-'))
 await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:200})
}
