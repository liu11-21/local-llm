"""Build the Windows desktop IPC worker as a directory, without UPX or AI runtimes."""
import os
from importlib.metadata import distribution
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"


def main():
    if os.name != "nt" or sys.maxsize <= 2**32:
        raise SystemExit("A Windows x64 Python interpreter is required.")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--console", "--noupx",
         "--name", "LocalLLMWorker", "--icon", str(ROOT / "logo.ico"),
         "--add-data", f"{ROOT / 'third_party' / 'llama.cpp-b11810-LICENSE'}:third_party",
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


if __name__ == "__main__":
    main()
