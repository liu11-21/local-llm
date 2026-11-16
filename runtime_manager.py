"""Select and install a separate pinned llama.app runtime without replacing legacy files."""
import hmac
import json
import os
from pathlib import Path
import tempfile
from copy import deepcopy
from threading import RLock,Thread
from time import monotonic,time
from urllib.request import urlopen
from download_recovery import owned
from runtime_trust import RuntimeTrust,discover,sha256,signature,OFFICIAL,BASELINE,code_integrity,launch_diagnostic,expected_signer
from llama_app_engine import LlamaAppEngine,engine_profile
from engine import LocalEngine
from runtime_discovery import inventory,candidate,validate

ROOT=Path(__file__).resolve().parent
MANIFEST=json.loads((ROOT/"llama-app-runtime.json").read_text(encoding="utf-8"))


class RuntimeManager:
    def __init__(self,data,legacy):
        self.data=Path(data);self.legacy=legacy;self.trust=RuntimeTrust();self.record={"kind":"legacy"};self.report=None
        self.file=self.data/"llama-runtime.json";self.official_only=False;self.web_verified=None
        self.discovery_lock=RLock();self.candidates=[];self.scan={'state':'not_detected','searched':0,'attempts':[],'errors':[]}
        self.discovery_thread=None
        try:
            value=json.loads(self.file.read_text(encoding="utf-8"))
            if isinstance(value,dict) and value.get("kind") in ("legacy","llama-app"):
                if value["kind"]=="legacy" or isinstance(value.get("path"),str) and isinstance(value.get("sha256"),str):self.record=value
        except (OSError,ValueError):pass

    def executable(self):
        if self.official_only and self.record['kind']!='llama-app':
            raise ValueError('WEB_RUNTIME_REQUIRED · 請到運算環境選擇官方已簽章的 llama.exe；Web 不需要舊版自製 EXE。')
        if self.record["kind"]=="legacy":return self.legacy()
        path=Path(self.record["path"])
        if path.is_symlink() or not path.is_file() or not hmac.compare_digest(sha256(path),self.record["sha256"]):
            raise ValueError("RUNTIME_CHANGED · Runtime 已移動或更改，請重新檢查與選擇。")
        if self.official_only and self.web_verified!=self.record['sha256']:
            if not expected_signer(signature(path),MANIFEST['expected_signer']):raise ValueError('WEB_RUNTIME_SIGNATURE · 官方 Runtime 的有效簽章無法確認，未執行。')
            self.web_verified=self.record['sha256']
        return path

    def factory(self):return LlamaAppEngine() if self.record["kind"]=="llama-app" else LocalEngine()

    def status(self,running=False):
        with self.discovery_lock:
            candidates=deepcopy(self.candidates);scan=deepcopy(self.scan)
        for row in candidates:
            row['selected']=self.record['kind']=='llama-app' and row.get('path')==self.record.get('path') and row.get('sha256')==self.record.get('sha256') and row['verified']
            if row['selected']:row['state']='running' if running else 'selected'
        return {"schema":2,"candidates":candidates,"scan":scan,"official_only":self.official_only,"selected":self.record["kind"],"selection":self.record,"trust":self.report,
                "discovered":[str(p) for p in discover()],"managed_installed":(self.data/"runtimes"/MANIFEST['id']/"llama.exe").is_file(),
                "official":OFFICIAL,"manifest":MANIFEST,"reported_baseline":BASELINE}

    def verify_candidate(self,path,sources=('manual',)):
        row=validate(candidate(str(path),sources),engine_profile,self.trust)
        with self.discovery_lock:
            self.candidates=[item for item in self.candidates if item['id']!=row['id']]+[deepcopy(row)]
        return row

    def start_discovery(self):
        with self.discovery_lock:
            if self.scan['state']=='scanning':return self.status()
            self.scan={'state':'scanning','started_at':int(time()),'searched':0,'attempts':[],'errors':[]};self.candidates=[]
            self.discovery_thread=Thread(target=self._discover,daemon=True,name='llama-runtime-discovery');self.discovery_thread.start()
        return self.status()

    def _discover(self):
        try:
            extra=[]
            if self.record['kind']=='llama-app':extra.append(('saved_selection',Path(self.record['path'])))
            extra.append(('managed_runtime',self.data/'runtimes'/MANIFEST['id']/'llama.exe'))
            found=inventory(extra)
            rows=[candidate(item['input_path'],item['sources']) for item in found['found'][:12]]
            with self.discovery_lock:
                self.scan.update({k:found[k] for k in ('searched','attempts','errors')});self.scan['truncated']=len(found['found'])>12
                self.candidates=deepcopy(rows)
            deadline=monotonic()+90
            for row in rows:
                def publish():
                    with self.discovery_lock:
                        self.candidates=[deepcopy(row) if existing['id']==row['id'] else existing for existing in self.candidates]
                if monotonic()>deadline:
                    row.update(state='failed',reason={'code':'SCAN_TIME_LIMIT','message':'本輪偵測時間已到；可按驗證單獨檢查此版本。'});publish();continue
                validate(row,engine_profile,self.trust,publish)
            with self.discovery_lock:self.scan.update(state='complete',finished_at=int(time()))
        except Exception as error:
            with self.discovery_lock:self.scan.update(state='failed',error={'code':'DISCOVERY_FAILED','message':str(error)},finished_at=int(time()))

    def inspect(self,path):
        self.report=self.trust.inspect(path,expected=MANIFEST['sha256'],source=OFFICIAL)
        if self.report['baseline_match']:
            self.report['source_evidence']='Matches maintainer-reported binary hash; official chain and other components still require independent evidence.'
        return self.report

    def select(self,data):
        kind=data.get('kind')
        if kind not in ('legacy','llama-app') or data.get('confirmed') is not True:
            raise ValueError('RUNTIME_CONFIRM · 請確認要切換的引擎。')
        record={'kind':kind}
        if self.official_only and kind=='legacy':raise ValueError('Web 使用官方 llama.exe；舊引擎仍保留供 Desktop 使用。')
        if kind=='legacy':self.report=None
        if kind=='llama-app':
            row=self.verify_candidate(data.get('path',''))
            if not row['verified']:raise ValueError(row['reason']['code']+' · '+row['reason']['message'])
            report=row['trust'];self.report=report
            report['source']=OFFICIAL;report['sha256_verified']=report['sha256']==MANIFEST['sha256'];report['source_confirmed']=report['sha256_verified']
            record.update(path=row['path'],sha256=row['sha256'],version=row['version'],devices=row['devices'],confirmed=True,
                          validation={'checked_at':row['checked_at'],'authenticode':row['authenticode'],'input_paths':row['input_paths']})
        staged=self.file.with_suffix('.tmp');staged.write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8');os.replace(staged,self.file)
        self.record=record
        return self.status()

    def install(self,cancel,update):
        if os.name!='nt':raise ValueError('此官方套件只支援 Windows x64。')
        try:import zstandard
        except (ImportError,OSError):raise ValueError('RUNTIME_DEPENDENCY · 下載解壓需要選用的 zstandard。請執行 Install-Web-Optional.cmd runtime 並重啟；原生套件仍須通過裝置政策。') from None
        target=self.data/'runtimes'/MANIFEST['id'];target.parent.mkdir(exist_ok=True)
        if not all(owned(p) for p in (self.data,self.data/'runtimes',target)):
            raise ValueError('RUNTIME_PATH · Runtime 目錄路徑不安全，未寫入。')
        if target.exists():
            path=target/'llama.exe'
            if path.is_file() and sha256(path)==MANIFEST['sha256']:return {'path':str(path),'message':'固定版本 Runtime 已安裝，尚未切換。'}
            raise ValueError('RUNTIME_CONFLICT · 既有 Runtime 內容不同，未覆蓋。')
        with tempfile.TemporaryDirectory(prefix='llama-app-',dir=target.parent) as scratch:
            scratch=Path(scratch);compressed=scratch/'runtime.zst';decoded=scratch/'payload';decoded.mkdir()
            received=0
            with urlopen(MANIFEST['url'],timeout=30) as response,compressed.open('wb') as out:
                while block:=response.read(256*1024):
                    if cancel.is_set():raise InterruptedError('Runtime 安裝已取消。')
                    received+=len(block)
                    if received>MANIFEST['compressed_bytes']:raise ValueError('Runtime 大小不符。')
                    out.write(block);update(received=received,total=MANIFEST['compressed_bytes'],message='下載固定版本官方 Runtime')
            if received!=MANIFEST['compressed_bytes'] or sha256(compressed)!=MANIFEST['compressed_sha256']:raise ValueError('Runtime 壓縮檔 SHA-256 不符。')
            path=decoded/'llama.exe';written=0
            with zstandard.ZstdDecompressor().stream_reader(compressed.open('rb')) as reader,path.open('wb') as out:
                while block:=reader.read(256*1024):
                    if cancel.is_set():raise InterruptedError('Runtime 安裝已取消。')
                    written+=len(block)
                    if written>MANIFEST['bytes']:raise ValueError('Runtime 解壓大小不符。')
                    out.write(block)
            report=self.trust.inspect(path,expected=MANIFEST['sha256'],source=OFFICIAL)
            if written!=MANIFEST['bytes'] or not report['sha256_verified'] or not expected_signer(report['authenticode'],MANIFEST['expected_signer']):
                raise ValueError('Runtime 完整性或官方簽章未通過，未安裝。')
            license_path=ROOT/'third_party'/'llama.cpp-b12360-LICENSE'
            if not license_path.is_file() or sha256(license_path)!=MANIFEST['license_sha256']:raise ValueError('缺少或不符對應 Runtime 授權原文。')
            (decoded/'LICENSE-llama.cpp').write_bytes(license_path.read_bytes())
            (decoded/'SOURCE.json').write_text(json.dumps(MANIFEST,indent=2),encoding='utf-8')
            if cancel.is_set():raise InterruptedError('Runtime 安裝已取消。')
            decoded.rename(target)
        return {'path':str(target/'llama.exe'),'message':'已安裝並校驗固定官方 Runtime；請確認後切換，不會覆蓋舊引擎。'}
