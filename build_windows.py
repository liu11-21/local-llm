"""Build the portable Windows EXE or a per-user Windows installer."""
from argparse import ArgumentParser
from pathlib import Path
import re
import shutil
import subprocess
import sys

from app import VERSION

ROOT = Path(__file__).resolve().parent


def build(*, iscc=None, thumbprint=None):
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
    name = "LocalLLM" if iscc else f"LocalLLM-v{VERSION}-Windows-x64"
    destination = build_dir / "install-bundle" if iscc else ROOT / "dist"
    args = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--noupx", "--windowed",
        "--onedir" if iscc else "--onefile", "--name", name, "--icon", str(ROOT / "logo.ico"),
        "--version-file", str(version_file), "--specpath", str(build_dir),
        "--workpath", str(build_dir / "pyinstaller"), "--distpath", str(destination),
        "--add-data", f"{ROOT / 'logo.png'}:.",
    ]
    for file in sorted(engine_files):
        args.extend(("--add-data", f"{file}:engine-vulkan"))
    subprocess.run([*args, str(ROOT / "app.py")], cwd=ROOT, check=True)
    if iscc:
        payload = destination / name
        (payload / "LocalLLM.installed").write_text("Local LLM Windows installer\n", encoding="utf-8")
        build_installer(iscc, payload, thumbprint)


def build_installer(iscc, payload, thumbprint):
    args = [str(iscc), f"/DAppVersion={VERSION}", f"/DPayloadDir={payload}", f"/O{ROOT / 'dist'}"]
    if thumbprint:
        signtool = shutil.which("signtool.exe")
        if not signtool:
            raise SystemExit("SignTool is required on PATH for a signed build.")
        signing = ["sign", "/sha1", thumbprint, "/fd", "sha256", "/tr", "http://timestamp.digicert.com", "/td", "sha256"]
        for path in sorted(payload.rglob("*")):
            if path.suffix.lower() not in {".exe", ".dll", ".pyd"}:
                continue
            valid = subprocess.run([signtool, "verify", "/pa", str(path)], capture_output=True).returncode == 0
            if not valid:
                subprocess.run([signtool, *signing, str(path)], check=True)
        args.extend(("/DSigned", f"/Srelease=$q{signtool}$q {' '.join(signing)} $f"))
    subprocess.run([*args, str(ROOT / "installer.iss")], cwd=ROOT, check=True)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--iscc", type=Path, help="Path to ISCC.exe to build Setup instead of the portable EXE.")
    parser.add_argument("--sign-thumbprint", help="Trusted code-signing certificate thumbprint in the current user's store.")
    options = parser.parse_args()
    if options.sign_thumbprint and (not options.iscc or not re.fullmatch(r"[a-fA-F0-9]{40}", options.sign_thumbprint)):
        parser.error("--sign-thumbprint requires --iscc and a 40-character certificate thumbprint.")
    build(iscc=options.iscc, thumbprint=options.sign_thumbprint)
