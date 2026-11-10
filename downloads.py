"""Download model files with bounded parallel HTTP range requests."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import nullcontext
import hashlib
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

from download_recovery import BLOCK, download_lock

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


def download_model(url, directory, workers, cancel, report, *, opener=open_download, recovery=None,
                   expected_size=None, expected_sha=None, before_publish=None):
    target = Path(directory).resolve() / model_filename(url)
    return download_file(url, target, workers, cancel, report, validate=check_gguf, opener=opener,
                         recovery=recovery, expected_size=expected_size, expected_sha=expected_sha,
                         before_publish=before_publish)


def download_file(url, target, workers, cancel, report, *, validate, opener=open_download,
                  recovery=None, expected_size=None, expected_sha=None, before_publish=None):
    """Transfer to a caller-validated destination and atomically publish after verification."""
    if not 1 <= workers <= 16:
        raise ValueError("下載執行緒須介於 1 到 16。")
    target.parent.mkdir(parents=True, exist_ok=True)
    with download_lock(recovery, target) if recovery else nullcontext() as checkpoints:
        return _download(url, target, workers, cancel, report, opener, checkpoints,
                         expected_size, expected_sha, before_publish, validate)


def _download(url, target, workers, cancel, report, opener, checkpoints, expected_size, expected_sha,
              before_publish, validate):
    if target.exists() or target.is_symlink():
        if checkpoints:
            checkpoints.discard_unrecoverable()
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
    if expected_size is not None and total and total != expected_size:
        raise ValueError("下載長度與模型倉庫公布的大小不符。")
    resumed = checkpoints.prepare(url, total, etag, expected_sha) if checkpoints else None
    if resumed is None:
        checkpoints = None
    resumable = checkpoints and ranged and (etag or expected_sha)
    if checkpoints and not resumable and resumed:
        checkpoints.clear()
        resumed = checkpoints.prepare(url, total, etag, expected_sha)
    if resumable:
        received = sum(min(BLOCK, total - int(index) * BLOCK) for index in resumed)
        if total >= BLOCK:
            count = min(workers, (total + BLOCK - 1) // BLOCK)
    if total - received > shutil.disk_usage(target.parent).free:
        raise OSError("可用磁碟空間不足，無法下載此模型。")
    report(received, total, count)
    if checkpoints:
        staging = checkpoints.staging
        staging.touch(exist_ok=True)
    else:
        with NamedTemporaryFile(dir=target.parent, prefix=".model-", suffix=".part", delete=False) as stream:
            staging = Path(stream.name)

    def download_range(start, end, block=None):
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
            if block is not None:
                checkpoints.checkpoint(block, output, start, end - start + 1)

    keep = False
    try:
        if ranged:
            with staging.open("r+b") as output:
                output.truncate(total)
            with ThreadPoolExecutor(max_workers=count, thread_name_prefix="model-range") as pool:
                if resumable and total >= BLOCK:
                    def download_blocks(worker):
                        for index in range(worker, (total + BLOCK - 1) // BLOCK, count):
                            if str(index) not in resumed:
                                download_range(index * BLOCK, min(total, (index + 1) * BLOCK) - 1, index)
                    jobs = [pool.submit(download_blocks, index) for index in range(count)]
                else:
                    jobs = [pool.submit(download_range, total * index // count, total * (index + 1) // count - 1)
                            for index in range(count)]
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
        if expected_size is not None and received != expected_size:
            raise ValueError("下載長度與模型倉庫公布的大小不符。")
        validate(staging)
        if expected_sha or before_publish:
            digest = hashlib.sha256()
            with staging.open("rb") as source:
                while data := source.read(1024 ** 2):
                    check_cancelled()
                    digest.update(data)
            sha = digest.hexdigest()
            if expected_sha and sha != expected_sha:
                raise ValueError("模型 SHA-256 與固定版本的倉庫記錄不符。")
            check_cancelled()
            if before_publish:
                before_publish(staging, sha)
        if os.name == "nt":
            staging.rename(target)
        else:
            os.link(staging, target)
        return target
    except (URLError, ConnectionError, TimeoutError, HTTPException):
        keep = bool(resumable and checkpoints.record["blocks"] and not cancel.is_set())
        raise
    finally:
        if not keep:
            if checkpoints:
                checkpoints.clear()
            else:
                staging.unlink(missing_ok=True)
