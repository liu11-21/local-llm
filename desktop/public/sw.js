// Deliberately network-only. Never cache APIs, credentials, model responses or old UI.
self.addEventListener('install',()=>self.skipWaiting())
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()))
self.addEventListener('fetch',event=>{
 if(event.request.mode==='navigate')event.respondWith(fetch(event.request).catch(()=>new Response(
  '<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Local LLM</title><h1>本機服務未連線</h1><p>請執行 Start-Web-Workspace.cmd，或開啟原本的啟動視窗。關閉分頁不會立即停止背景工作；可使用 Stop-Web-Workspace.cmd 停止。</p></html>',
  {status:503,headers:{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'}})))
})
