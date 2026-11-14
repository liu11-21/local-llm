"""Estimate GGUF placement for a llama.cpp session before launching it."""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import struct
import subprocess

from hardware import MIB, detect_hardware, estimate_ram

DEVICE_LINE = re.compile(
    r"^\s*((?:CUDA|Vulkan)\d+):\s*(.*?)\s*\(([\d,]+) MiB,\s*([\d,]+) MiB free\)\s*$",
    re.MULTILINE,
)
SCALAR_BYTES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}


@dataclass(frozen=True)
class LoadPlan:
    device: str | None
    layers: int
    total_layers: int
    vram: int
    ram: int
    mapped_bytes: int
    device_free: int | None
    shared: bool = False
    mmap_args: tuple[str, ...] = ()


def engine_environment():
    return {key: value for key, value in os.environ.items() if not key.upper().startswith("LLAMA_")}


def block_count(model):
    """Read only GGUF metadata, never model tensor contents."""
    limit = 64 * MIB
    with Path(model).open("rb") as stream:
        def read(size):
            if stream.tell() + size > limit:
                raise ValueError("GGUF metadata exceeds read limit")
            value = stream.read(size)
            if len(value) != size:
                raise ValueError("Incomplete GGUF metadata")
            return value

        def skip(size):
            if stream.tell() + size > limit:
                raise ValueError("GGUF metadata exceeds read limit")
            stream.seek(size, os.SEEK_CUR)

        def number(format):
            return struct.unpack("<" + format, read(struct.calcsize("<" + format)))[0]

        if read(4) != b"GGUF" or number("I") not in (2, 3):
            return 0
        number("Q")  # Tensor count.
        for _ in range(min(number("Q"), 50_000)):
            key = read(number("Q"))
            kind = number("I")
            if key.endswith(b".block_count") and kind == 4:
                count = number("I")
                return count if 0 < count <= 1024 else 0
            if kind == 8:
                skip(number("Q"))
            elif kind == 9:
                item_kind, count = number("I"), number("Q")
                if item_kind == 8 and count <= 2_000_000:
                    for _ in range(count):
                        skip(number("Q"))
                else:
                    skip(SCALAR_BYTES[item_kind] * count)
            else:
                skip(SCALAR_BYTES[kind])
    return 0


def engine_output(executable, option):
    try:
        output = subprocess.run(
            [str(executable), *(["version"] if option=="--version" else ["serve",option]) ] if Path(executable).name.lower() in ("llama.exe","llama") else [str(executable), option], cwd=Path(executable).parent, env=engine_environment(),
            capture_output=True, timeout=8, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if output.returncode:
        return ""
    return (output.stdout + b"\n" + output.stderr).decode("utf-8", errors="replace")


def engine_devices(executable):
    log = engine_output(executable, "--list-devices")
    if Path(executable).name.lower() in ("llama.exe","llama"):
        # CUDA needs a separately validated hardware run before enabling it in 0.8.
        log = "\n".join(line for line in log.splitlines() if not line.lstrip().startswith("CUDA"))
    # Vulkan's device list can report a shared heap. Budget against host RAM
    # whenever it cannot be identified as dedicated.
    return [
        (name, int(free.replace(",", "")) * MIB, name.startswith("Vulkan") and "NVIDIA" not in adapter.upper())
        for name, adapter, _, free in DEVICE_LINE.findall(log)
    ]


def allocate(model_bytes, blocks, devices, ram_available=None, mmap_args=()):
    reserve = 768 * MIB
    budgets = [
        (name, min(free, max(0, (ram_available or 0) - 1024 * MIB)) if shared else free, shared)
        for name, free, shared in devices
    ]
    device, free, shared = max(budgets, key=lambda item: (not item[2], item[1]), default=(None, 0, False))
    per_layer = (model_bytes + blocks - 1) // blocks if blocks else 0
    layers = min(blocks, max(0, (free - reserve) // per_layer)) if per_layer else 0
    if not layers:
        return LoadPlan(None, 0, blocks, 0, estimate_ram(model_bytes), model_bytes, None, mmap_args=mmap_args)
    weights = min(model_bytes, layers * per_layer)
    ram = estimate_ram(model_bytes - weights)
    if shared:
        ram += weights + reserve
    return LoadPlan(device, layers, blocks, weights + reserve, ram, model_bytes, free, shared, mmap_args)


def plan_load(executable, model):
    model = Path(model)
    size = model.stat().st_size
    try:
        blocks = block_count(model)
    except (OSError, ValueError, KeyError):
        blocks = 0
    help_text = engine_output(executable, "--help")
    mmap_args = ("--load-mode", "mmap") if "--load-mode" in help_text else ()
    if not mmap_args and re.search(r"(?<![\w-])--mmap\b", help_text):
        mmap_args = ("--mmap",)
    return allocate(size, blocks, engine_devices(executable) if blocks else [],
                    detect_hardware(model.parent).ram_available, mmap_args)
