"""Checkpoint complete ranges in an application-owned model staging directory."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from threading import Lock


BLOCK = 16 * 1024 ** 2
SHA256 = re.compile(r"[0-9a-f]{64}")


def owned(path):
    return not path.is_symlink() and path.resolve() == path.absolute()


def digest_range(stream, offset, length):
    stream.seek(offset)
    digest = hashlib.sha256()
    remaining = length
    while remaining:
        chunk = stream.read(min(remaining, 1024 ** 2))
        if not chunk:
            return None
        digest.update(chunk)
        remaining -= len(chunk)
    return digest.hexdigest()


@contextmanager
def exclusive(path):
    if not owned(path) or (path.exists() and not path.is_file()):
        raise ValueError("下載鎖定檔案不安全。")
    with path.open("a+b") as lock:
        try:
            if os.name == "nt":
                import msvcrt
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError("另一個工作台正在下載同名模型。") from None
        yield


class Checkpoints:
    def __init__(self, root, target):
        self.name = target.name
        self.key = hashlib.sha256(target.name.casefold().encode()).hexdigest()
        self.directory = root / self.key
        self.manifest = self.directory / "resume.json"
        self.staging = self.directory / "data.part"
        self.lock = Lock()
        self.record = None

    def load(self):
        if not owned(self.manifest) or not self.manifest.is_file():
            return None
        try:
            with self.manifest.open(encoding="utf-8") as stream:
                record = json.loads(stream.read(4 * 1024 ** 2))
            if not isinstance(record, dict) or record.get("schema") != 1 or record.get("name", "").casefold() != self.name.casefold():
                return None
            total, blocks = record.get("total"), record.get("blocks")
            if type(total) is not int or total <= 0 or not isinstance(blocks, dict):
                return None
            if any(not re.fullmatch(r"0|[1-9]\d{0,10}", index) or int(index) * BLOCK >= total
                   or not isinstance(digest, str) or not SHA256.fullmatch(digest) for index, digest in blocks.items()):
                return None
            return record
        except (OSError, ValueError, TypeError, AttributeError):
            return None

    def save(self):
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory, prefix="checkpoint-", delete=False) as stream:
            temporary = Path(stream.name)
            try:
                json.dump(self.record, stream, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            except BaseException:
                stream.close()
                temporary.unlink(missing_ok=True)
                raise
        try:
            temporary.replace(self.manifest)
        finally:
            temporary.unlink(missing_ok=True)

    def prepare(self, url, total, etag, expected_sha):
        previous = self.load()
        if not owned(self.staging) or (self.staging.exists() and not self.staging.is_file()):
            return None
        if previous is None and (self.staging.exists() or self.manifest.exists()):
            return None
        self.record = {"schema": 1, "name": self.name, "url": url, "total": total,
                       "etag": etag, "expected_sha": expected_sha, "blocks": {}}
        identity = ("url", "total", "etag") if etag else ("url", "total", "expected_sha")
        if previous and self.staging.exists() and self.staging.stat().st_size == total and all(
            previous.get(key) == self.record[key] for key in identity
        ):
            with self.staging.open("rb") as source:
                for index, digest in previous["blocks"].items():
                    offset = int(index) * BLOCK
                    if digest_range(source, offset, min(BLOCK, total - offset)) == digest:
                        self.record["blocks"][index] = digest
        if self.staging.exists() and not self.record["blocks"]:
            self.staging.unlink()
        self.save()
        return self.record["blocks"].copy()

    def checkpoint(self, index, output, start, size):
        os.fsync(output.fileno())
        digest = digest_range(output, start, size)
        if digest is None:
            raise OSError("無法讀回完整的下載區段。")
        with self.lock:
            self.record["blocks"][str(index)] = digest
            self.save()

    def clear(self):
        self.staging.unlink(missing_ok=True)
        self.manifest.unlink(missing_ok=True)

    def discard_unrecoverable(self):
        if self.load() and owned(self.staging) and (self.staging.is_file() or not self.staging.exists()):
            self.clear()


@contextmanager
def download_lock(root, target):
    root.mkdir(parents=True, exist_ok=True)
    if not owned(root):
        raise ValueError("模型下載暫存目錄不安全。")
    checkpoints = Checkpoints(root, target)
    checkpoints.directory.mkdir(exist_ok=True)
    if not owned(checkpoints.directory):
        raise ValueError("模型下載暫存目錄不安全。")
    with exclusive(checkpoints.directory / "active.lock"):
        yield checkpoints


def recover_downloads(root, models, validate, *, clean=False):
    pending = []
    if not root.is_dir() or not owned(root):
        return pending
    for directory in root.iterdir():
        if not SHA256.fullmatch(directory.name) or not directory.is_dir() or not owned(directory):
            continue
        manifest = directory / "resume.json"
        if not owned(manifest) or not manifest.is_file():
            continue
        try:
            with manifest.open(encoding="utf-8") as stream:
                record = json.loads(stream.read(4 * 1024 ** 2))
            source = validate(record["url"])
            if not source:
                continue
            target = models / source["file"].rsplit("/", 1)[-1]
            checkpoints = Checkpoints(root, target)
            if checkpoints.directory != directory:
                continue
            with exclusive(directory / "active.lock"):
                record = checkpoints.load()
                if not record or record.get("url") != source["source"] or not owned(checkpoints.staging):
                    continue
                if (not target.exists() and checkpoints.staging.is_file()
                        and checkpoints.staging.stat().st_size == record["total"]
                        and (record.get("etag") or record.get("expected_sha")) and record["blocks"]):
                    pending.append({"name": target.name, "url": source["source"], "total": record["total"],
                                    "received": sum(min(BLOCK, record["total"] - int(index) * BLOCK)
                                                    for index in record["blocks"])})
                elif clean:
                    checkpoints.discard_unrecoverable()
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            continue
    return pending
