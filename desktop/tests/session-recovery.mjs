import assert from 'node:assert/strict'
import {spawn,execFileSync} from 'node:child_process'
import {mkdtemp,readFile,mkdir,rm,writeFile,realpath} from 'node:fs/promises'
import {join,resolve,basename,sep} from 'node:path'
import {tmpdir} from 'node:os'
import {fileURLToPath} from 'node:url'
import {build} from 'vite'
import {chromium} from 'playwright-core'

const root=resolve(fileURLToPath(new URL('../../',import.meta.url))),desktop=join(root,'desktop')
const app=process.env.LOCALLLM_WEB_PACKAGE?await realpath(process.env.LOCALLLM_WEB_PACKAGE):root
const baseline=process.env.LOCALLLM_SESSION_BASELINE==='1'
const temporary=await realpath(tmpdir()),profile=await realpath(await mkdtemp(join(temporary,'localllm-session-')))
const python=process.env.LOCALLLM_PYTHON||'python',port=18781,origin=`http://127.0.0.1:${port}`
const output=join(root,'build/session-recovery');await mkdir(output,{recursive:true})
const observations=[],errors=[],checks={},secrets=[];let child,browser,log=''
const redact=text=>secrets.reduce((value,secret)=>value.replaceAll(secret,'[REDACTED]'),String(text))
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
function state(){const code=`import sys,json;from pathlib import Path;sys.path.insert(0,${JSON.stringify(app)});from web_launcher import read_state;print(json.dumps(read_state(Path(${JSON.stringify(profile)}))))`;try{return JSON.parse(execFileSync(python,['-I','-S','-B','-c',code],{encoding:'utf8',windowsHide:true,stdio:'pipe',timeout:5000}))}catch{return null}}
async function start(){
 child=spawn(python,['-I','-S','-B',join(desktop,'tests/session-server.py'),'--app',app,'--data',profile,'--port',String(port),...(!baseline?['--transport',join(output,'transport/transport-test.js')]:[])],{windowsHide:true,stdio:['ignore','pipe','pipe']})
 for(const stream of [child.stdout,child.stderr])stream.on('data',data=>{log+=data.toString('utf8')})
 for(let i=0;i<100;i++){const v=state();if(v){secrets.push(v.bootstrap);return v}if(child.exitCode!==null)throw Error('Session test host exited: '+log);await sleep(300)}throw Error('Session host timeout')
}
async function stop(){execFileSync(python,['-I','-S','-B',join(app,'web_launcher.py'),'stop','--data',profile],{windowsHide:true,stdio:'pipe',timeout:15000});for(let i=0;i<100&&child.exitCode===null;i++)await sleep(150);assert.notEqual(child.exitCode,null)}
try{
 if(!baseline)await build({root:desktop,configFile:false,mode:'web',logLevel:'error',build:{outDir:join(output,'transport'),emptyOutDir:true,minify:false,lib:{entry:join(desktop,'src/transport.ts'),formats:['es'],fileName:()=> 'transport-test.js'}}})
 let record=await start()
 browser=await chromium.launch({executablePath:process.env.LOCALLLM_BROWSER||join(process.env.ProgramFiles||'C:\\Program Files','Google/Chrome/Application/chrome.exe'),headless:true})
 const context=await browser.newContext({viewport:{width:1280,height:900}})
 await context.addInitScript(()=>{if(location.protocol==='http:')localStorage.setItem('localllm-onboarding-v1',JSON.stringify({stage:'skipped',task:'chat'}))})
 const page=await context.newPage();page.setDefaultTimeout(15000);page.setDefaultNavigationTimeout(15000);page.on('pageerror',e=>errors.push(e.message))
 const logRequests=[]
 page.on('response',r=>{const u=new URL(r.url());if(u.pathname.startsWith('/api/')){
  const row={path:u.pathname,status:r.status(),origin:r.request().headers().origin||null,host:u.host};observations.push(row)
  if(r.status()>=400)logRequests.push(Promise.race([r.json(),sleep(1000).then(()=>null)]).then(body=>{if(body){row.error=redact(body.error||'');row.code=body.code||null}}).catch(()=>{}))
 }})
 const launchPath=baseline?'/':'/launch'
 await page.goto(origin+launchPath+'#bootstrap='+record.bootstrap);await page.getByText('本機服務已連線',{exact:true}).waitFor()
 checks.first_start='PASS';await page.reload();await page.getByText('本機服務已連線',{exact:true}).waitFor();checks.reload='PASS'
 const firstToken=record.bootstrap
 const prior=await page.evaluate(async()=>{const s=await(await fetch('/api/session')).json();return s.value.csrf})
 await stop();record=await start();assert.notEqual(record.bootstrap,firstToken)
 const failed=await page.evaluate(async csrf=>{const r=await fetch('/api/rpc',{method:'POST',headers:{'Content-Type':'application/json','X-Workspace-CSRF':csrf},body:JSON.stringify({op:'info',data:{}})});return r.status},prior)
 assert.equal(failed,401)
 if(!baseline){await page.getByRole('dialog',{name:'恢復工作階段',exact:true}).waitFor();checks.restart_invalid_session_detected='PASS'}
 // Same-document navigation reproduces the original blocker. Do not use about:blank/reload.
 await page.goto(origin+launchPath+'#bootstrap='+record.bootstrap)
 if(baseline){
  await sleep(1000);const status=await page.evaluate(async()=> (await fetch('/api/session')).status)
  assert.equal(status,401);assert(page.url().includes('bootstrap='))
  await Promise.allSettled(logRequests)
  await writeFile(join(output,'BEFORE.json'),JSON.stringify({status:'FAIL',expected_reproduction:'PASS',baseline:'fe2a363',http:observations,same_document_bootstrap_consumed:false,old_session_status:status,console:errors.map(redact)},null,2)+'\n')
  console.log('PASS reproduced old FE/HTTP session failure; no authorization policy was relaxed')
 }else{
  await page.getByText('本機服務已連線',{exact:true}).waitFor();assert(!page.url().includes('bootstrap='));checks.restart_same_document='PASS'
  const other=await context.newPage();await other.goto(origin+'/#/chat');await other.getByText('本機服務已連線',{exact:true}).waitFor()
  await writeFile(join(profile,'expire-session'),'expire controlled test sessions')
  await sleep(250)
  await page.getByRole('dialog',{name:'恢復工作階段',exact:true}).waitFor();checks.expiry_detected_without_reload='PASS'
  await page.reload();await page.getByRole('dialog',{name:'恢復工作階段',exact:true}).waitFor();checks.expiry_gate='PASS'
  const otherReauthenticated=other.waitForResponse(r=>new URL(r.url()).pathname==='/api/session'&&r.request().method()==='GET'&&r.status()===200)
  await page.goto(origin+launchPath+'#bootstrap='+record.bootstrap);await page.getByText('本機服務已連線',{exact:true}).waitFor()
  await otherReauthenticated;await other.getByText('本機服務已連線',{exact:true}).waitFor();checks.reauth_and_multi_tab='PASS'
  const job=JSON.parse(await readFile(join(profile,'test-job.json'),'utf8')).id
  let requests=0;await page.route('**/api/jobs/*/events',async route=>{requests++;if(requests===1)return route.abort();return route.continue()})
  await page.evaluate(async id=>{const t=await import('/transport-test.js');await t.initializeWeb();window.sessionTransport=t;window.sessionAdapter=new t.WebHTTPAdapter();await window.sessionAdapter.request('job',{id})},job)
  for(let i=0;i<60&&requests<2;i++)await sleep(100)
  assert(requests>=2,'SSE must reconnect after the controlled dropped connection');checks.sse_reconnect='PASS'
  const cancel=await page.evaluate(async id=>await window.sessionAdapter.request('cancel',{id}),job);assert(cancel.ok);assert.equal(cancel.value.id,job)
  for(let i=0;i<50;i++){const r=await page.evaluate(async id=>await window.sessionAdapter.request('job',{id}),job);if(r.value?.state==='cancelled')break;await sleep(100);if(i===49)assert.fail('Controlled waiting task did not cancel')}
  checks.cancel='PASS'
  // A second login rotates cookie/CSRF; the old tab must refresh, never replay a write.
  await other.goto(origin+'/#bootstrap='+record.bootstrap);await other.getByText('本機服務已連線',{exact:true}).waitFor()
  const session=await page.evaluate(async()=>await window.sessionTransport.webSession());assert(session.csrf)
  const stale=await page.evaluate(async csrf=>{const r=await fetch('/api/rpc',{method:'POST',headers:{'Content-Type':'application/json','X-Workspace-CSRF':csrf},body:JSON.stringify({op:'info',data:{}})});return {status:r.status,body:await r.json()}},prior)
  assert.equal(stale.status,403);assert.equal(stale.body.code,'CSRF_INVALID');checks.stale_csrf_rejected='PASS'
  // Rotate the browser cookie without a BroadcastChannel notice to create a real
  // stale-CSRF transport request. It may refresh credentials, never replay a write.
  await page.evaluate(async()=>await window.sessionTransport.webSession())
  await context.request.post(origin+'/api/session',{headers:{Origin:origin,'X-Workspace-Bootstrap':record.bootstrap},data:{}})
  let writes=0
  const countWrite=request=>{if(request.method()==='POST'&&new URL(request.url()).pathname==='/api/rpc'){const b=request.postDataJSON();if(b?.op==='run'&&b.data?.action==='engine-stop')writes++}}
  page.on('request',countWrite)
  const rejected=await page.evaluate(async()=>{try{await window.sessionTransport.webPost('/api/rpc',{op:'run',data:{action:'engine-stop'}});return ''}catch(e){return e.message}})
  assert(rejected.includes('沒有重送'));assert.equal(writes,1);page.off('request',countWrite);checks.write_not_replayed='PASS'
  const anonymous=await browser.newContext();assert.equal((await anonymous.request.post(origin+'/api/rpc',{headers:{Origin:origin},data:{op:'info',data:{}}})).status(),401);await anonymous.close()
  for(const headers of [{Origin:'http://localhost:'+port},{Origin:'https://evil.test'},{Origin:origin,Host:'evil.test:'+port}])assert.equal((await context.request.post(origin+'/api/rpc',{headers,data:{op:'info',data:{}}})).status(),403)
  checks.security='PASS'
  await page.evaluate(async()=>await window.sessionTransport.logoutWeb())
  await page.getByRole('dialog',{name:'恢復工作階段',exact:true}).waitFor();await other.getByRole('dialog',{name:'恢復工作階段',exact:true}).waitFor();checks.logout_multi_tab='PASS'
  assert(!(await context.cookies()).some(cookie=>cookie.name===`localllm_web_session_${port}`));checks.logout_cookie_cleared='PASS'
  await page.goto(origin+'/#bootstrap='+record.bootstrap);await page.getByText('本機服務已連線',{exact:true}).waitFor();checks.login_after_logout='PASS'
  await page.evaluate(()=>location.hash='/library');await page.getByLabel('匯入 GGUF 檔案',{exact:true}).waitFor();checks.library_access='PASS'
  assert.deepEqual(errors,[])
  await Promise.allSettled(logRequests)
  await writeFile(join(output,'SESSION_RECOVERY_TESTS.json'),JSON.stringify({status:'PASS',scope:'real official Python / SQLite / HTTP / Chrome; waiting TaskManager fixture for SSE and cancel, no AI inference',checks,http:observations,console:errors,network_log:'paths/status/origin/error only; credentials omitted',target_RTX:'BLOCKED: specified desktop QA directory is not on this host'},null,2)+'\n')
  console.log('PASS real browser session reload/restart/expiry/reauth/multi-tab/logout, transport SSE reconnect/cancel and security boundaries')
 }
 await stop()
}catch(error){error.message=redact(error.message);if(error.stack)error.stack=redact(error.stack);throw error}finally{
 if(browser)await browser.close().catch(()=>{})
 if(child&&child.exitCode===null)try{await stop()}catch{child.kill()}
 const target=await realpath(profile);assert(target.startsWith(temporary+sep)&&basename(target).startsWith('localllm-session-'));await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:200})
}
