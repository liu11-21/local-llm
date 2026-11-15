import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {resolve,join} from 'node:path'
import {fileURLToPath} from 'node:url'
import {writeFile,mkdir} from 'node:fs/promises'
import {chromium} from 'playwright-core'

const root=resolve(fileURLToPath(new URL('../../',import.meta.url)))
const profile=process.argv[2];assert(profile,'Explicit synthetic test profile required')
const python=process.env.LOCALLLM_PYTHON||'python'
const code=`import sys,json;from pathlib import Path;sys.path.insert(0,${JSON.stringify(root)});from web_launcher import read_state;print(json.dumps(read_state(Path(${JSON.stringify(profile)}))))`
const state=JSON.parse(execFileSync(python,['-I','-S','-B','-c',code],{encoding:'utf8',windowsHide:true}));assert(state)
const browser=await chromium.launch({executablePath:join(process.env.ProgramFiles||'C:\\Program Files','Google/Chrome/Application/chrome.exe'),headless:true,chromiumSandbox:true})
try{
 const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'})
 await context.addInitScript(()=>localStorage.setItem('localllm-onboarding-v1',JSON.stringify({stage:'skipped',task:'chat'})))
 const page=await context.newPage();const failures=[];page.on('pageerror',error=>failures.push(error.message))
 await page.goto(`http://127.0.0.1:${state.port}/#bootstrap=${state.bootstrap}`)
 await page.getByText('本機服務已連線',{exact:true}).waitFor();await page.evaluate(()=>location.hash='/chat')
 const chat=page.getByRole('region',{name:'文字聊天',exact:true})
 await chat.locator('.chat-config').evaluate(node=>{node.open=true})
 await chat.getByLabel('運算環境',{exact:true}).selectOption('local')
 await chat.getByLabel('模型',{exact:true}).selectOption('Qwen3-0.6B-Q4_0.gguf')
 await chat.getByText('生成參數',{exact:true}).click()
 await chat.getByLabel('本機裝置',{exact:true}).selectOption('cpu')
 await chat.getByLabel('最大輸出 Token',{exact:true}).fill('64')
 await chat.getByLabel('Thinking（需模型範本支援，預設關閉）',{exact:true}).uncheck()
 await chat.getByLabel('訊息',{exact:true}).fill('請只輸出以下繁體文字：瀏覽器真實推理成功。')
 await chat.getByRole('button',{name:'送出',exact:true}).click()
 await chat.locator('.message.assistant .markdown').waitFor({timeout:90000})
 await chat.getByRole('button',{name:'送出',exact:true}).waitFor({timeout:90000})
 assert.deepEqual(failures,[])
 const answer=await chat.locator('.message.assistant .markdown').last().innerText();assert(answer.trim())
 const output=join(root,'build/v090-browser');await mkdir(output,{recursive:true})
 await chat.locator('.chat-config').evaluate(node=>{node.open=false})
 await chat.locator('.compose-footer > details').evaluate(node=>{node.open=false})
 await page.evaluate(()=>window.scrollTo(0,0))
 await page.screenshot({path:join(output,'chrome-chat-real.png'),fullPage:false})
 await writeFile(join(output,'chat-real.json'),JSON.stringify({status:'PASS',browser:'Chrome',model:'Qwen3-0.6B Q4_0',backend:'CPU',
  scope:'Actual React composer -> authenticated HTTP -> shared scheduler -> signed llama.app -> SSE browser render',answer,
  note:'Single synthetic instruction; not a quality benchmark or RTX/SAC test.'},null,2)+'\n')
 console.log('PASS actual Chrome React composer, signed llama.app CPU inference and SSE answer render')
 await context.close()
}finally{await browser.close()}
