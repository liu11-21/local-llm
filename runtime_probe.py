"""Bounded, read-only CLI probes with owned-process-tree cleanup."""
import ctypes as ct
import os
import subprocess
from tempfile import TemporaryFile


class ProbeError(ValueError):
    def __init__(self,code,message,record=None):
        super().__init__(message);self.code=code;self.record=record or {}


class BasicLimits(ct.Structure):
    _fields_=[('process_time',ct.c_int64),('job_time',ct.c_int64),('flags',ct.c_uint32),('minimum',ct.c_size_t),
              ('maximum',ct.c_size_t),('active',ct.c_uint32),('affinity',ct.c_size_t),('priority',ct.c_uint32),('scheduling',ct.c_uint32)]


class ExtendedLimits(ct.Structure):
    _fields_=[('basic',BasicLimits),('io',ct.c_uint64*6),('process_memory',ct.c_size_t),('job_memory',ct.c_size_t),('peak_process',ct.c_size_t),('peak_job',ct.c_size_t)]


def attach_job(process):
    if os.name!='nt':return None
    kernel=ct.WinDLL('kernel32',use_last_error=True)
    kernel.CreateJobObjectW.argtypes=[ct.c_void_p,ct.c_wchar_p];kernel.CreateJobObjectW.restype=ct.c_void_p
    kernel.SetInformationJobObject.argtypes=[ct.c_void_p,ct.c_int,ct.c_void_p,ct.c_uint32]
    kernel.AssignProcessToJobObject.argtypes=[ct.c_void_p,ct.c_void_p];kernel.CloseHandle.argtypes=[ct.c_void_p]
    handle=kernel.CreateJobObjectW(None,None);limits=ExtendedLimits();limits.basic.flags=0x2000
    if not handle or not kernel.SetInformationJobObject(handle,9,ct.byref(limits),ct.sizeof(limits)) or not kernel.AssignProcessToJobObject(handle,ct.c_void_p(int(process._handle))):
        if handle:kernel.CloseHandle(handle)
        process.kill();process.wait(timeout=3)
        raise ProbeError('PROBE_CLEANUP_GUARD','無法建立探測子程序保護，已停止探測。')
    return kernel,handle


def run_probe(argv,timeout=15):
    record={'argv':list(map(str,argv)),'exit_code':None,'timeout':False,'cleanup':'not started'}
    env={k:v for k,v in os.environ.items() if not k.upper().startswith('LLAMA_') and k.upper()!='HF_TOKEN'}
    with TemporaryFile() as output:
        process=subprocess.Popen(record['argv'],stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,
            env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),start_new_session=os.name!='nt')
        job=None
        try:
            job=attach_job(process)
            try:record['exit_code']=process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                record['timeout']=True
                raise ProbeError('PROBE_TIMEOUT','Runtime 執行探測逾時，已清理該探測程序。',record) from None
        finally:
            if job:job[0].CloseHandle(job[1])
            elif os.name!='nt':
                import signal
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
            if process.poll() is None:process.kill()
            process.wait(timeout=3);record['cleanup']='owned process tree closed'
        output.seek(0);raw=output.read(256*1024+1)
        if len(raw)>256*1024:raise ProbeError('PROBE_OUTPUT_LIMIT','Runtime 探測輸出超過限制。',record)
        text=raw.decode('utf-8',errors='replace');record['output']=text[:2000]
        return text,record
