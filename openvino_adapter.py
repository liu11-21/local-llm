"""Optional, pinned OpenVINO environment managed by the existing desktop Worker."""
from contextlib import contextmanager
import ctypes as ct
from hashlib import file_digest, sha256
import json
import os
from pathlib import Path
from queue import Empty, Queue
import re
import shutil
import subprocess
import tempfile
from threading import Event, Lock, Thread
from time import monotonic, time
from uuid import uuid4
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from comfy_runtime import external_process
from download_recovery import exclusive, owned
from downloads import download_file
from windows_http import WindowsResponse
from hardware import detect_hardware
from task_manager import timestamp

VERSION = "2025.4.1"
FILES = ("config.json","generation_config.json","tokenizer_config.json","special_tokens_map.json",
         "openvino_model.xml","openvino_model.bin","openvino_tokenizer.xml","openvino_tokenizer.bin",
         "openvino_detokenizer.xml","openvino_detokenizer.bin")
LIMIT = 8*1024**3


def package_manifest():
    return json.loads(Path(__file__).with_name("openvino-packages.lock.json").read_text(encoding="utf-8"))


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream,"sha256").hexdigest()


class BasicLimits(ct.Structure):
    _fields_ = [("process_time",ct.c_int64),("job_time",ct.c_int64),("flags",ct.c_uint32),
                ("minimum",ct.c_size_t),("maximum",ct.c_size_t),("active",ct.c_uint32),
                ("affinity",ct.c_size_t),("priority",ct.c_uint32),("scheduling",ct.c_uint32)]


class ExtendedLimits(ct.Structure):
    _fields_ = [("basic",BasicLimits),("io",ct.c_uint64*6),("process_memory",ct.c_size_t),
                ("job_memory",ct.c_size_t),("peak_process",ct.c_size_t),("peak_job",ct.c_size_t)]


@contextmanager
def memory_limit(process, maximum):
    handle = None
    if os.name=="nt":
        kernel = ct.WinDLL("kernel32",use_last_error=True)
        kernel.CreateJobObjectW.argtypes = [ct.c_void_p,ct.c_wchar_p]
        kernel.CreateJobObjectW.restype = ct.c_void_p
        kernel.SetInformationJobObject.argtypes = [ct.c_void_p,ct.c_int,ct.c_void_p,ct.c_uint32]
        kernel.AssignProcessToJobObject.argtypes = [ct.c_void_p,ct.c_void_p]
        kernel.CloseHandle.argtypes = [ct.c_void_p]
        handle = kernel.CreateJobObjectW(None,None)
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000 | 0x100
        limits.process_memory = maximum
        if (not handle or not kernel.SetInformationJobObject(handle,9,ct.byref(limits),ct.sizeof(limits))
                or not kernel.AssignProcessToJobObject(handle,ct.c_void_p(int(process._handle)))):
            if handle:
                kernel.CloseHandle(handle)
            process.kill()
            raise RuntimeError("無法建立 OpenVINO 程序記憶體限制。")
    try:
        yield
    finally:
        if handle:
            kernel.CloseHandle(handle)


class OpenVINOAdapter:
    def __init__(self, data, connect):
        self.root = data / "openvino"
        self.connect = connect
        self.runtime = self.root / ("runtime-"+VERSION)
        self.models = self.root / "models"
        self.safe = owned(self.root) and owned(self.models)
        if self.safe:
            try:
                self.root.mkdir(exist_ok=True)
                self.models.mkdir(exist_ok=True)
            except OSError:
                self.safe = False
        self.process = None
        self.lock = Lock()
        self.detected = {"state":"not-checked","devices":[],"version":VERSION}
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS engine_runs (
                        id TEXT PRIMARY KEY,engine TEXT NOT NULL,model TEXT NOT NULL,
                        details TEXT NOT NULL,created TEXT NOT NULL)""")
            if db.execute("PRAGMA user_version").fetchone()[0]<10:
                db.execute("PRAGMA user_version=10")

    def installed(self):
        return self.safe and owned(self.runtime) and (self.runtime/"READY.json").is_file() and (self.runtime/"python.exe").is_file()

    def status(self):
        models = []
        directories = sorted(self.models.iterdir()) if self.safe and owned(self.models) else []
        for directory in directories:
            if not re.fullmatch(r"[a-f0-9]{16}",directory.name) or not owned(directory):
                continue
            try:
                metadata = directory/"MODEL.json"
                if not owned(metadata) or metadata.stat().st_size>256*1024:
                    continue
                record = json.loads(metadata.read_text(encoding="utf-8"))
                models.append({"id":directory.name,**record})
            except (OSError,ValueError):
                continue
        return {"id":"openvino","installed":self.installed(),"version":VERSION,"models":models,
                "devices":self.detected["devices"],"detection":self.detected["state"],
                "busy":self.process is not None,"formats":["OpenVINO IR"],
                "adapters":[{"vendor":"AMD","state":"contract-only"},{"vendor":"Qualcomm","state":"contract-only"}]}

    def install_plan(self):
        files = package_manifest()["files"]
        return {"version":VERSION,"download_bytes":sum(item["bytes"] for item in files),
                "disk_required":600*1024**2,"installed":self.installed(),"files":files,
                "directory":str(self.runtime)}

    def install(self, cancel, update):
        if not self.safe:
            raise ValueError("選用 Runtime 資料夾無法安全存取。既有引擎仍可使用。")
        if os.name!="nt":
            raise ValueError("此固定版本 Runtime 套件支援 Windows x64。")
        cache = self.root/"downloads"
        cache.mkdir(exist_ok=True)
        if not owned(self.root) or not owned(cache):
            raise ValueError("OpenVINO 安裝目錄不安全。")
        with exclusive(self.root/"install.lock"):
            if self.installed():
                return {"message":"OpenVINO 已安裝。"}
            if self.runtime.exists():
                raise ValueError("Runtime 目錄不完整，請先移除再重試。")
            manifest = package_manifest()
            if shutil.disk_usage(self.root).free<600*1024**2:
                raise ValueError("安裝 OpenVINO 至少需要 600 MiB 可用空間。")
            for file in manifest["files"]:
                target = cache/file["file"]
                if not owned(target):
                    raise ValueError("套件快取不安全。")
                if target.exists():
                    if target.stat().st_size!=file["bytes"] or digest(target)!=file["sha256"]:
                        raise ValueError("既有 OpenVINO 套件校驗失敗，請檢查下載快取。")
                else:
                    update(message="下載並校驗 "+file["name"])
                    download_file(file["url"],target,4,cancel,
                                  lambda received,total,_workers:update(received=received,total=total),validate=lambda _:None,
                                  opener=WindowsResponse,
                                  recovery=cache/"checkpoints",expected_size=file["bytes"],expected_sha=file["sha256"])
            with tempfile.TemporaryDirectory(prefix="install-",dir=self.root) as temporary:
                stage = Path(temporary)/"runtime"
                stage.mkdir()
                python = manifest["files"][0]
                with ZipFile(cache/python["file"]) as archive:
                    for item in archive.infolist():
                        if Path(item.filename).name!=item.filename or item.is_dir():
                            raise ValueError("Python 套件包含非預期路徑。")
                    archive.extractall(stage)
                (stage/"python312._pth").write_text("python312.zip\n.\nLib/site-packages\nimport site\n",encoding="ascii")
                pip = next(file for file in manifest["files"] if file["name"]=="pip")
                requirements = Path(temporary)/"requirements.txt"
                requirements.write_text("\n".join(f"{file['name']}=={file['version']} --hash=sha256:{file['sha256']}"
                                                for file in manifest["files"][1:] if file["name"]!="pip"),encoding="ascii")
                command = [str(stage/"python.exe"),"-I","-c",
                           "import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_module('pip',run_name='__main__')",
                           str(cache/pip["file"]),"install","--no-index","--require-hashes","--no-deps","--no-compile",
                           "--disable-pip-version-check","--no-warn-script-location","--find-links",str(cache),
                           "--target",str(stage/"Lib/site-packages"),"-r",str(requirements)]
                update(message="在獨立環境安裝已校驗的 OpenVINO…")
                self._command(command,cancel,120)
                if cancel.is_set():
                    raise InterruptedError("已取消 OpenVINO 安裝。")
                (stage/"READY.json").write_text(json.dumps(manifest),encoding="utf-8")
                stage.rename(self.runtime)
        return {"message":"OpenVINO 已安裝於獨立環境。"}

    def _command(self, command, cancel, timeout):
        process = external_process(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                   creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        deadline = monotonic()+timeout
        try:
            while process.poll() is None:
                if cancel.wait(.1) or monotonic()>deadline:
                    raise InterruptedError("作業已取消或逾時。")
            if process.returncode:
                raise RuntimeError("OpenVINO 環境安裝失敗。")
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()

    def import_model(self, source, cancel, update):
        if not self.safe or not owned(self.models):
            raise ValueError("OpenVINO 模型資料夾不安全。")
        source = Path(source).absolute()
        source = source.parent.resolve()/source.name
        if not owned(source) or not source.is_dir():
            raise ValueError("請選擇沒有連結的 OpenVINO IR 模型資料夾。")
        for name in ("openvino_model.xml","openvino_model.bin"):
            if not owned(source/name) or not (source/name).is_file():
                raise ValueError("模型需要 openvino_model.xml 與 openvino_model.bin。")
        xml = source/"openvino_model.xml"
        if xml.stat().st_size>10*1024**2:
            raise ValueError("模型結構檔超出限制。")
        files = [source/name for name in FILES if (source/name).exists()]
        if any(path.stat().st_size>(10*1024**2 if path.suffix==".xml" else 1024**2)
               for path in files if path.suffix!=".bin"):
            raise ValueError("模型設定或結構檔超出大小限制。")
        size = sum(path.stat().st_size for path in files)
        if size>LIMIT or shutil.disk_usage(self.models).free<size+256*1024**2:
            raise ValueError("模型超出 8 GiB 限制或磁碟空間不足。")
        text = all((source/name).is_file() for name in ("openvino_tokenizer.xml","openvino_tokenizer.bin",
                                                       "openvino_detokenizer.xml","openvino_detokenizer.bin","config.json"))
        hashes = {}
        with tempfile.TemporaryDirectory(prefix="import-",dir=self.root) as temporary:
            stage = Path(temporary)/"model"
            stage.mkdir()
            for path in files:
                if not owned(path) or not path.is_file() or path.stat().st_nlink!=1:
                    raise ValueError("模型檔案不安全。")
                update(message="匯入並校驗 "+path.name)
                with path.open("rb") as original, (stage/path.name).open("xb") as output:
                    value = sha256()
                    while block:=original.read(1024**2):
                        if cancel.is_set():
                            raise InterruptedError("已取消模型匯入。")
                        output.write(block)
                        value.update(block)
                    hashes[path.name] = value.hexdigest()
            identity = sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
            graph = ET.parse(stage/"openvino_model.xml").getroot()
            if graph.tag!="net":
                raise ValueError("請匯入有效的 OpenVINO IR 模型。")
            config = json.loads((stage/"config.json").read_text(encoding="utf-8")) if text else {}
            compression = graph.find("./rt_info/nncf/weight_compression")
            quantization = {child.tag:child.get("value") for child in compression} if compression is not None else {}
            npu_candidate = (not text or quantization.get("mode")=="int4_sym" and
                             quantization.get("group_size") in ("-1","128") and quantization.get("ratio")=="1.0")
            record = {"label":source.name[:100],"kind":"text" if text else "tensor","format":"OpenVINO IR",
                      "architecture":config.get("model_type","custom-ir"),"quantization":quantization.get("mode","unknown"),
                      "compression":quantization,"npu_candidate":npu_candidate,
                      "bytes":size,"hashes":hashes,"imported":timestamp(),"verified_inference":False,
                      "operators":sorted({node.get("type","") for node in graph.findall("./layers/layer")})[:512],
                      "kv_cache":any(node.get("type") in ("ReadValue","Assign") for node in graph.findall("./layers/layer")),
                      "context":1024 if text else None,"license":"user-provided"}
            (stage/"MODEL.json").write_text(json.dumps(record),encoding="utf-8")
            if not (self.models/identity).exists():
                stage.rename(self.models/identity)
        return {"message":"OpenVINO IR 已匯入。實際相容性由所選裝置載入驗證。","model":identity}

    def validate_model(self, identity):
        if not isinstance(identity,str) or not re.fullmatch(r"[a-f0-9]{16}",identity):
            raise ValueError("OpenVINO 模型識別碼無效。")
        directory = self.models/identity
        if not self.safe or not owned(directory) or not owned(directory/"MODEL.json"):
            raise ValueError("OpenVINO 模型目錄不安全。")
        record = json.loads((directory/"MODEL.json").read_text(encoding="utf-8"))
        for name,expected in record["hashes"].items():
            if name not in FILES or not owned(directory/name) or digest(directory/name)!=expected:
                raise ValueError("模型檔案已變更，請重新匯入。")
        return directory,record

    def execute(self, request, cancel, update, *, timeout=180, memory=LIMIT):
        if not self.installed():
            raise ValueError("請先安裝可選 OpenVINO Runtime。")
        with self.lock:
            if self.process is not None:
                raise ValueError("OpenVINO 正在執行其他工作。")
            command = [str(self.runtime/"python.exe"),"-I","-B",str(Path(__file__).with_name("openvino_runner.py"))]
            process = external_process(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                                       creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            self.process = process
        events = Queue(maxsize=32)
        def receive():
            try:
                while line:=process.stdout.readline(2*1024**2+1):
                    if len(line)>2*1024**2:
                        break
                    item = json.loads(line)
                    events.put(item,timeout=1)
            except Exception:
                pass
            finally:
                try:
                    events.put(None,timeout=1)
                except Exception:
                    pass
        reader = Thread(target=receive,daemon=True)
        result = None
        deadline = monotonic()+timeout
        try:
            with memory_limit(process,memory):
                process.stdin.write(json.dumps(request,ensure_ascii=True).encode()+b"\n")
                process.stdin.close()
                reader.start()
                while True:
                    if cancel.is_set():
                        raise InterruptedError("已取消 OpenVINO 工作。")
                    if monotonic()>deadline:
                        raise TimeoutError("OpenVINO 載入或推理逾時。")
                    try:
                        event = events.get(timeout=.1)
                    except Empty:
                        continue
                    if event is None:
                        break
                    if event.get("event")=="error":
                        if request.get("op")=="benchmark":
                            raise ValueError(event.get("code","OPENVINO_REQUEST_FAILED"))
                        messages = {"DEVICE_UNAVAILABLE":"所選裝置未由 OpenVINO 回報。請檢查驅動，或明確改選 CPU。",
                                    "CONTEXT_LIMIT":"OpenVINO 輸入超過 1024 Token。請縮短提示詞或建立新對話。",
                                    "INPUT_MISMATCH":"輸入張量數量與模型不符。",
                                    "INPUT_TOO_LARGE":"輸入張量超出大小限制。","OUTPUT_TOO_LARGE":"模型輸出超出大小限制。"}
                        raise RuntimeError(messages.get(event.get("code"),"OpenVINO 無法執行。請檢查裝置、驅動、模型格式、算子與記憶體。"))
                    if event.get("event")=="result":
                        result = event
                    else:
                        update(event)
                if process.wait(timeout=5)!=0 or result is None:
                    raise RuntimeError("OpenVINO 工作程序未完成。")
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            if reader.is_alive():
                reader.join(timeout=2)
            process.stdout.close()
            if not process.stdin.closed:
                process.stdin.close()
            with self.lock:
                self.process = None
        return result

    def detect(self, cancel, update):
        try:
            result = self.execute({"op":"detect"},cancel,lambda _:None,timeout=30,memory=2*1024**3)
        except Exception:
            self.detected = {"state":"failed","devices":[],"version":VERSION}
            raise
        self.detected = {"state":"reported","devices":result["devices"],"version":result["version"],"checked_at":int(time())}
        return {"message":"已更新獨立 OpenVINO 環境的可用裝置。"}

    def infer(self, identity, device, cancel, update, *, inputs=None, messages=None, max_tokens=128):
        if not isinstance(device,str) or not re.fullmatch(r"CPU|NPU(?:\.\d+)?|GPU(?:\.\d+)?",device):
            raise ValueError("請明確選擇 CPU、Intel GPU 或 NPU。")
        if type(max_tokens) is not int or not 1<=max_tokens<=512:
            raise ValueError("OpenVINO 每次最多生成 512 Token。")
        directory,model = self.validate_model(identity)
        if device.startswith("NPU") and not model.get("npu_candidate"):
            raise ValueError("此文字模型未確認符合 NPU 的對稱 INT4、group size 與 ratio 要求。請改選 CPU 或匯入相容模型。")
        ram = detect_hardware(self.root).ram_available
        if ram is not None and ram<model["bytes"]+512*1024**2:
            raise ValueError("目前可用 RAM 低於模型權重與基本工作空間估計。請先釋放其他模型。")
        if model["kind"]=="tensor" and (not isinstance(inputs,list) or len(json.dumps(inputs))>200000):
            raise ValueError("請提供大小受限的 JSON 輸入陣列。")
        request = {"op":"infer","kind":model["kind"],"model":str(directory),"device":device,
                   "cache":str(self.root/"compiled"/identity/device.replace(".","-")),"inputs":inputs,
                   "messages":messages,"max_tokens":max_tokens}
        if not owned(Path(request["cache"])):
            raise ValueError("OpenVINO 編譯快取目錄不安全。")
        evidence = {"requested_device":device,"verified_inference":False,"status":"failed"}
        try:
            result = self.execute(request,cancel,update)
            evidence = {**result.get("evidence",{}),"status":"completed","latency_ms":result.get("latency_ms"),
                        "model_hashes":model["hashes"],"memory_limit":LIMIT,"timeout_seconds":180}
            return result
        finally:
            if cancel.is_set():
                evidence["status"] = "cancelled"
            with self.connect() as db:
                db.execute("INSERT INTO engine_runs VALUES(?,?,?,?,?)",
                           (uuid4().hex,"openvino",identity,json.dumps(evidence),timestamp()))

    def remove(self):
        if self.process is not None:
            raise ValueError("請先取消或等待 OpenVINO 工作完成。")
        with exclusive(self.root/"install.lock"):
            target = self.runtime.absolute()
            if target.parent!=self.root.absolute() or not owned(target):
                raise ValueError("Runtime 目錄不安全。")
            if target.exists():
                shutil.rmtree(target)
        self.detected = {"state":"not-checked","devices":[],"version":VERSION}
        return {"message":"已移除 OpenVINO Runtime，已匯入模型仍保留。"}

    def close(self):
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                self.process.kill()
