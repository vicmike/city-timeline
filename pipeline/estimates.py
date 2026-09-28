"""Attach every historian's estimate (from Wikipedia's "Historical urban
community sizes" tables) to the registry cities, with a citation per value."""
from . import wikisizes

VIA = "Wikipedia, Historical urban community sizes"


def build(cities: dict, alias_index: dict):
    ws = wikisizes.load()
    rev = ws["revision"].get("revid")
    permalink = f"https://en.wikipedia.org/w/index.php?oldid={rev}" if rev else \
        "https://en.wikipedia.org/wiki/Historical_urban_community_sizes"

    citations: dict[str, dict] = {}

    def cite(ref: str) -> str:
        key, _, page = ref.partition("#p")
        gid, label = wikisizes.group_of(key, ws["citations"])
        cid = f"hucs:{key}{'#p' + page if page else ''}"
        if cid not in citations:
            c = ws["citations"].get(key, {})
            citations[cid] = {
                "label": label, "group": gid,
                "author": c.get("author") or None, "year": c.get("year") or None,
                "title": c.get("title") or None, "work": c.get("work") or None,
                "page": page or None,
                "url": c.get("url") or None, "archiveUrl": c.get("archiveUrl") or None,
                "via": VIA, "viaUrl": permalink,
            }
        return cid

    by_city: dict[str, list] = {}
    all_rows: list[dict] = []
    unmatched: dict[str, dict] = {}
    for r in ws["rows"]:
        cid = None
        for name in (r["link"], r["city"]):
            if name and name.lower() in alias_index:
                cid = alias_index[name.lower()]
                break
        sources = [cite(x) for x in r["refs"]]
        groups = sorted({citations[s]["group"] for s in sources}) or ["unsourced"]
        est = {"year": r["year"], "low": r["low"], "high": r["high"],
               "sources": sources, "groups": groups}
        all_rows.append({**est, "cid": cid, "link": r["link"], "city": r["city"], "location": r["location"]})
        if cid:
            by_city.setdefault(cid, []).append(est)
        elif sources:
            u = unmatched.setdefault(r["link"] or r["city"], {"name": r["city"], "location": r["location"], "max": 0, "years": set()})
            u["max"] = max(u["max"], r["high"])
            u["years"].add(r["year"])

    for ests in by_city.values():
        ests.sort(key=lambda e: (e["year"], e["low"]))
    return {
        "byCity": by_city,
        "citations": citations,
        "unmatched": unmatched,
        "revision": ws["revision"],
        "permalink": permalink,
        "rows": ws["rows"],
        "allRows": all_rows,
    }


def spread(primary: int | None, ests: list[dict]) -> dict | None:
    """Range across the primary figure and every *cited* estimate for a year."""
    vals = [v for e in ests if e["sources"] for v in (e["low"], e["high"])]
    if primary:
        vals.append(primary)
    if len(vals) < 2:
        return None
    return {"min": min(vals), "max": max(vals), "n": sum(1 for e in ests if e["sources"]) + (1 if primary else 0)}
