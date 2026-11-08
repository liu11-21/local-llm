"""Download GGUF files with bounded parallel HTTP range requests."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.client import HTTPException
import os
from pathlib import Path
import re
import shutil
from tempfile import NamedTemporaryFile
from threading import Event, Lock
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

BLOCK_SIZE = 256 * 1024
RETRY_SPAN = 4 * 1024 ** 2
RANGE_HEADER = re.compile(r"bytes (\d+)-(\d+)/(\d+)")
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class DownloadCancelled(Exception):
    pass


def model_filename(url):
    parts = urlsplit(url)
    name = unquote(parts.path.rsplit("/", 1)[-1])
    if parts.scheme != "https" or not parts.hostname or parts.username is not None:
        raise ValueError("請輸入公開的 HTTPS 模型下載網址。")
    if (
        not re.fullmatch(r"[\w.-]{1,175}\.gguf", name, re.IGNORECASE)
        or name.startswith(".")
        or name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL"}
        or re.fullmatch(r"(?:COM|LPT)[0-9¹²³]", name.split(".")[0], re.IGNORECASE)
    ):
        raise ValueError("網址須指向有效的 .gguf 檔案。")
    if re.search(r"-\d{5}-of-\d{5}\.gguf$", name, re.IGNORECASE):
        raise ValueError("請選擇單一 GGUF 檔案的量化版本。")
    return name


class HttpsRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if parsed.scheme != "https" or parsed.username is not None:
            raise ValueError("下載來源重新導向至非 HTTPS 或含登入資訊的網址。")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_download(url, byte_range=None, etag=None):
    headers = {"Accept-Encoding": "identity", "User-Agent": "LocalLLM/0.1"}
    if byte_range:
        headers["Range"] = f"bytes={byte_range[0]}-{byte_range[1]}"
    if etag:
        headers["If-Range"] = etag
    request = Request(url, headers=headers)
    return build_opener(HttpsRedirect()).open(request, timeout=15)


def check_encoding(response):
    if response.headers.get("Content-Encoding", "identity").lower() != "identity":
        raise ValueError("下載來源傳回壓縮內容，無法安全地合併位元組範圍。")


def content_range(response):
    match = RANGE_HEADER.fullmatch(response.headers.get("Content-Range", ""))
    if response.status != 206 or match is None:
        raise ValueError("下載來源未回傳有效的 HTTP 位元組範圍。")
    return tuple(map(int, match.groups()))


def entity_tag(response):
    value = response.headers.get("ETag")
    return value if value and value.startswith('"') and value.endswith('"') else None


def check_gguf(path):
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) < 24 or header[:4] != b"GGUF" or int.from_bytes(header[4:8], "little") not in (2, 3):
        raise ValueError("檔案的標頭不是支援的 GGUF 格式。")


def download_model(url, directory, workers, cancel, report, *, opener=open_download):
    """Report (downloaded bytes, total bytes, worker count) and publish only complete files."""
    if not 1 <= workers <= 16:
        raise ValueError("下載執行緒須介於 1 到 16。")
    target = Path(directory) / model_filename(url)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"模型已存在：{target.name}")

    stop = Event()
    lock = Lock()
    received = 0

    def check_cancelled():
        if cancel.is_set() or stop.is_set():
            raise DownloadCancelled()

    def advance(length):
        nonlocal received
        with lock:
            received += length
            report(received, total, count)

    def probe_source():
        with opener(url, (0, 0)) as probe:
            check_encoding(probe)
            if probe.status == 206:
                first, last, length = content_range(probe)
                if (first, last) != (0, 0) or length < 24 or len(probe.read(2)) != 1:
                    raise ValueError("下載來源回傳錯誤的檔案範圍。")
                return length, True, entity_tag(probe)
            if probe.status == 200:
                return int(probe.headers.get("Content-Length") or 0), False, entity_tag(probe)
            raise ValueError(f"下載來源回傳 HTTP {probe.status}。")

    for attempt in range(3):
        check_cancelled()
        try:
            total, ranged, etag = probe_source()
            break
        except HTTPError as error:
            if error.code not in RETRYABLE_STATUS or attempt == 2:
                raise
        except (URLError, ConnectionError, TimeoutError, HTTPException):
            if attempt == 2:
                raise ConnectionError("無法連接模型下載來源。請檢查網路，或稍後重試。") from None
        if cancel.wait(0.5 * (attempt + 1)):
            raise DownloadCancelled()
    count = min(workers, total) if ranged else 1

    if total > shutil.disk_usage(target.parent).free:
        raise OSError("可用磁碟空間不足，無法下載此模型。")
    report(0, total, count)
    with NamedTemporaryFile(dir=target.parent, prefix=".model-", suffix=".part", delete=False) as stream:
        staging = Path(stream.name)

    def download_range(start, end):
        position = start
        attempt = 0
        span = end - start + 1
        with staging.open("r+b", buffering=0) as output:
            output.seek(start)
            while position <= end:
                check_cancelled()
                last = min(end, position + span - 1)
                try:
                    with opener(url, (position, last), etag) as response:
                        check_encoding(response)
                        if content_range(response) != (position, last, total) or entity_tag(response) != etag:
                            raise ValueError("檔案在下載期間變更，或伺服器回傳了錯誤的區段。")
                        declared = response.headers.get("Content-Length")
                        if declared is not None and int(declared) != last - position + 1:
                            raise ValueError("下載區段長度與 HTTP 標頭不符。")
                        while position <= last:
                            check_cancelled()
                            chunk = response.read1(min(BLOCK_SIZE, last - position + 1))
                            if not chunk:
                                raise ConnectionError("下載區段中途斷線。")
                            if output.write(chunk) != len(chunk):
                                raise OSError("無法完整寫入下載區段。")
                            position += len(chunk)
                            advance(len(chunk))
                    attempt = 0
                    continue
                except HTTPError as error:
                    if error.code not in RETRYABLE_STATUS or attempt == 2:
                        raise
                except (URLError, ConnectionError, TimeoutError, HTTPException):
                    if attempt == 2:
                        raise ConnectionError("模型下載連線中斷。請檢查網路後重試；未留下不完整的模型。") from None
                attempt += 1
                span = min(span, RETRY_SPAN)
                if cancel.wait(0.5 * attempt):
                    raise DownloadCancelled()

    try:
        if ranged:
            with staging.open("r+b") as output:
                output.truncate(total)
            with ThreadPoolExecutor(max_workers=count, thread_name_prefix="gguf-range") as pool:
                jobs = [
                    pool.submit(download_range, total * index // count, total * (index + 1) // count - 1)
                    for index in range(count)
                ]
                try:
                    for job in as_completed(jobs):
                        job.result()
                except Exception:
                    stop.set()
                    for job in jobs:
                        job.cancel()
                    raise
        else:
            with opener(url) as response, staging.open("wb") as output:
                check_encoding(response)
                if response.status != 200 or entity_tag(response) != etag:
                    raise ValueError("檔案在下載期間變更。")
                while True:
                    check_cancelled()
                    chunk = response.read1(BLOCK_SIZE)
                    if not chunk:
                        break
                    if total and received + len(chunk) > total:
                        raise ValueError("下載內容超出檔案長度。")
                    output.write(chunk)
                    advance(len(chunk))
        check_cancelled()
        if total and received != total:
            raise ValueError("模型下載不完整。")
        check_gguf(staging)
        if os.name == "nt":
            staging.rename(target)
        else:
            os.link(staging, target)
        return target
    finally:
        staging.unlink(missing_ok=True)
