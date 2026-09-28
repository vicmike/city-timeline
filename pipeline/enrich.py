"""Per-city facts and images from Wikipedia / Wikimedia Commons.

Only called for cities that appear in the registry. Every response is cached
under data/cache/ so rebuilds are offline. Image licensing comes from the
Commons file page's extmetadata and is carried through to the output; images
without a usable licence are dropped rather than shown unattributed.
"""
import html
import re
from urllib.parse import quote, unquote

from .fetch import cached_json

WIKI_REST = "https://en.wikipedia.org/api/rest_v1/page/summary/"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
EN_API = "https://en.wikipedia.org/w/api.php"


def _strip_html(text: str | None) -> str | None:
    if not text:
        return None
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(html.unescape(text).split()) or None


def summary(title: str) -> dict | None:
    data = cached_json("wikipedia/summary", title, WIKI_REST + quote(title.replace(" ", "_"), safe=""))
    if not data:
        return None
    return {
        "title": data.get("title"),
        "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
        "qid": data.get("wikibase_item"),
        "description": data.get("description"),
        "extract": data.get("extract"),
        "coordinates": data.get("coordinates"),
        "image_source": (data.get("originalimage") or {}).get("source"),
        "revision": data.get("revision"),
        "retrieved": data.get("timestamp"),
    }


def _no_query(url: str | None) -> str | None:
    return url.split("?", 1)[0] if url else None


def _file_name(image_url: str) -> str:
    # .../commons/a/ab/Some_File.jpg  or  .../commons/thumb/a/ab/Some_File.jpg/800px-...
    parts = image_url.split("?", 1)[0].split("/")
    if "thumb" in parts:
        return unquote(parts[parts.index("thumb") + 3])
    return unquote(parts[-1])


def image(image_url: str | None, width: int = 960) -> dict | None:
    if not image_url:
        return None
    name = _file_name(image_url)
    params = {
        "action": "query", "format": "json", "formatversion": "2",
        "titles": f"File:{name}", "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "iiurlwidth": str(width),
    }
    # Most lead images live on Commons; a few are local to en.wikipedia.
    for ns, api in (("commons", COMMONS_API), ("enwiki", EN_API)):
        data = cached_json(f"{ns}/imageinfo", name, api, **params)
        pages = (data or {}).get("query", {}).get("pages", [])
        info = pages[0].get("imageinfo") if pages and not pages[0].get("missing") else None
        if info:
            break
    else:
        return None
    info = info[0]
    meta = {k: (v or {}).get("value") for k, v in info.get("extmetadata", {}).items()}
    license_name = _strip_html(meta.get("LicenseShortName"))
    if not license_name:
        return None
    return {
        "file": name,
        "url": _no_query(info.get("thumburl") or info.get("url")),
        "width": info.get("thumbwidth") or info.get("width"),
        "height": info.get("thumbheight") or info.get("height"),
        "original": _no_query(info.get("url")),
        "page": info.get("descriptionurl"),
        "artist": _strip_html(meta.get("Artist")),
        "credit": _strip_html(meta.get("Credit")),
        "license": license_name,
        "licenseUrl": meta.get("LicenseUrl"),
        "description": _strip_html(meta.get("ImageDescription")),
        "date": _strip_html(meta.get("DateTimeOriginal")),
    }
