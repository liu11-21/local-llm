#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::{json, Value};
use std::{
    io::{BufRead, BufReader, Read, Write},
    path::PathBuf,
    process::{Child, ChildStdin, ChildStdout, Command, Stdio},
    sync::{Arc, Mutex},
};
use tauri::{path::BaseDirectory, AppHandle, Manager, State};

#[cfg(windows)]
mod lifecycle {
    use std::{io, mem, os::windows::{io::{AsRawHandle, FromRawHandle, OwnedHandle}}, process::Child, ptr};
    use windows_sys::Win32::System::JobObjects::{
        AssignProcessToJobObject, CreateJobObjectW, SetInformationJobObject,
        JobObjectExtendedLimitInformation, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    };

    pub fn attach(child: &Child) -> io::Result<OwnedHandle> {
        unsafe {
            let raw = CreateJobObjectW(ptr::null(), ptr::null());
            if raw.is_null() {
                return Err(io::Error::last_os_error());
            }
            let job = OwnedHandle::from_raw_handle(raw);
            let mut limits: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = mem::zeroed();
            limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            if SetInformationJobObject(
                job.as_raw_handle(),
                JobObjectExtendedLimitInformation,
                (&limits as *const JOBOBJECT_EXTENDED_LIMIT_INFORMATION).cast(),
                mem::size_of_val(&limits) as u32,
            ) == 0 || AssignProcessToJobObject(job.as_raw_handle(), child.as_raw_handle()) == 0 {
                return Err(io::Error::last_os_error());
            }
            Ok(job)
        }
    }
}

const REQUEST_LIMIT: usize = 256 * 1024;
const RESPONSE_LIMIT: u64 = 16 * 1024 * 1024;

struct Worker {
    child: Child,
    input: ChildStdin,
    output: BufReader<ChildStdout>,
    #[cfg(windows)]
    _job: std::os::windows::io::OwnedHandle,
}

impl Worker {
    fn open(app: &AppHandle) -> Result<Self, String> {
        let executable = app.path().resolve("worker/LocalLLMWorker.exe", BaseDirectory::Resource)
            .map_err(|e| e.to_string())?;
        let mut command = if executable.is_file() {
            Command::new(executable)
        } else {
            #[cfg(debug_assertions)]
            {
                let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
                let mut python = Command::new("python");
                python.arg(root.join("desktop_worker.py")).current_dir(root);
                python
            }
            #[cfg(not(debug_assertions))]
            return Err("安裝缺少工作程序。請用安裝程式重新安裝。".into());
        };
        let appdata = app.path().local_data_dir().map_err(|e| e.to_string())?.join("LocalLLM");
        command.arg("--data").arg(appdata);
        command.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }
        let mut child = command.spawn().map_err(|e| format!("無法啟動工作程序：{e}"))?;
        #[cfg(windows)]
        let job = match lifecycle::attach(&child) {
            Ok(job) => job,
            Err(error) => {
                let _ = child.kill();
                let _ = child.wait();
                return Err(format!("無法管理工作程序生命週期：{error}"));
            }
        };
        let input = child.stdin.take().expect("piped stdin");
        let output = BufReader::new(child.stdout.take().expect("piped stdout"));
        let mut worker = Self { child, input, output, #[cfg(windows)] _job: job };
        let identity = worker.request(br#"{"op":"build-info","data":{}}"#.to_vec())?;
        let value = &identity["value"];
        if identity["ok"] != true || value["version"] != env!("CARGO_PKG_VERSION")
            || value["channel"] != "Development"
            || (!cfg!(debug_assertions) && value["commit"] != env!("WORKSPACE_COMMIT")) {
            return Err("App 與工作程序版本不一致或資料無法開啟。請使用完整 Workspace 安裝包重新安裝；請先保留使用者資料。".into());
        }
        Ok(worker)
    }

    fn request(&mut self, mut bytes: Vec<u8>) -> Result<Value, String> {
        bytes.push(b'\n');
        let error = |_e: std::io::Error| "工作程序連線中斷。請重新連線，先查看任務中心原工作狀態；不會自動重送。".to_string();
        self.input.write_all(&bytes).map_err(error)?;
        self.input.flush().map_err(error)?;
        let mut line = Vec::new();
        self.output.by_ref().take(RESPONSE_LIMIT).read_until(b'\n', &mut line).map_err(error)?;
        if line.last() != Some(&b'\n') {
            return Err("工作程序已停止或回應超出上限。請重新連線並查看原任務狀態，避免重複提交。".into());
        }
        serde_json::from_slice(&line).map_err(|_| "工作程序回應格式不正確。".into())
    }
}

impl Drop for Worker {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

#[derive(Default)]
struct Workspace(Arc<Mutex<Option<Worker>>>);

#[tauri::command]
async fn workspace(app: AppHandle, window: tauri::WebviewWindow, state: State<'_, Workspace>, op: String, data: Value)
    -> Result<Value, String>
{
    if window.label() != "main" || !data.is_object() {
        return Err("工作台請求無效。".into());
    }
    let request = serde_json::to_vec(&json!({ "op": op, "data": data })).map_err(|e| e.to_string())?;
    if request.len() + 1 > REQUEST_LIMIT {
        return Err("工作資料超出上限。".into());
    }
    let session = state.0.clone();
    tauri::async_runtime::spawn_blocking(move || {
        let mut worker = session.lock().map_err(|_| "工作程序無法存取。".to_string())?;
        if worker.is_none() {
            *worker = Some(Worker::open(&app)?);
        }
        let result = worker.as_mut().unwrap().request(request);
        if result.is_err() {
            worker.take();
        }
        result
    }).await.map_err(|e| e.to_string())?
}

fn main() {
    tauri::Builder::default()
        .manage(Workspace::default())
        .invoke_handler(tauri::generate_handler![workspace])
        .run(tauri::generate_context!())
        .expect("無法開啟 Local LLM 工作台");
}
