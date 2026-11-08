"""Find and download stable Local LLM releases from the project's GitHub repository."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
import time
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from downloads import DownloadCancelled, HttpsRedirect, check_encoding

REPOSITORY = "liu11-21/local-llm"
RELEASES = f"https://github.com/{REPOSITORY}/releases"
LATEST = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
MAX_EXE = 1024 ** 3
VERSION_PATTERN = re.compile(r"(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})")


@dataclass(frozen=True)
class Update:
    tag: str
    name: str
    url: str
    size: int
    sha256: str


class ReleaseRedirect(HttpsRedirect):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        host = urlsplit(newurl).netloc
        if host not in {"github.com", "api.github.com", "release-assets.githubusercontent.com",
                        "objects.githubusercontent.com"}:
            raise ValueError("更新來源重新導向至非預期的 GitHub 網域。")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_github(url, accept):
    request = Request(url, headers={"Accept": accept, "Accept-Encoding": "identity", "User-Agent": "LocalLLM-Updater"})
    return build_opener(ReleaseRedirect()).open(request, timeout=15)


def select_update(release, current, *, installer=False):
    tag = release.get("tag_name", "")
    match = VERSION_PATTERN.fullmatch(tag[1:]) if isinstance(tag, str) and tag.startswith("v") else None
    if release.get("draft") or release.get("prerelease") or match is None:
        raise ValueError("GitHub 未提供可辨識的正式版本。")
    current_match = VERSION_PATTERN.fullmatch(current)
    if tuple(map(int, match.groups())) <= tuple(map(int, current_match.groups())):
        return None
    suffix = "-Setup.exe" if installer else ".exe"
    name = f"LocalLLM-{tag}-Windows-x64{suffix}"
    url = f"{RELEASES}/download/{tag}/{name}"
    for asset in release.get("assets", []):
        if asset.get("name") != name or asset.get("state") != "uploaded":
            continue
        size, digest = asset.get("size"), asset.get("digest")
        if (asset.get("browser_download_url") == url and type(size) is int and 0 < size <= MAX_EXE
                and isinstance(digest, str) and re.fullmatch(r"sha256:[a-fA-F0-9]{64}", digest)):
            return Update(tag, name, url, size, digest[7:].lower())
    raise ValueError(f"{tag} 暫無可校驗的 Windows x64 發行檔。")


def check_for_update(current, *, installer=False):
    with open_github(LATEST, "application/vnd.github+json") as response:
        raw = response.read(1024 ** 2 + 1)
    if len(raw) > 1024 ** 2:
        raise ValueError("GitHub 版本資料超出大小限制。")
    return select_update(json.loads(raw), current, installer=installer)


def download_update(update, directory, cancel, progress):
    def check_cancel():
        if cancel.is_set():
            raise DownloadCancelled()

    check_cancel()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / update.name
    if target.is_file() and target.stat().st_size == update.size:
        with target.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        check_cancel()
        if digest == update.sha256:
            return target

    temp = None
    try:
        with open_github(update.url, "application/octet-stream") as response:
            check_encoding(response)
            length = response.headers.get("Content-Length")
            if response.status != 200 or (length is not None and length != str(update.size)):
                raise ValueError("更新檔大小與發行資料不符。")
            with NamedTemporaryFile(dir=directory, prefix=".update-", suffix=".part", delete=False) as output:
                temp = Path(output.name)
                digest = hashlib.sha256()
                received = 0
                last_report = 0.0
                while True:
                    check_cancel()
                    block = response.read1(256 * 1024)
                    if not block:
                        break
                    received += len(block)
                    if received > update.size:
                        raise ValueError("更新檔大小與發行資料不符。")
                    output.write(block)
                    digest.update(block)
                    now = time.monotonic()
                    if now - last_report >= 0.15 or received == update.size:
                        progress(received, update.size)
                        last_report = now
                if received != update.size or digest.hexdigest() != update.sha256:
                    raise ValueError("更新檔 SHA-256 或大小核對失敗，請重試。")
        check_cancel()
        if os.name == "nt":
            try:
                Path(f"{temp}:Zone.Identifier").write_text(
                    f"[ZoneTransfer]\r\nZoneId=3\r\nHostUrl={update.url}\r\n", encoding="ascii", newline=""
                )
            except OSError:
                pass  # Some filesystems do not support Windows alternate streams.
        os.replace(temp, target)
        return target
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
