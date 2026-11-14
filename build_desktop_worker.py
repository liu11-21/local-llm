"""Build the Windows desktop IPC worker as a directory, without UPX or AI runtimes."""
import os
from importlib.metadata import distribution
from pathlib import Path
import shutil
import subprocess
import sys
import json
from check_workspace_version import check
from workspace_version import build_info, VERSION
from release_evidence import seed

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"


def main():
    if os.name != "nt" or sys.maxsize <= 2**32:
        raise SystemExit("A Windows x64 Python interpreter is required.")
    check()
    BUILD.mkdir(exist_ok=True)
    stamp = BUILD / "workspace-build.json"
    stamp.write_text(json.dumps(build_info()), encoding="utf-8")
    version_file=BUILD / "worker-version.txt"
    numeric=tuple(map(int,VERSION.split(".")))+(0,)
    version_file.write_text("VSVersionInfo(ffi=FixedFileInfo(filevers="+repr(numeric)+",prodvers="+repr(numeric)+",mask=0x3f,flags=0,OS=0x40004,fileType=0x1,subtype=0,date=(0,0)),kids=[StringFileInfo([StringTable('040904B0',[StringStruct('CompanyName','Local LLM'),StringStruct('FileDescription','Local LLM Workspace Worker'),StringStruct('FileVersion','"+VERSION+"'),StringStruct('ProductName','Local LLM Workspace'),StringStruct('ProductVersion','"+VERSION+"'),StringStruct('OriginalFilename','LocalLLMWorker.exe')])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])",encoding="utf-8")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--console", "--noupx",
         "--name", "LocalLLMWorker", "--version-file", str(version_file), "--icon", str(ROOT / "logo.ico"),
         "--add-data", f"{stamp}:.",
         "--add-data", f"{ROOT / 'llama-app-runtime.json'}:.",
         "--add-data", f"{ROOT / 'third_party' / 'llama.cpp-b12360-LICENSE'}:third_party",
         "--add-data", f"{ROOT / 'third_party' / 'llama.cpp-b11810-LICENSE'}:third_party",
         "--add-data", f"{ROOT / 'openvino-packages.lock.json'}:.",
         "--add-data", f"{ROOT / 'openvino_runner.py'}:.",
         "--add-data", f"{ROOT / 'benchmark_openvino.py'}:.",
         "--exclude-module", "tkinter", "--distpath", str(BUILD / "desktop-worker"),
         "--workpath", str(BUILD / "desktop-pyinstaller"), "--specpath", str(BUILD),
         str(ROOT / "desktop_worker.py")],
        check=True, cwd=ROOT,
    )
    notices = BUILD / "desktop-worker" / "LocalLLMWorker" / "notices"
    notices.mkdir(exist_ok=True)
    shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", notices / "Python-LICENSE.txt")
    packager = distribution("PyInstaller")
    license_file = next(file for file in packager.files if file.name == "COPYING.txt")
    shutil.copyfile(packager.locate_file(license_file), notices / "PyInstaller-COPYING.txt")
    for name in ("cryptography", "cffi", "pycparser", "zstandard"):
        package = distribution(name)
        for file in package.files or ():
            if file.name.startswith("LICENSE"):
                shutil.copyfile(package.locate_file(file), notices / f"{name}-{file.name}.txt")
    # Keep source development usable without fetching Cargo sources. Release CI
    # replaces this tracked review snapshot with its exact resolved build graph.
    seed(BUILD / "release-notices")


if __name__ == "__main__":
    main()
