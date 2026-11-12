"""Workspace identity; legacy app.py release versions are deliberately separate."""
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import subprocess
import sys

VERSION = "0.7.0"
CHANNEL = "Development"


@lru_cache(maxsize=1)
def build_info():
    root = Path(__file__).resolve().parent
    stamp = root / "workspace-build.json"
    if getattr(sys, "frozen", False):
        value = json.loads(stamp.read_text(encoding="utf-8"))
        if value.get("version") != VERSION or value.get("channel") != CHANNEL:
            raise ValueError("工作程序建置版本不符，請重新安裝完整的 Workspace。")
        return value
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                         text=True, stderr=subprocess.DEVNULL, timeout=5).strip()
    except (OSError, subprocess.SubprocessError):
        commit = "unknown"
    return {"version": VERSION, "channel": CHANNEL, "commit": commit,
            "target": "Windows x64" if os.name == "nt" else sys.platform, "signed": False}


def require_identity(value, expected_version=VERSION, expected_commit=None):
    if (not isinstance(value, dict) or value.get("version") != expected_version
            or value.get("channel") != CHANNEL
            or expected_commit and value.get("commit") != expected_commit):
        raise ValueError("App 與工作程序版本不一致。請關閉程式，使用完整 Workspace 安裝包重新安裝；不會自動重送任務。")
    return value
