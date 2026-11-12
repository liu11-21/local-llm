"""Cached observations of the managed service; no HTTP while scheduler locks are held."""
from threading import Event,Lock,Thread
from time import time
from benchmark_adapters import native_peak
from device_resources import ResourceDemand
from media import ComfyClient
from resource_contract import fresh_measure


def reservation(stats,queue,hardware,peak,*,now=None,committed_limit=None):
    now=time() if now is None else now
    unknown={'state':'unknown','model_loaded':None,'precise':False,'checked_at':now}
    fallback=ResourceDemand(engine='ComfyUI',limitations=('ComfyUI 資源／裝置或生成峰值未知，維持全域互斥。',))
    if not isinstance(queue,dict) or not all(isinstance(queue.get(key),list) for key in ('queue_running','queue_pending')):
        return unknown,fallback
    if queue['queue_running'] or queue['queue_pending']:
        return {**unknown,'state':'generating' if queue['queue_running'] else 'switching'},fallback
    devices=stats.get('devices',[]) if isinstance(stats,dict) else []
    if len(devices)!=1 or type(peak) is not int or peak<=0 or type(committed_limit) is not int or committed_limit<peak:return unknown,fallback
    item=devices[0]
    candidates=[gpu for gpu in hardware.get('devices',[]) if gpu.get('kind')=='gpu' and gpu.get('memory_type')=='dedicated'
                and gpu['name'].casefold() in str(item.get('name','')).casefold() and fresh_measure(gpu['vram_total'],now)
                and fresh_measure(gpu['vram_available'],now) and type(item.get('vram_total')) is int
                and abs(gpu['vram_total']['value']-item['vram_total'])<=max(64*1024**2,item['vram_total']//20)]
    if len(candidates)!=1 or item.get('type') not in ('cuda','xpu') or not all(type(item.get(k)) is int and item[k]>=0 for k in ('vram_free','torch_vram_total')):
        return unknown,fallback
    gpu=candidates[0]
    state='loaded' if item['torch_vram_total'] else 'idle'
    # Actual weights are not enumerated by /system_stats. Resident allocations are
    # evidence of occupancy, not a fabricated model identity. Same GPU stays locked.
    details={'state':state,'model_loaded':None,'resident_allocations':item['torch_vram_total'],
             'device':gpu['id'],'mapping':'unique-name-and-dedicated-capacity','precise':True,'checked_at':now,'committed_limit':committed_limit}
    return details,ResourceDemand(engine='ComfyUI',device=gpu['id'],ram=committed_limit,
        cpu_load=10,bandwidth=10,exclusive=('gpu:'+gpu['id'],),limitations=('服務預留完整 Job Object 記憶體上限；生成或未知時恢復全域互斥。',))


class ComfyResources:
    def __init__(self,app):
        self.app,self.lock,self.stop=app,Lock(),Event()
        self.observed=None
        self.thread=None

    def snapshot(self):
        status=self.app.comfy_health.status
        if status and status['state'] in ('starting','stopping','failed','unhealthy'):
            return {'state':{'starting':'switching','stopping':'releasing'}.get(status['state'],'unknown'),'precise':False},ResourceDemand(engine='ComfyUI') if self.app.comfy.running() else None
        if not self.app.comfy.running():return {'state':'stopped','precise':True},None
        if self.thread is None:
            self.thread=Thread(target=self._run,daemon=True,name='comfy-resource-monitor');self.thread.start()
        with self.lock:saved=self.observed
        if saved and 0<=time()-saved[0]['checked_at']<4:return saved
        return {'state':'unknown','precise':False},ResourceDemand(engine='ComfyUI')

    def _run(self):
        while not self.stop.is_set():
            try:
                if self.app.comfy.running():
                    client=ComfyClient(self.app.comfy.port,timeout=.7)
                    value=reservation(client.json('/system_stats'),client.json('/queue'),self.app.hardware_monitor.snapshot(),native_peak(self.app.comfy.process),committed_limit=self.app.comfy.memory_budget)
                    with self.lock:self.observed=value
                else:
                    with self.lock:self.observed=None
            except Exception:
                with self.lock:self.observed=None
            self.stop.wait(1)

    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(timeout=2)
