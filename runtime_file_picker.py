"""Explicit-user Windows file dialog using the OS common dialog, no upload/EXE copy."""
import ctypes as ct
from ctypes import wintypes as wt
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from runtime_probe import run_probe,ProbeError


def choose_existing():
    if os.name!='nt':raise ValueError('檔案選擇器需要 Windows；亦可輸入既有 llama.exe 的完整路徑。')
    class OpenFileName(ct.Structure):
        _fields_=[('lStructSize',wt.DWORD),('hwndOwner',wt.HWND),('hInstance',wt.HINSTANCE),('lpstrFilter',wt.LPCWSTR),
            ('lpstrCustomFilter',wt.LPWSTR),('nMaxCustFilter',wt.DWORD),('nFilterIndex',wt.DWORD),('lpstrFile',wt.LPWSTR),
            ('nMaxFile',wt.DWORD),('lpstrFileTitle',wt.LPWSTR),('nMaxFileTitle',wt.DWORD),('lpstrInitialDir',wt.LPCWSTR),
            ('lpstrTitle',wt.LPCWSTR),('Flags',wt.DWORD),('nFileOffset',wt.WORD),('nFileExtension',wt.WORD),
            ('lpstrDefExt',wt.LPCWSTR),('lCustData',wt.LPARAM),('lpfnHook',ct.c_void_p),('lpTemplateName',wt.LPCWSTR),
            ('pvReserved',ct.c_void_p),('dwReserved',wt.DWORD),('FlagsEx',wt.DWORD)]
    filename=ct.create_unicode_buffer(32768);request=OpenFileName();request.lStructSize=ct.sizeof(request)
    request.lpstrFilter='官方 llama.exe\0llama.exe\0\0';request.lpstrFile=ct.cast(filename,wt.LPWSTR);request.nMaxFile=len(filename)
    request.lpstrTitle='選擇已安裝的官方 llama.exe（不下載、不複製）';request.Flags=0x00080000|0x00001000|0x00000800|0x00000008|0x02000000
    dialog=ct.WinDLL('comdlg32',use_last_error=True);dialog.GetOpenFileNameW.argtypes=[ct.POINTER(OpenFileName)];dialog.GetOpenFileNameW.restype=wt.BOOL
    if not dialog.GetOpenFileNameW(ct.byref(request)):
        error=dialog.CommDlgExtendedError()
        if error:raise OSError('Windows 檔案選擇器無法開啟：'+str(error))
        return None
    return filename.value


def pick_existing():
    if getattr(sys,'frozen',False):raise ValueError('此選擇器使用官方 Python；Desktop 可直接輸入完整路徑。')
    command=[sys.executable,'-I','-B',str(Path(__file__).resolve())]
    text,record=run_probe(command,timeout=120)
    if record['exit_code']!=0:raise ProbeError('RUNTIME_PICKER_FAILED','Windows 檔案選擇器失敗，請查看診斷或輸入完整路徑。',record)
    try:return json.loads(text)['path']
    except (ValueError,KeyError,TypeError):raise ProbeError('RUNTIME_PICKER_FAILED','Windows 檔案選擇器回覆格式不符。') from None


if __name__=='__main__':
    try:print(json.dumps({'path':choose_existing()},ensure_ascii=True))
    except (ValueError,OSError) as error:
        print(json.dumps({'error':str(error)},ensure_ascii=True));raise SystemExit(1)
