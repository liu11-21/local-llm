"""Recommended models and public Hugging Face GGUF discovery."""
from http.client import HTTPException
import json
from pathlib import PurePosixPath
import re
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from downloads import model_filename

HUB = "https://huggingface.co"
RECOMMENDED = {
    "bartowski/SmolLM2-135M-Instruct-GGUF": (
        "小型英文測試", "SmolLM2-135M-Instruct-Q4_K_M.gguf",
        105454432, "09816acd5d99df7be770d85ea30822623dab342c",
    ),
    "HuggingFaceTB/SmolLM2-360M-Instruct-GGUF": (
        "輕量英文對話", "smollm2-360m-instruct-q8_0.gguf",
        386404992, "593b5a2e04c8f3e4ee880263f93e0bd2901ad47f",
    ),
    "Qwen/Qwen2.5-0.5B-Instruct-GGUF": (
        "輕量中文對話", "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        491400032, "9217f5db79a29953eb74d5343926648285ec7e67",
    ),
    "Qwen/Qwen2.5-1.5B-Instruct-GGUF": (
        "中文對話", "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        1117320736, "91cad51170dc346986eccefdc2dd33a9da36ead9",
    ),
    "Qwen/Qwen2.5-3B-Instruct-GGUF": (
        "較大型中文對話", "qwen2.5-3b-instruct-q4_k_m.gguf",
        2104932768, "7dabda4d13d513e3e842b20f0d435c732f172cbe",
    ),
}
REPO_ID = re.compile(r"[\w][\w.-]*/[\w][\w.-]*", re.ASCII)
REVISION = re.compile(r"[0-9a-f]{40}")
METADATA_LIMIT = 8 * 1024 * 1024


def download_url(repo, revision, filename):
    return f"{HUB}/{quote(repo, safe='/')}/resolve/{revision}/{quote(filename, safe='/')}"


def recommended_file(repo):
    _, filename, size, revision = RECOMMENDED[repo]
    return filename, size, download_url(repo, revision, filename)


def read_metadata(path):
    request = Request(HUB + path, headers={"Accept": "application/json", "User-Agent": "LocalLLM"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=12) as response:
                content = response.read(METADATA_LIMIT + 1)
            break
        except HTTPError as error:
            with error:
                if error.code in (401, 403):
                    raise ValueError("此模型需要登入或申請存取權。") from error
                if error.code == 429:
                    raise ValueError("Hugging Face 的查詢次數已達上限，請稍後再試。") from error
                raise ValueError(f"Hugging Face 回傳 HTTP {error.code}。") from error
        except (OSError, HTTPException) as error:
            if attempt == 2:
                raise ValueError("無法連線到 Hugging Face，請檢查網路後再試。") from error
            time.sleep(0.3 * (attempt + 1))
    if len(content) > METADATA_LIMIT:
        raise ValueError("Hugging Face 回傳的清單過大。")
    try:
        return json.loads(content)
    except (ValueError, UnicodeError) as error:
        raise ValueError("Hugging Face 回傳的資料格式無法讀取。") from error


def search_models(query):
    parameters = {"filter": "gguf", "sort": "downloads", "direction": -1, "limit": 40}
    if query:
        parameters["search"] = query
    results = read_metadata("/api/models?" + urlencode(parameters))
    if not isinstance(results, list):
        raise ValueError("Hugging Face 回傳的搜尋結果格式不符。")
    return [
        (entry["id"], entry.get("downloads"))
        for entry in results
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        and REPO_ID.fullmatch(entry["id"])
    ]


def model_files(repo):
    if not REPO_ID.fullmatch(repo):
        raise ValueError("模型倉庫名稱格式不符。")
    repo_path = quote(repo, safe="/")
    info = read_metadata(f"/api/models/{repo_path}?blobs=true")
    if not isinstance(info, dict):
        raise ValueError("Hugging Face 回傳的倉庫資料格式不符。")
    if info.get("gated") or info.get("private"):
        raise ValueError("此模型需要登入或申請存取權。")
    revision, siblings = info.get("sha"), info.get("siblings")
    if not isinstance(revision, str) or not REVISION.fullmatch(revision) or not isinstance(siblings, list):
        raise ValueError("Hugging Face 未提供可辨識的版本或檔案清單。")
    files = []
    for entry in siblings:
        filename = entry.get("rfilename") if isinstance(entry, dict) else None
        if not isinstance(filename, str) or not filename.lower().endswith(".gguf"):
            continue
        if any(part in ("", ".", "..") for part in filename.split("/")) or "\\" in filename:
            continue
        if re.search(r"(^|[._-])mmproj", PurePosixPath(filename).name, re.IGNORECASE):
            continue
        url = download_url(repo, revision, filename)
        try:
            model_filename(url)
        except ValueError:
            continue
        size = entry.get("size")
        files.append((filename, size if type(size) is int and size > 0 else None, url))
    return sorted(files, key=lambda item: item[0].casefold())
