"""Detect resources used by the Windows CPU engine and estimate model fit."""
import ctypes
from dataclasses import dataclass
from enum import IntEnum
import os
from pathlib import Path
import shutil

MIB = 1024 ** 2
GIB = 1024 * MIB
FIT_LABELS = ("適合", "記憶體偏緊", "待確認", "記憶體不足", "磁碟空間不足")


class Fit(IntEnum):
    GOOD = 0
    TIGHT = 1
    UNKNOWN = 2
    LOW_RAM = 3
    LOW_DISK = 4


@dataclass(frozen=True)
class Hardware:
    cpu_threads: int | None
    ram_total: int | None
    ram_available: int | None
    disk_available: int | None


class MemoryStatus(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_uint32),
        ("memory_load", ctypes.c_uint32),
        ("total_physical", ctypes.c_uint64),
        ("available_physical", ctypes.c_uint64),
        ("total_page_file", ctypes.c_uint64),
        ("available_page_file", ctypes.c_uint64),
        ("total_virtual", ctypes.c_uint64),
        ("available_virtual", ctypes.c_uint64),
        ("available_extended_virtual", ctypes.c_uint64),
    ]


def detect_hardware(model_dir):
    total = available = disk = None
    if os.name == "nt":
        memory = MemoryStatus(length=ctypes.sizeof(MemoryStatus))
        get_memory = ctypes.WinDLL("kernel32").GlobalMemoryStatusEx
        get_memory.argtypes = (ctypes.POINTER(MemoryStatus),)
        get_memory.restype = ctypes.c_int
        if get_memory(ctypes.byref(memory)):
            total, available = memory.total_physical, memory.available_physical

    model_dir = Path(model_dir)
    try:
        disk = shutil.disk_usage(model_dir if model_dir.exists() else model_dir.parent).free
    except OSError:
        pass
    return Hardware(os.cpu_count(), total, available, disk)


def estimate_ram(model_bytes):
    # Allow for weights, cache and working memory at the app's 2048-token CPU setting.
    return model_bytes + (model_bytes + 3) // 4 + 768 * MIB


def model_fit(hardware, model_bytes, *, installed=False):
    """Return a rank into FIT_LABELS. Lower ranks are preferred."""
    if not model_bytes:
        return Fit.UNKNOWN
    ram = estimate_ram(model_bytes)
    if not installed and hardware.disk_available is not None and hardware.disk_available < model_bytes:
        return Fit.LOW_DISK
    if hardware.ram_available is not None and hardware.ram_available < ram:
        return Fit.LOW_RAM
    if hardware.ram_available is None or (hardware.disk_available is None and not installed):
        return Fit.UNKNOWN
    return Fit.GOOD if hardware.ram_available >= ram + GIB else Fit.TIGHT
