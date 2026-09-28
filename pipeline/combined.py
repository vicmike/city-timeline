"""The "All historians" ranking: each city's figure for a year is the median of
every cited historian's estimate, one vote per historian/work.

Chandler (1987) reaches us three ways (the Reba et al. digitization, figures
Wikipedia cites to Chandler, and the citypops dataset built on Chandler's
figures), so those collapse into a single Chandler vote, preferring the
digitized value. Uncited values never vote.
"""
from collections import defaultdict
from statistics import median

CHANDLER_GROUPS = {"chandler-1987", "citypops"}
DIGITIZED = "chandler-digitized"
DIGITIZED_CITATION = {
    "label": "Chandler (1987)", "group": "chandler-1987",
    "author": "Tertius Chandler", "year": "1987",
    "title": "Four Thousand Years of Urban Growth, as digitized by Reba, Reitsma & Seto (2016)",
    "work": "Scientific Data 3, 160034", "page": None,
    "url": "https://doi.org/10.6084/m9.figshare.2059494", "archiveUrl": None,
    "via": "Reba, Reitsma & Seto (2016) dataset", "viaUrl": "https://doi.org/10.6084/m9.figshare.2059494",
}


def _mid(low: int, high: int) -> float:
    return (low * high) ** 0.5


def votes_for_year(year: int, est: dict, ch, by_chandler: dict) -> dict:
    """{cityKey: {voteGroup: {"values": [...], "sources": [...]}}}; cityKey is a
    registry id, or "?<wikipedia link>" for cities not in the registry."""
    votes: dict = defaultdict(lambda: defaultdict(lambda: {"values": [], "sources": []}))
    for r in est["allRows"]:
        if r["year"] != year or not r["sources"]:
            continue
        key = r["cid"] or f"?{r['link'] or r['city']}"
        # A figure cited jointly to several historians ("1,000,000 [Morris][Modelski]")
        # is a vote from each of them.
        for g in dict.fromkeys("chandler" if g in CHANDLER_GROUPS else g for g in r["groups"]):
            v = votes[key][g]
            v["values"].append(_mid(r["low"], r["high"]))
            v["sources"] += [s for s in r["sources"]
                             if ("chandler" if est["citations"][s]["group"] in CHANDLER_GROUPS
                                 else est["citations"][s]["group"]) == g]
    for row in ch[(ch.year == year) & (ch.population > 0)].itertuples():
        key = by_chandler.get(row.key, f"?chandler:{row.key}")
        v = votes[key]["chandler"]
        # The digitized figure is the Chandler vote; Wikipedia's copies only back it up.
        v["digitized"] = float(row.population)
        v["sources"] = [DIGITIZED] + v["sources"]
    return votes


def figures(votes: dict, citations: dict) -> dict:
    """{cityKey: {"population", "votes": [...]}} using the median across votes."""
    out = {}
    for key, groups in votes.items():
        vs = []
        for g, v in groups.items():
            value = v["digitized"] if "digitized" in v else median(v["values"])
            label = "Chandler (1987)" if g == "chandler" else " & ".join(
                dict.fromkeys(citations[s]["label"] for s in v["sources"]))
            vs.append({"group": g, "label": label, "value": int(round(value, -3) or value),
                       "sources": list(dict.fromkeys(v["sources"]))})
        vs.sort(key=lambda x: -x["value"])
        out[key] = {"population": int(round(median(x["value"] for x in vs), -3)), "votes": vs}
    return out
