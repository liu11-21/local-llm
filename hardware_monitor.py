"""Optional Windows hardware inventory and cached WDDM performance counters.

No inference package is imported by monitoring. Missing counters remain unknown.
"""
import ctypes as ct
import json
import math
import os
from pathlib import Path
import re
import subprocess
from threading import Event, Lock, Thread
from time import monotonic, time
import uuid


def reading(value=None, source="detected", status=None):
    return {"value":value, "source":source if value is not None else "unknown",
            "status":status or ("available" if value is not None else "unknown")}


def windows_inventory(cancel=None):
    """CIM exposes typed PnP/driver records, independent of localized UI text."""
    executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    script = r"""
    $ErrorActionPreference='Stop'
    [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
    $devices=@(Get-CimInstance Win32_PnPEntity -Filter "Present = True AND
      (PNPClass = 'Display' OR PNPClass = 'ComputeAccelerator' OR PNPClass = 'NeuralProcessor' OR
       Name LIKE '%NPU%' OR Name LIKE '%AI Boost%' OR Name LIKE '%AMD IPU%' OR Name LIKE '%Hexagon%')")
    $drivers=@(Get-CimInstance Win32_PnPSignedDriver -Filter "DeviceClass = 'DISPLAY' OR
      DeviceClass = 'COMPUTEACCELERATOR' OR DeviceClass = 'NEURALPROCESSOR' OR
      DeviceName LIKE '%NPU%' OR DeviceName LIKE '%AI Boost%' OR DeviceName LIKE '%AMD IPU%' OR DeviceName LIKE '%Hexagon%'")
    @($devices | ForEach-Object {
      $device=$_
      $driver=$drivers | Where-Object DeviceID -eq $device.PNPDeviceID | Select-Object -First 1
      @{id=$device.PNPDeviceID;name=$device.Name;vendor=$device.Manufacturer;
        class=$device.PNPClass;problem=$device.ConfigManagerErrorCode;driver=$driver.DriverVersion}
    }) | ConvertTo-Json -Compress
    """
    with subprocess.Popen([str(executable),"-NoProfile","-NonInteractive","-Command",script],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          creationflags=subprocess.CREATE_NO_WINDOW) as process:
        deadline = monotonic()+20
        while True:
            try:
                raw, _ = process.communicate(timeout=0.25)
                break
            except subprocess.TimeoutExpired:
                if monotonic()>=deadline or cancel is not None and cancel.is_set():
                    process.kill()
                    process.communicate()
                    raise OSError("Windows inventory unavailable") from None
        if process.returncode:
            raise OSError("Windows inventory unavailable")
    raw = raw.decode("utf-8-sig").strip()
    rows = json.loads(raw) if raw else []
    return rows if isinstance(rows,list) else [rows]


class Luid(ct.Structure):
    _fields_ = [("low",ct.c_uint32),("high",ct.c_uint32)]


class AdapterDescription(ct.Structure):
    _fields_ = [("name",ct.c_wchar*128),("vendor",ct.c_uint32),("device",ct.c_uint32),
                ("subsystem",ct.c_uint32),("revision",ct.c_uint32),("dedicated",ct.c_size_t),
                ("reserved",ct.c_size_t),("shared",ct.c_size_t),("luid",Luid),("flags",ct.c_uint32)]


def dxgi_adapters():
    def method(pointer, slot, result, *arguments):
        table = ct.cast(pointer,ct.POINTER(ct.POINTER(ct.c_void_p))).contents
        return ct.WINFUNCTYPE(result,ct.c_void_p,*arguments)(table[slot])

    library = ct.WinDLL("dxgi.dll")
    factory = ct.c_void_p()
    iid = (ct.c_ubyte*16).from_buffer_copy(uuid.UUID("770aae78-f26f-4dba-a829-253c83d1b387").bytes_le)
    create = library.CreateDXGIFactory1
    create.argtypes = [ct.c_void_p,ct.POINTER(ct.c_void_p)]
    create.restype = ct.c_int32
    if create(ct.byref(iid),ct.byref(factory)) < 0:
        raise OSError("DXGI inventory unavailable")
    devices = []
    try:
        for index in range(32):
            adapter = ct.c_void_p()
            status = method(factory,12,ct.c_int32,ct.c_uint32,ct.POINTER(ct.c_void_p))(
                factory,index,ct.byref(adapter))
            if status < 0:
                break
            try:
                desc = AdapterDescription()
                if method(adapter,10,ct.c_int32,ct.POINTER(AdapterDescription))(adapter,ct.byref(desc)) < 0 or desc.flags & 2:
                    continue
                devices.append({"id":f"{desc.luid.high:08x}_{desc.luid.low:08x}","kind":"gpu","name":desc.name,
                                "vendor":{0x10de:"NVIDIA",0x1002:"AMD",0x8086:"Intel"}.get(desc.vendor,"Unknown"),
                                "vram_total":reading(desc.dedicated),"shared_limit":reading(desc.shared)})
            finally:
                method(adapter,2,ct.c_uint32)(adapter)
    finally:
        method(factory,2,ct.c_uint32)(factory)
    return devices


class CounterNumber(ct.Union):
    _fields_ = [("double",ct.c_double),("large",ct.c_int64)]


class CounterValue(ct.Structure):
    _anonymous_ = ("number",)
    _fields_ = [("status",ct.c_uint32),("number",CounterNumber)]


class CounterItem(ct.Structure):
    _fields_ = [("name",ct.c_wchar_p),("value",CounterValue)]


class WindowsCounters:
    def __init__(self):
        self.library = ct.WinDLL("pdh.dll")
        self.query = ct.c_void_p()
        self.handles = {}
        lib = self.library
        lib.PdhOpenQueryW.argtypes = [ct.c_wchar_p,ct.c_size_t,ct.POINTER(ct.c_void_p)]
        lib.PdhAddEnglishCounterW.argtypes = [ct.c_void_p,ct.c_wchar_p,ct.c_size_t,ct.POINTER(ct.c_void_p)]
        lib.PdhCollectQueryData.argtypes = [ct.c_void_p]
        lib.PdhCloseQuery.argtypes = [ct.c_void_p]
        lib.PdhGetFormattedCounterArrayW.argtypes = [ct.c_void_p,ct.c_uint32,ct.POINTER(ct.c_uint32),
                                                    ct.POINTER(ct.c_uint32),ct.c_void_p]
        if lib.PdhOpenQueryW(None,0,ct.byref(self.query)) != 0:
            raise OSError("PDH query unavailable")
        for key,path in {"engines":r"\GPU Engine(*)\Utilization Percentage",
                         "dedicated":r"\GPU Adapter Memory(*)\Dedicated Usage",
                         "shared":r"\GPU Adapter Memory(*)\Shared Usage"}.items():
            handle = ct.c_void_p()
            if lib.PdhAddEnglishCounterW(self.query,path,0,ct.byref(handle)) == 0:
                self.handles[key] = handle
        lib.PdhCollectQueryData(self.query)
        self.last = monotonic()

    def sample(self):
        elapsed = monotonic() - self.last
        self.last = monotonic()
        if self.library.PdhCollectQueryData(self.query) != 0:
            return {}
        result = {}
        for key,handle in self.handles.items():
            if key=="engines" and elapsed>15:
                continue
            size, count = ct.c_uint32(),ct.c_uint32()
            self.library.PdhGetFormattedCounterArrayW(handle,0x200,ct.byref(size),ct.byref(count),None)
            if not 0 < size.value <= 8*1024**2:
                continue
            buffer = ct.create_string_buffer(size.value)
            if self.library.PdhGetFormattedCounterArrayW(handle,0x200,ct.byref(size),ct.byref(count),buffer) != 0:
                continue
            items = ct.cast(buffer,ct.POINTER(CounterItem))
            result[key] = [(items[i].name,items[i].value.double) for i in range(count.value)
                           if items[i].value.status in (0,1) and math.isfinite(items[i].value.double)
                           and items[i].value.double >= 0]
        return result

    def close(self):
        if self.query:
            self.library.PdhCloseQuery(self.query)
            self.query = ct.c_void_p()


def counter_values(rows, adapter, *, engines=False):
    groups = {}
    for name,value in rows:
        match = re.search(r"luid_0x([a-f0-9]+)_0x([a-f0-9]+)_phys_(\d+)(.*)",name,re.I)
        if not match or f"{int(match[1],16):08x}_{int(match[2],16):08x}" != adapter:
            continue
        engine = re.search(r"_eng_(\d+)_",match[4]) if engines else None
        key = (match[3],engine[1] if engine else "memory")
        groups[key] = groups.get(key,0) + value
    if not groups:
        return None
    return round(min(100,max(groups.values())),1) if engines else int(sum(groups.values()))


def npu_devices(rows):
    devices = []
    for row in rows:
        name, vendor = str(row.get("name") or ""),str(row.get("vendor") or "")
        if row.get("class") not in ("ComputeAccelerator","NeuralProcessor") and not re.search(
                r"AI Boost|\bNPU\b|AMD IPU|Hexagon",name,re.I):
            continue
        combined = name + " " + vendor + " " + str(row.get("id", ""))
        brand = ("Intel" if re.search(r"Intel|VEN_8086",combined,re.I) else
                 "AMD" if re.search(r"AMD|VEN_1022|VEN_1002",combined,re.I) else
                 "Qualcomm" if re.search(r"Qualcomm|QCOM|VEN_17CB",combined,re.I) else "Unknown")
        # A broad compute-accelerator class is a candidate until a named NPU is identified.
        confirmed = bool(re.search(r"AI Boost|\bNPU\b|AMD IPU|Hexagon",name,re.I))
        devices.append({"id":row["id"],"kind":"npu" if confirmed else "accelerator","name":name,"vendor":brand,
                        "driver":reading(row.get("driver")),"driver_state":reading(row.get("problem")),
                        "utilization":reading(status="unsupported"),"vram_total":reading(status="unsupported"),
                        "vram_used":reading(status="unsupported"),"vram_available":reading(status="unsupported"),
                        "verified_inference":False})
    return devices


class HardwareMonitor:
    def __init__(self, inventory=None, adapters=dxgi_adapters, counters=WindowsCounters, *, windows=None):
        self.stop = Event()
        self.inventory = inventory if inventory is not None else lambda:windows_inventory(self.stop)
        self.adapters, self.counter_factory = adapters,counters
        self.windows = os.name == "nt" if windows is None else windows
        self.devices = []
        self.inventory_at = None
        self.inventory_state = "unknown"
        self.counters = None
        self.sampled = self.refreshed = self.attempted = float("-inf")
        self.cached = None
        self.lock = Lock()
        self.providers = []
        self.provider_state = "not-checked"
        self.provider_checked_at = None
        self.npu_inventory_state = "unknown"
        self.refresh_thread = None
        self.closed = False

    def refresh_inventory(self):
        rows, devices = [], []
        npu_state = state = "unknown"
        try:
            rows = self.inventory()
            npu_state = "available"
        except (OSError,ValueError,subprocess.SubprocessError):
            pass
        try:
            devices = self.adapters()
            state = "available"
        except (OSError,ValueError,subprocess.SubprocessError):
            pass
        for device in devices:
            row = next((row for row in rows if row.get("name")==device["name"]),{})
            device.update(driver=reading(row.get("driver")),driver_state=reading(row.get("problem")),
                          verified_inference=False)
        with self.lock:
            self.refreshed = monotonic()
            self.devices = (devices + npu_devices(rows))[:32]
            self.inventory_state, self.npu_inventory_state = state,npu_state
            self.inventory_at = int(time())
            self.cached = None

    def snapshot(self):
        with self.lock:
            now = monotonic()
            if self.cached is not None and now - self.sampled < 3:
                return self.cached
            if not self.windows:
                self.inventory_state = "unsupported"
            elif not self.closed and now - self.refreshed >= 60 and not (
                    self.refresh_thread and self.refresh_thread.is_alive()):
                self.refreshed = now
                self.refresh_thread = Thread(target=self.refresh_inventory,daemon=True,name="hardware-inventory")
                self.refresh_thread.start()
            if self.windows and not self.closed and self.counters is None and now - self.attempted >= 60:
                self.attempted = now
                try:
                    self.counters = self.counter_factory()
                except (OSError,ValueError):
                    pass
            values = {}
            if self.counters is not None:
                try:
                    values = self.counters.sample()
                except (OSError,ValueError):
                    self.counters.close()
                    self.counters = None
            devices = []
            for device in self.devices:
                item = dict(device)
                if device["kind"] == "gpu":
                    used = counter_values(values.get("dedicated",[]),device["id"])
                    total = device["vram_total"]["value"]
                    # Reject contradictory driver counters instead of manufacturing free memory.
                    if used is not None and used > total:
                        used = None
                    item.update(utilization=reading(counter_values(values.get("engines",[]),device["id"],engines=True)),
                                vram_used=reading(used),vram_available=reading(total-used if used is not None else None),
                                shared_used=reading(counter_values(values.get("shared",[]),device["id"])))
                devices.append(item)
            self.sampled = now
            self.cached = {"schema":1,"checked_at":int(time()),"inventory_at":self.inventory_at,
                           "state":self.inventory_state,"devices":devices,
                           "npu_present":reading(any(d["kind"]=="npu" for d in devices)
                                                 if self.npu_inventory_state=="available" else None),
                           "providers":self.providers,"provider_state":self.provider_state,
                           "provider_checked_at":self.provider_checked_at}
            return self.cached

    def set_providers(self, providers, state):
        with self.lock:
            self.providers, self.provider_state, self.provider_checked_at = providers,state,int(time())
            self.cached = None

    def close(self):
        with self.lock:
            self.closed = True
            self.stop.set()
            if self.counters:
                self.counters.close()
                self.counters = None
        if self.refresh_thread:
            self.refresh_thread.join(timeout=1)
