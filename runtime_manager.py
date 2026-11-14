"""Select and install a separate pinned llama.app runtime without replacing legacy files."""
import hmac
import json
import os
from pathlib import Path
import tempfile
from urllib.request import urlopen
from download_recovery import owned
from runtime_trust import RuntimeTrust,discover,sha256,OFFICIAL,BASELINE,code_integrity,launch_diagnostic,expected_signer
from llama_app_engine import LlamaAppEngine,engine_profile
from engine import LocalEngine

ROOT=Path(__file__).resolve().parent
MANIFEST=json.loads((ROOT/"llama-app-runtime.json").read_text(encoding="utf-8"))


class RuntimeManager:
    def __init__(self,data,legacy):
        self.data=Path(data);self.legacy=legacy;self.trust=RuntimeTrust();self.record={"kind":"legacy"};self.report=None
        self.file=self.data/"llama-runtime.json"
        try:
            value=json.loads(self.file.read_text(encoding="utf-8"))
            if isinstance(value,dict) and value.get("kind") in ("legacy","llama-app"):
                if value["kind"]=="legacy" or isinstance(value.get("path"),str) and isinstance(value.get("sha256"),str):self.record=value
        except (OSError,ValueError):pass

    def executable(self):
        if self.record["kind"]=="legacy":return self.legacy()
        path=Path(self.record["path"])
        if path.is_symlink() or not path.is_file() or not hmac.compare_digest(sha256(path),self.record["sha256"]):
            raise ValueError("RUNTIME_CHANGED · Runtime 已移動或更改，請重新檢查與選擇。")
        return path

    def factory(self):return LlamaAppEngine() if self.record["kind"]=="llama-app" else LocalEngine()

    def status(self):
        return {"selected":self.record["kind"],"selection":self.record,"trust":self.report,
                "discovered":[str(p) for p in discover()],"managed_installed":(self.data/"runtimes"/MANIFEST['id']/"llama.exe").is_file(),
                "official":OFFICIAL,"manifest":MANIFEST,"reported_baseline":BASELINE}

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
        if kind=='legacy':self.report=None
        if kind=='llama-app':
            report=self.inspect(data.get('path',''))
            auth=report['authenticode']
            if not expected_signer(auth,MANIFEST['expected_signer']):
                raise ValueError('RUNTIME_SIGNATURE · 新版官方 Runtime 需有效 Hugging Face 簽章；未執行此檔案。')
            try:caps=engine_profile(Path(report['path']))
            except OSError as error:
                detail=launch_diagnostic(error,Path(report['path']));report.update(detail)
                raise ValueError(detail['code']+' · '+detail['hint']) from None
            record.update(path=report['path'],sha256=report['sha256'],version=caps['version'],devices=caps.get('devices',[]),confirmed=True)
            report['gpu_identified']=bool(caps.get('devices'))
            report['version']=caps['version'];report['cli_probe_success']=True
        staged=self.file.with_suffix('.tmp');staged.write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8');os.replace(staged,self.file)
        self.record=record
        return self.status()

    def install(self,cancel,update):
        if os.name!='nt':raise ValueError('此官方套件只支援 Windows x64。')
        import zstandard
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
