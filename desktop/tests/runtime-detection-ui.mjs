import assert from 'node:assert/strict'

// API/React contract fixtures only. No executable or hardware result is fabricated
// outside this browser test; real installed-runtime acceptance is reported separately.
export async function exerciseRuntimeDetection(page){
 let selected=false;let scan='not_detected';let pickerCalls=0;const operations=[]
 const file='C:\\Controlled Runtime\\llama.exe'
 const valid=()=>({id:'verified-fixture',input_path:file,input_paths:[file],path:file,exists:true,state:selected?'selected':'verified',
  verified:true,selected,version:'Controlled build 12360',authenticode:{status:'Valid',signer:'CN=Hugging Face, O=Hugging Face'},
  sources:['user_path'],trace:[{stage:'cli',ok:true}],probes:[]})
 const status=()=>({schema:2,selected:selected?'llama-app':'legacy',selection:selected?{path:file,version:'Controlled build 12360',devices:[]}:{},
  discovered:[file],managed_installed:false,manifest:{id:'fixture',version:'b12360',sha256:'a'.repeat(64)},
  scan:{state:scan,searched:3,attempts:[],errors:[]},candidates:scan==='not_detected'?[]:[valid(),{...valid(),id:'bad-fixture',input_path:'C:\\Bad\\llama.exe',path:'C:\\Bad\\llama.exe',
   state:'failed',verified:false,selected:false,reason:{code:'RUNTIME_SIGNATURE',message:'Controlled wrong publisher, never executed'},authenticode:{status:'NotSigned'}}]})
 const handler=async route=>{
  const {op,data}=route.request().postDataJSON();operations.push(op)
  const reply=value=>route.fulfill({json:{ok:true,value}})
  if(op==='runtime-discover'){scan='complete';return reply(status())}
  if(op==='runtime-status')return reply(status())
  if(op==='runtime-select'){assert.equal(data.path,file);assert.equal(data.confirmed,true);selected=true;return reply(status())}
  if(op==='runtime-pick'){assert.equal(data.confirmed,true);pickerCalls++;return reply({cancelled:false,status:status()})}
  if(op==='info'){
   const response=await route.fetch();const json=await response.json();json.value.models=[];json.value.registry.models=[]
   json.value.engine=selected;json.value.llama_runtime={selected:selected?'llama-app':'legacy',selection:selected?{path:file,version:'Controlled build 12360'}:{}}
   return route.fulfill({json})
  }
  return route.fallback()
 }
 await page.route('**/__desktop_dev_rpc',handler)
 await page.evaluate(()=>localStorage.setItem('localllm-onboarding-v1',JSON.stringify({stage:'skipped',task:'chat'})))
 await page.reload();await page.getByText('本機工作台已連線').waitFor({state:'attached'})
 async function go(name){const menu=page.getByTitle('導覽');if(await menu.isVisible())await menu.click();await page.getByRole('button',{name,exact:true}).click()}
 await go('運算環境')
 const list=page.getByRole('region',{name:'已安裝的 Runtime',exact:true})
 await list.getByText('已驗證 · 尚未選取',{exact:true}).waitFor()
 assert.equal(selected,false,'Discovery/verification must not silently select')
 const invalid=list.getByRole('article',{name:'Runtime 候選 bad-fixture',exact:true})
 assert.equal(await invalid.getByRole('button',{name:'選取此 Runtime',exact:true}).count(),0)
 await invalid.getByText(/Controlled wrong publisher/).waitFor()
 await list.getByRole('button',{name:'選取此 Runtime',exact:true}).click()
 await list.getByRole('button',{name:'已選取',exact:true}).waitFor();assert(selected)
 await page.reload();await page.getByText('本機工作台已連線').waitFor({state:'attached'});await go('運算環境')
 await page.getByRole('region',{name:'已安裝的 Runtime',exact:true}).getByRole('button',{name:'已選取',exact:true}).waitFor()
 await page.getByRole('button',{name:'選擇既有 llama.exe 檔案',exact:true}).click();assert.equal(pickerCalls,1)
 for(const [width,height] of [[1280,900],[1024,768],[800,600],[650,720]]){
  await page.setViewportSize({width,height})
  for(const theme of ['dark','light']){
   if(await page.evaluate(()=>document.documentElement.dataset.theme)!==theme)await page.getByTitle('切換主題').click()
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Detection overflow ${width}/${theme}`)
  }
 }
 await go('文字聊天');await page.getByRole('button',{name:'送出',exact:true}).waitFor()
 await page.getByText('Runtime 已選取；尚未準備 GGUF 模型。請到「模型與應用」匯入或選擇模型，無需重裝 Runtime。',{exact:true}).waitFor()
 assert(await page.getByRole('button',{name:'送出',exact:true}).isDisabled(),'No model must remain unprepared, not inferred')
 assert(operations.includes('runtime-discover'));assert(!operations.includes('run'),'Detection-only workflow must not download or infer')
 await page.unroute('**/__desktop_dev_rpc',handler)
 console.log('PASS controlled runtime discovery/verification/visible list/negative publisher, no-model selection, reload persistence, picker and four sizes/both themes; no real runtime downloaded/executed')
}
