"""Build the standalone Windows x64 executable from the checked-out source."""
from pathlib import Path
import subprocess
import sys

from app import VERSION

ROOT = Path(__file__).resolve().parent


def build():
    engine = ROOT / "engine-vulkan"
    required = ("llama-server.exe", "llama-server-impl.dll", "llama-common.dll", "llama.dll",
                "ggml.dll", "ggml-base.dll", "ggml-vulkan.dll", "mtmd.dll", "libomp.dll",
                "LICENSE-llama.cpp", "LICENSE-LLVM-OpenMP")
    missing = [name for name in required if not (engine / name).is_file()]
    if missing:
        raise SystemExit("Missing llama.cpp files in engine-vulkan: " + ", ".join(missing))
    engine_files = {*(engine / name for name in required), *engine.glob("ggml*.dll")}
    build_dir = ROOT / "build"
    build_dir.mkdir(exist_ok=True)
    version_file = build_dir / "version.txt"
    version_tuple = (*map(int, VERSION.split(".")), 0)
    version_file.write_text(f"""
VSVersionInfo(
  ffi=FixedFileInfo(filevers={version_tuple}, prodvers={version_tuple}, mask=63,
      flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
      StringStruct('FileDescription', 'Local LLM'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('ProductName', 'Local LLM'),
      StringStruct('ProductVersion', '{VERSION}')])]),
      VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)
""", encoding="utf-8")
    args = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
        "--name", f"LocalLLM-v{VERSION}-Windows-x64", "--icon", str(ROOT / "logo.ico"),
        "--version-file", str(version_file), "--specpath", str(build_dir),
        "--workpath", str(build_dir / "pyinstaller"), "--distpath", str(ROOT / "dist"),
        "--add-data", f"{ROOT / 'logo.png'}:.",
    ]
    for file in sorted(engine_files):
        args.extend(("--add-data", f"{file}:engine-vulkan"))
    subprocess.run([*args, str(ROOT / "app.py")], cwd=ROOT, check=True)


if __name__ == "__main__":
    build()
