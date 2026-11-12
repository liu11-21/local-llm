"""Download, install and run the official Windows ComfyUI portable runtime."""
from dataclasses import dataclass
import ctypes
import hashlib
from http.client import HTTPException
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory, TemporaryFile
import time

from downloads import check_encoding, content_range, open_download
from media import ComfyClient

VERSION = "v0.44.0"
BASE_URL = f"https://github.com/Comfy-Org/ComfyUI/releases/download/{VERSION}/"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass(frozen=True)
class Asset:
    name: str
    size: int
    sha256: str


ASSETS = {
    "intel": Asset("ComfyUI_windows_portable_intel.7z", 1486960018,
                   "f6af50a466e14db785996429cae92370490e7026150ea2d46f022b77f859d57d"),
    "amd": Asset("ComfyUI_windows_portable_amd.7z", 1671700941,
                 "b9ff564ced02a9a9f5dd3b6a5228ee2f1da33303a4f34f5438b8b80428fedd28"),
    "nvidia": Asset("ComfyUI_windows_portable_nvidia.7z", 2054382457,
                    "7170c2db49c182a81adcc051e80234f99dd891656fb200737f87797876348f96"),
    "nvidia_cu126": Asset("ComfyUI_windows_portable_nvidia_cu126.7z", 1945636677,
                          "a26cf84f043b3d9fbf0d53296f57d7190482c339caf1b3b5cfda5149d454be9f"),
}
PROFILES = {
    # The Intel build probes XPU even with --cpu; use the CUDA 12.6 bundle's CPU mode.
    "CPU": ("nvidia_cu126", ("--cpu",)),
    "Intel GPU": ("intel", ()),
    "AMD GPU": ("amd", ()),
    "NVIDIA GPU": ("nvidia", ()),
    "NVIDIA CUDA 12.6": ("nvidia_cu126", ()),
}


def install_directory(root, profile):
    return Path(root) / f"{ASSETS[PROFILES[profile][0]].name.removesuffix('.7z')}-{VERSION}"


def installed(path):
    return (path / "python_embeded" / "python.exe").is_file() and (path / "ComfyUI" / "main.py").is_file()


def check_cancelled(cancel):
    if cancel.is_set():
        raise InterruptedError("已取消 ComfyUI 作業。")


def check_port(port):
    try:
        with socket.socket() as listener:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind(("127.0.0.1", port))
    except OSError as error:
        raise OSError(f"連接埠 {port} 無法使用。若已開啟 ComfyUI，可直接生成。") from error


def external_process(args, **options):
    # Frozen DLLs belong to Local LLM, not to the portable Python or Windows tar.
    bundle = getattr(sys, "_MEIPASS", None)
    if os.name != "nt" or not bundle:
        return subprocess.Popen(args, **options)
    set_dll_directory = ctypes.windll.kernel32.SetDllDirectoryW
    set_dll_directory.argtypes = [ctypes.c_wchar_p]
    set_dll_directory(None)
    try:
        return subprocess.Popen(args, **options)
    finally:
        set_dll_directory(bundle)


def download_asset(asset, path, cancel, progress):
    digest = hashlib.sha256()
    received = 0
    with path.open("wb") as output:
        for attempt in range(4):
            check_cancelled(cancel)
            bounds = (received, asset.size - 1) if received else None
            try:
                with open_download(BASE_URL + asset.name, bounds) as response:
                    check_encoding(response)
                    if response.status == 200:
                        if received:
                            output.seek(0)
                            output.truncate()
                            digest = hashlib.sha256()
                            received = 0
                        declared = response.headers.get("Content-Length")
                        if declared is not None and int(declared) != asset.size:
                            raise ValueError("官方下載檔的大小與發行資料不符。")
                    elif not bounds or content_range(response) != (*bounds, asset.size):
                        raise ValueError("官方下載伺服器回傳了非預期的區段。")
                    last_update = 0.0
                    while received < asset.size:
                        check_cancelled(cancel)
                        block = response.read1(min(1024 ** 2, asset.size - received))
                        if not block:
                            raise ConnectionError("下載中途斷線。")
                        output.write(block)
                        digest.update(block)
                        received += len(block)
                        now = time.monotonic()
                        if received == asset.size or now - last_update >= 0.25:
                            progress(received, asset.size)
                            last_update = now
                    break
            except (OSError, HTTPException) as error:
                check_cancelled(cancel)
                if attempt == 3:
                    raise ConnectionError(f"無法完成 ComfyUI 下載：{error}") from error
                cancel.wait(attempt + 1)
    if received != asset.size or digest.hexdigest() != asset.sha256:
        raise ValueError("ComfyUI 下載檔的 SHA-256 核對失敗。")


def extract_archive(archive, target, cancel):
    tar = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "tar.exe"
    if not tar.is_file():
        raise RuntimeError("找不到 Windows tar.exe，請更新 Windows 後重試。")
    with TemporaryFile() as log, external_process(
        [str(tar), "-xf", str(archive), "-C", str(target)],
        stdout=log, stderr=subprocess.STDOUT, creationflags=NO_WINDOW,
    ) as process:
        try:
            deadline = time.monotonic() + 1800
            while process.poll() is None:
                check_cancelled(cancel)
                if time.monotonic() >= deadline:
                    raise TimeoutError("ComfyUI 解壓縮逾時。")
                cancel.wait(0.2)
            if process.returncode:
                log.seek(0, os.SEEK_END)
                log.seek(max(0, log.tell() - 1500))
                raise RuntimeError("ComfyUI 解壓縮失敗：" + log.read().decode("utf-8", "replace"))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


def install(root, profile, cancel, status, progress):
    root = Path(root).resolve()
    target = install_directory(root, profile)
    if installed(target):
        return target
    if target.exists():
        raise FileExistsError(f"安裝資料夾已存在但不完整：{target}")
    asset = ASSETS[PROFILES[profile][0]]
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < asset.size * 5:
        raise OSError("磁碟空間不足。安裝期間需同時保留壓縮檔與解壓檔。")
    with TemporaryDirectory(prefix=".install-", dir=root) as staging:
        staging = Path(staging)
        archive = staging / asset.name
        extracted = staging / "extracted"
        extracted.mkdir()
        status("正在下載官方 ComfyUI…")
        download_asset(asset, archive, cancel, progress)
        check_cancelled(cancel)
        status("SHA-256 核對完成，正在解壓縮…")
        extract_archive(archive, extracted, cancel)
        check_cancelled(cancel)
        layouts = [path for path in (extracted, *extracted.iterdir()) if installed(path)]
        if len(layouts) != 1:
            raise ValueError("官方壓縮檔的便攜版目錄結構無法辨識。")
        try:
            layouts[0].rename(target)
        except FileExistsError:
            if not installed(target):
                raise
    return target


class ManagedComfy:
    def __init__(self):
        self.process = None
        self.port = None
        self.memory_guard=None
        self.memory_budget=None

    def running(self):
        return self.process is not None and self.process.poll() is None

    def health_probe(self):
        if not self.running():
            return False
        try:
            stats = ComfyClient(self.port, timeout=2).json("/system_stats")
            return isinstance(stats, dict) and isinstance(stats.get("system"), dict)
        except HTTPException:
            return False

    def start(self, directory, profile, port, cancel, *, memory_mib=0):
        if self.running():
            raise RuntimeError("ComfyUI 已啟動。")
        client = ComfyClient(port, timeout=2)
        if not installed(directory):
            raise ValueError("請先下載並安裝 ComfyUI。")
        check_cancelled(cancel)
        check_port(port)
        env = {key: value for key, value in os.environ.items() if key.upper() not in ("PYTHONHOME", "PYTHONPATH")}
        env["PYTHONUTF8"] = "1"
        log_path = directory / "local-llm-comfyui.log"
        args = [str(directory / "python_embeded" / "python.exe"), "-s", "ComfyUI/main.py",
                "--windows-standalone-build", "--disable-auto-launch",
                "--listen", "127.0.0.1", "--port", str(port), *PROFILES[profile][1]]
        with log_path.open("wb") as log:
            self.process = external_process(args, cwd=directory, env=env, stdin=subprocess.DEVNULL,
                                            stdout=log, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
        self.port = port
        self.profile=profile
        self.directory=directory
        try:
            from hardware import detect_hardware
            from resource_policy import memory_policy,GIB
            from openvino_adapter import memory_limit
            physical=detect_hardware(directory)
            policy=memory_policy(physical.ram_total,physical.ram_available,user_mib=memory_mib)
            if policy['admission_available'] is not None and policy['ceiling']:
                budget=min(policy['admission_available'],policy['ceiling'] if memory_mib else policy['safe_capacity']//2)
                if budget<GIB:raise ValueError('ComfyUI 的安全記憶體容量不足。')
                self.memory_guard=memory_limit(self.process,budget)
                self.memory_guard.__enter__()
                self.memory_budget=budget
            # A fresh extraction can spend several minutes loading Windows/PyTorch DLLs.
            deadline = time.monotonic() + 600
            while time.monotonic() < deadline:
                check_cancelled(cancel)
                if not self.running():
                    exit_code = self.process.returncode
                    with log_path.open("rb") as log:
                        log.seek(0, os.SEEK_END)
                        log.seek(max(0, log.tell() - 8192))
                        detail = log.read().decode("utf-8", "replace")
                    if "Windows fatal exception: access violation" in detail or exit_code == 0xC0000005:
                        hint = "請查看啟動日誌。" if profile == "CPU" else "請確認顯示驅動相容，或改選 CPU。"
                        raise RuntimeError(f"ComfyUI 的硬體後端崩潰。{hint}")
                    reason = detail.strip().splitlines()[-1:] or ["請查看啟動日誌"]
                    raise RuntimeError(f"ComfyUI 啟動失敗（{exit_code}）：{reason[0]}")
                try:
                    stats = client.json("/system_stats")
                    if isinstance(stats, dict) and "system" in stats and self.running():
                        return
                except (ConnectionError, HTTPException, ValueError, RuntimeError):
                    pass
                cancel.wait(0.5)
            raise TimeoutError(f"等待 ComfyUI 啟動逾時。啟動日誌：{log_path}")
        except Exception:
            self.stop()
            raise

    def stop(self):
        if self.running():
            self.process.terminate()
            try:
                self.process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=4)
        self.process = self.port = None
        if self.memory_guard:self.memory_guard.__exit__(None,None,None)
        self.memory_guard=None
        self.memory_budget=None
