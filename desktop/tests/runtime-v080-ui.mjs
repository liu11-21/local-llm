import assert from 'node:assert/strict'
export async function exerciseRuntimeV080(page) {
 let selected='legacy';let installed=false;const requests=[]
 const state=()=>({selected,selection:{path:'C:\\Controlled\\llama.exe',version:'Controlled build 12360',devices:[
  {id:'Vulkan0',name:'Controlled NVIDIA '+ 'LongName'.repeat(25),backend:'Vulkan',available:true,memory_type:'needs-physical-mapping',reported_total_mib:15995,reported_free_mib:15227},
  {id:'Vulkan1',name:'Controlled Intel Graphics',backend:'Vulkan',available:true,memory_type:'shared-or-unified',reported_total_mib:27649,reported_free_mib:24000}]},
  discovered:['C:\\Controlled\\llama.exe'],managed_installed:installed,manifest:{id:'controlled-only',version:'b12360',sha256:'a'.repeat(64)},
  trust:{sha256:'a'.repeat(64),source_confirmed:true,sha256_verified:false,authenticode:{status:'Valid',signer:'Controlled UI fixture'},launch_success:false,gpu_identified:true,inference_success:false,sac:'NOT VERIFIED'}})
 const handler=async route=>{
  const {op,data}=route.request().postDataJSON();const reply=value=>route.fulfill({json:{ok:true,value}})
  if(op==='runtime-status')return reply(state())
  if(op==='runtime-select'){requests.push(data);selected=data.kind;return reply(state())}
  if(op==='run' && data.action==='runtime-install'){assert.equal(data.confirmed,true);installed=true;return reply({id:'d'.repeat(32)})}
  if(op==='job' && data.id==='d'.repeat(32))return reply({id:data.id,state:'completed',result:{path:'C:\\Controlled\\llama.exe'}})
  return route.fallback()
 }
 await page.route('**/__desktop_dev_rpc',handler)
 const menu=page.getByTitle('導覽');if(await menu.isVisible())await menu.click()
 await page.getByRole('button',{name:'運算環境',exact:true}).click()
 await page.getByRole('heading',{name:'文字 Runtime',exact:true}).waitFor()
 await page.getByRole('button',{name:'下載官方固定版本 · 約 13 MB',exact:true}).click()
 await page.getByText('相容引擎 · llama-server',{exact:true}).waitFor();assert.equal(selected,'legacy','Install must not auto-switch')
 await page.getByText('選擇引擎與信任證據',{exact:true}).click()
 await page.getByRole('button',{name:'檢查並切換新版',exact:true}).click()
 await page.getByText('llama.app · serve',{exact:true}).waitFor()
 assert(requests.some(r=>r.kind==='llama-app' && r.confirmed))
 await page.getByText(/Smart App Control：尚未完成獨立實機驗證/).waitFor()
 await page.getByText(/共享／統一記憶體，非獨立顯存/).first().waitFor()
 for(const [width,height] of [[1280,900],[1024,768],[800,600],[650,720]]) {
  await page.setViewportSize({width,height})
  for(const theme of ['dark','light']) {
   if(await page.evaluate(()=>document.documentElement.dataset.theme)!==theme)await page.getByTitle('切換主題').click()
   await page.waitForTimeout(30)
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Runtime overflow ${width} ${theme}`)
  }
 }
 await page.getByRole('button',{name:'使用舊版相容引擎',exact:true}).click();assert.equal(selected,'legacy')
 await page.unroute('**/__desktop_dev_rpc',handler)
 console.log('PASS controlled 0.8 Runtime install without auto-switch, confirmed selection, named GPU/memory types, independent trust/SAC states, four sizes and both themes; no real downloads or inference')
}
