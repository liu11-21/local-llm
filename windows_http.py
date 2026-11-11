"""Windows system-TLS transport for the existing verified range downloader."""
import ctypes as ct
from email.parser import Parser
from urllib.parse import urlsplit


class WindowsResponse:
    def __init__(self, url, byte_range=None, etag=None):
        parsed = urlsplit(url)
        if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Runtime 下載需要公開的 HTTPS 來源。")
        self.library = ct.WinDLL("winhttp.dll",use_last_error=True)
        self.handles = []
        lib = self.library
        lib.WinHttpOpen.argtypes = [ct.c_wchar_p,ct.c_uint32,ct.c_wchar_p,ct.c_wchar_p,ct.c_uint32]
        lib.WinHttpOpen.restype = ct.c_void_p
        lib.WinHttpConnect.argtypes = [ct.c_void_p,ct.c_wchar_p,ct.c_uint16,ct.c_uint32]
        lib.WinHttpConnect.restype = ct.c_void_p
        lib.WinHttpOpenRequest.argtypes = [ct.c_void_p,ct.c_wchar_p,ct.c_wchar_p,ct.c_wchar_p,
                                          ct.c_wchar_p,ct.c_void_p,ct.c_uint32]
        lib.WinHttpOpenRequest.restype = ct.c_void_p
        lib.WinHttpSetTimeouts.argtypes = [ct.c_void_p,ct.c_int,ct.c_int,ct.c_int,ct.c_int]
        lib.WinHttpSetOption.argtypes = [ct.c_void_p,ct.c_uint32,ct.c_void_p,ct.c_uint32]
        lib.WinHttpSendRequest.argtypes = [ct.c_void_p,ct.c_wchar_p,ct.c_uint32,ct.c_void_p,
                                          ct.c_uint32,ct.c_uint32,ct.c_size_t]
        lib.WinHttpReceiveResponse.argtypes = [ct.c_void_p,ct.c_void_p]
        lib.WinHttpQueryHeaders.argtypes = [ct.c_void_p,ct.c_uint32,ct.c_wchar_p,ct.c_void_p,
                                           ct.POINTER(ct.c_uint32),ct.c_void_p]
        lib.WinHttpReadData.argtypes = [ct.c_void_p,ct.c_void_p,ct.c_uint32,ct.POINTER(ct.c_uint32)]
        lib.WinHttpCloseHandle.argtypes = [ct.c_void_p]
        try:
            session = self.handle(lib.WinHttpOpen("LocalLLM/0.6.2",4,None,None,0))
            protocols = ct.c_uint32(0x800)
            if not lib.WinHttpSetOption(session,84,ct.byref(protocols),4):
                raise OSError("無法啟用 TLS 1.2。")
            lib.WinHttpSetTimeouts(session,15000,15000,15000,15000)
            connection = self.handle(lib.WinHttpConnect(session,parsed.hostname,parsed.port or 443,0))
            path = parsed.path or "/"
            if parsed.query:
                path += "?"+parsed.query
            self.request = self.handle(lib.WinHttpOpenRequest(connection,"GET",path,None,None,None,0x00800000))
            redirects = ct.c_uint32(1)
            if not lib.WinHttpSetOption(self.request,88,ct.byref(redirects),4):
                raise OSError("無法設定 HTTPS 重新導向政策。")
            headers = "Accept-Encoding: identity\r\n"
            if byte_range:
                headers += f"Range: bytes={byte_range[0]}-{byte_range[1]}\r\n"
            if etag:
                headers += f"If-Range: {etag}\r\n"
            if not lib.WinHttpSendRequest(self.request,headers,len(headers),None,0,0,0):
                raise ConnectionError(f"Windows HTTPS 連線失敗（{ct.get_last_error()}）。")
            if not lib.WinHttpReceiveResponse(self.request,None):
                raise ConnectionError(f"Windows HTTPS 回應失敗（{ct.get_last_error()}）。")
            status, size = ct.c_uint32(),ct.c_uint32(4)
            if not lib.WinHttpQueryHeaders(self.request,19 | 0x20000000,None,ct.byref(status),ct.byref(size),None):
                raise OSError("無法取得下載狀態。")
            self.status = status.value
            size = ct.c_uint32()
            lib.WinHttpQueryHeaders(self.request,22,None,None,ct.byref(size),None)
            if not 0<size.value<1024**2:
                raise OSError("下載標頭大小無效。")
            buffer = ct.create_unicode_buffer(size.value//ct.sizeof(ct.c_wchar)+1)
            if not lib.WinHttpQueryHeaders(self.request,22,None,buffer,ct.byref(size),None):
                raise OSError("無法取得下載標頭。")
            self.headers = Parser().parsestr(buffer.value.split("\r\n",1)[1])
        except Exception:
            self.close()
            raise

    def handle(self, value):
        if not value:
            raise OSError("無法建立 Windows HTTPS 工作階段。")
        self.handles.append(value)
        return value

    def read(self, size):
        if not 0<=size<=1024**2:
            raise ValueError("下載讀取大小超出限制。")
        buffer, received = ct.create_string_buffer(size),ct.c_uint32()
        if not self.library.WinHttpReadData(self.request,buffer,size,ct.byref(received)):
            raise ConnectionError("Windows HTTPS 傳輸中斷。")
        return buffer.raw[:received.value]

    def close(self):
        for handle in reversed(self.handles):
            self.library.WinHttpCloseHandle(handle)
        self.handles = []

    read1 = read

    def __enter__(self):
        return self

    def __exit__(self,*_):
        self.close()
