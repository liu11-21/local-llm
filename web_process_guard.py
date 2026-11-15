"""Own a Windows kill-on-close job for the Python host and inherited children."""
import ctypes as ct
import os

_handle=None


def enable():
    global _handle
    if os.name!='nt':return 'NOT VERIFIED: Windows Job Object unavailable'
    if _handle:return 'active: Windows kill-on-close job'
    from openvino_adapter import ExtendedLimits
    kernel=ct.WinDLL('kernel32',use_last_error=True)
    kernel.CreateJobObjectW.argtypes=[ct.c_void_p,ct.c_wchar_p];kernel.CreateJobObjectW.restype=ct.c_void_p
    kernel.SetInformationJobObject.argtypes=[ct.c_void_p,ct.c_int,ct.c_void_p,ct.c_uint32]
    kernel.AssignProcessToJobObject.argtypes=[ct.c_void_p,ct.c_void_p]
    kernel.GetCurrentProcess.restype=ct.c_void_p;kernel.CloseHandle.argtypes=[ct.c_void_p]
    handle=kernel.CreateJobObjectW(None,None);limits=ExtendedLimits();limits.basic.flags=0x2000
    if not handle or not kernel.SetInformationJobObject(handle,9,ct.byref(limits),ct.sizeof(limits)) or not kernel.AssignProcessToJobObject(handle,kernel.GetCurrentProcess()):
        if handle:kernel.CloseHandle(handle)
        raise ValueError('無法建立 Web 子程序關閉保護；未啟動 Runtime。請保留系統政策並查看程序／沙箱限制。')
    # Intentionally held until process exit, never inherited or explicitly closed:
    # closing a job containing this process would also terminate the host immediately.
    _handle=handle
    return 'active: Windows kill-on-close job'
