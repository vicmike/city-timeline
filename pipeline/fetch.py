"""Cached, polite HTTP fetching. Everything lands under data/cache/ and is
never re-downloaded unless the cached file is deleted."""
import hashlib
import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

from .config import CACHE, MANIFEST, SOURCES, USER_AGENT

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT
_last_request = 0.0
MIN_INTERVAL = 1.0  # seconds between live requests (Wikimedia rate limits)


def _get(url: str, **params) -> requests.Response:
    global _last_request
    for attempt in range(5):
        wait = MIN_INTERVAL - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        resp = _session.get(url, params=params or None, timeout=60)
        if resp.status_code == 429 or resp.status_code >= 500:
            time.sleep(2 ** (attempt + 1))
            continue
        resp.raise_for_status()
        return resp
    resp.raise_for_status()
    return resp


def download(key: str) -> Path:
    src = SOURCES[key]
    path: Path = src["path"]
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"  downloading {key} ...")
        path.write_bytes(_get(src["url"]).content)
    _record(key, src["url"], path)
    member = src.get("member")
    if member:
        out = path.parent / member
        if not out.exists():
            with zipfile.ZipFile(path) as zf:
                name = next(n for n in zf.namelist() if n.endswith(member))
                out.write_bytes(zf.read(name))
        return out
    return path


def _record(key: str, url: str, path: Path) -> None:
    """Pin each raw source (URL, retrieval date, checksum) in the committed
    manifest, so any published number can be traced to the exact file."""
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    entry = manifest.get(key, {})
    if entry.get("sha256") != digest:
        retrieved = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).date().isoformat()
        if entry.get("sha256"):
            print(f"  NOTE: {key} changed since last pinned ({entry['retrieved']})")
        manifest[key] = {"url": url, "retrieved": retrieved, "sha256": digest, "bytes": path.stat().st_size}
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


def cached_json(namespace: str, key: str, url: str, **params) -> dict | None:
    """GET a JSON endpoint once and cache the body (or a 404 marker) on disk."""
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in key)
    path = CACHE / namespace / f"{safe}.json"
    if path.exists():
        data = json.loads(path.read_text())
        return None if data.get("__missing__") else data
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = _get(url, **params).json()
    except requests.HTTPError as err:
        if err.response is not None and err.response.status_code == 404:
            path.write_text(json.dumps({"__missing__": True}))
            return None
        raise
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    return data
