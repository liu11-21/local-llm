"""One application instance shared by desktop JSON IPC and browser HTTP transports.

Business rules remain in the tested Desktop service; this boundary serializes external
commands (jobs still run through TaskManager) and owns shutdown. No HTTP in the core.
"""
from threading import RLock
from desktop_worker import Desktop
from workspace_errors import explain,user_message


class WorkspaceApplication:
    def __init__(self,data,*,web=False):
        self.lock=RLock();self.closed=False;self.service=Desktop(data)
        self.service.runtime_manager.official_only=web

    def response(self,op,data):
        with self.lock:
            try:
                if self.closed:raise ValueError('工作台服務已停止。')
                if not isinstance(op,str) or not isinstance(data,dict):raise ValueError('工作資料格式不正確。')
                if self.service.runtime_manager.official_only and op=='run' and data.get('action')=='engine-install':
                    raise ValueError('Web 使用官方已簽章的 llama.exe；請到運算環境安裝或選擇新版 Runtime。')
                return {'ok':True,'value':self.service.rpc(op,data)}
            except Exception as error:
                info=explain(error)
                return {'ok':False,'error':user_message(info),'error_info':info}

    def close(self):
        with self.lock:
            if not self.closed:
                self.closed=True;self.service.close()
