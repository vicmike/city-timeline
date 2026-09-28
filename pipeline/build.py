"""Build public/data/timeline.json + public/data/cities.json from cached sources.

    uv run python -m pipeline            # full build (fetches anything not cached)
    uv run python -m pipeline --no-enrich  # quick check: skip Wikipedia/Commons, write only the report

Writes data/build-report.md with every validation warning, the corrections
applied, and where the historians disagree. Exits non-zero on hard errors
(e.g. a top-5 city with no registry entry).
"""
import argparse
import json
import sys
from datetime import date

from . import chandler, combined, enrich, estimates, un, validate, wikilist
from .config import (COMBINED_ONLY_YEARS, CURATED, HISTORICAL_YEARS, MAX_WITH_TIES, MIN_RECORDED_CITIES,
                     MODERN_YEARS, OUT, REPORT, TOP_N)

SOURCES = {
    "chandler": {
        "label": "Chandler (1987)",
        "citation": "Tertius Chandler, Four Thousand Years of Urban Growth: An Historical Census (1987), "
                    "as digitized by Reba, Reitsma & Seto, 'Spatializing 6,000 years of global urbanization "
                    "from 3700 BC to AD 2000', Scientific Data 3, 160034 (2016).",
        "url": "https://doi.org/10.6084/m9.figshare.2059494",
        "license": "CC BY 4.0",
        "definition": "Built-up urban area including suburbs (Chandler's definition). Pre-modern figures are "
                      "historians' estimates, not censuses.",
    },
    "wup2018": {
        "label": "UN WUP 2018",
        "citation": "United Nations, DESA, Population Division (2018). World Urbanization Prospects: "
                    "The 2018 Revision, File 22.",
        "url": "https://population.un.org/wup/",
        "license": "CC BY 3.0 IGO",
        "definition": "Urban agglomeration, as each country defines it. Values after the 2018 revision "
                      "(including 2020 and 2025) are UN projections.",
    },
    "wup2025": {
        "label": "UN WUP 2025 (Degree of Urbanisation)",
        "citation": "United Nations, DESA, Population Division (2025). World Urbanization Prospects: "
                    "The 2025 Revision, File 18.",
        "url": "https://population.un.org/wup/",
        "license": "CC BY 3.0 IGO",
        "definition": "'City' under the Degree of Urbanisation: a contiguous high-density (1,500+/km²) "
                      "area of 50,000+ people on a 1 km² grid, applied identically in every country.",
    },
    "otherHistorians": {
        "label": "Other historians' #1 (Morris, Modelski)",
        "citation": "Ian Morris, Social Development (2010); George Modelski, World Cities: -3000 to 2000 "
                    "(Faros2000, 2003). Each historian's largest city per year, as tabulated on Wikipedia's "
                    "'List of largest cities throughout history'.",
        "url": "https://en.wikipedia.org/wiki/List_of_largest_cities_throughout_history",
        "license": "CC BY-SA 4.0 (Wikipedia table)",
    },
    "hucs": {
        "label": "Other historians' estimates",
        "citation": "Per-city estimates from Morris, Modelski, Chandler, de Vries, Chandler & Fox and other "
                    "scholars, as tabulated (each value with its own citation) in Wikipedia's 'Historical urban "
                    "community sizes'. We rely on Wikipedia's transcription; values it gives without a citation "
                    "are shown as uncited and never used for ranking.",
        "url": "https://en.wikipedia.org/wiki/Historical_urban_community_sizes",
        "license": "CC BY-SA 4.0 (Wikipedia table); figures belong to the cited works",
    },
    "combined": {
        "label": "All historians (median)",
        "citation": "For each city, the median of every cited historian's estimate for that year: Chandler (1987) "
                    "counted once, plus Morris, Modelski, de Vries, Chandler & Fox and other scholars as cited in "
                    "Wikipedia's 'Historical urban community sizes'. Each card lists the figures behind its median.",
        "url": "https://en.wikipedia.org/wiki/Historical_urban_community_sizes",
        "license": "Figures belong to the cited works",
        "definition": "Median of the cited historians' estimates. Historians define a city differently and often "
                      "disagree by 2x or more; a figure resting on one source is marked as such.",
    },
    "wikipedia": {
        "label": "Wikipedia",
        "citation": "English Wikipedia article summaries; images from Wikimedia Commons (individual "
                    "licences listed per image).",
        "url": "https://en.wikipedia.org/",
        "license": "CC BY-SA 4.0 (text); per-image",
    },
}


def year_label(year: int) -> str:
    if year < 0:
        return f"{-year} BC"
    return f"AD {year}" if year < 1000 else str(year)


def era_name(city: dict, year: int) -> str:
    for entry in city["names"]:
        if "to" not in entry or year <= entry["to"]:
            return entry["name"]
    return city["names"][-1]["name"]


def rank_with_ties(rows: list[tuple[str, int]]) -> tuple[list[dict], list[str]]:
    """rows sorted desc by population. Keep the top N plus anything tied with
    #N. If that tie group would push past MAX_WITH_TIES, stop before it and
    return the tied keys separately so the snapshot can say so."""
    ranks = [1 + sum(1 for _, q in rows[:i] if q > p) for i, (_, p) in enumerate(rows)]
    keep = [i for i, r in enumerate(ranks) if r <= TOP_N]
    overflow = []
    if len(keep) > MAX_WITH_TIES:
        last = ranks[keep[-1]]
        overflow = [rows[i][0] for i in keep if ranks[i] == last]
        keep = [i for i in keep if ranks[i] < last]
    counts = {}
    for i in keep:
        counts[ranks[i]] = counts.get(ranks[i], 0) + 1
    ranked = [{"key": rows[i][0], "population": int(rows[i][1]), "rank": ranks[i],
               "tied": counts[ranks[i]] > 1} for i in keep]
    return ranked, overflow


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-enrich", action="store_true")
    args = parser.parse_args()

    registry = json.loads((CURATED / "cities.json").read_text())
    cities = registry["cities"]
    # Editorial text is split into one file per era so it can be written and
    # reviewed in pieces; files are merged by snapshot year.
    blurbs = {"snapshots": {}}
    for f in sorted((CURATED / "blurbs").glob("*.json")):
        for year, entry in json.loads(f.read_text()).get("snapshots", {}).items():
            if year in blurbs["snapshots"]:
                raise SystemExit(f"{f.name}: snapshot {year} already defined in another blurbs file")
            blurbs["snapshots"][year] = entry
    by_chandler = {k: cid for cid, c in cities.items() for k in c.get("chandler", [])}
    by_wup18 = {k: cid for cid, c in cities.items() for k in c.get("wup2018", [])}
    by_wup25 = {k: cid for cid, c in cities.items() for k in c.get("wup2025", [])}

    print("loading sources ...")
    ch, corrections = chandler.load()
    w18 = un.load_wup2018()
    w25 = un.load_wup2025()
    leaders = wikilist.load()

    errors: list[str] = []
    fixes = {(c["key"], int(c["year"])): c["reason"] for c in corrections}
    by_chandler_rev = {cid: k for k, cid in by_chandler.items()}
    snapshots = []

    def resolve(mapping, key, source, year, label):
        cid = mapping.get(key)
        if cid is None:
            errors.append(f"{year_label(year)}: {source} city {label!r} (key {key!r}) has no entry in "
                          f"data/curated/cities.json")
        return cid

    alias_index = {}
    for cid, c in cities.items():
        for n in [c["wikipedia"], *[e["name"] for e in c["names"]], *c.get("aliases", [])]:
            alias_index[n.lower()] = cid

    print("parsing multi-historian estimates ...")
    est = estimates.build(cities, alias_index)

    def combined_entries(year):
        """All-historians median ranking for a year (see pipeline/combined.py)."""
        figs = combined.figures(combined.votes_for_year(year, est, ch, by_chandler), est["citations"])
        rows = sorted(figs.items(), key=lambda kv: -kv[1]["population"])
        ranked, overflow = rank_with_ties([(k, f["population"]) for k, f in rows])
        out = []
        for r in ranked:
            if r["key"].startswith("?"):
                errors.append(f"{year_label(year)}: combined ranking #{r['rank']} is {r['key'][1:]!r} "
                              f"({r['population']:,}), which has no entry in data/curated/cities.json")
                continue
            f = figs[r["key"]]
            out.append({"id": r["key"], "rank": r["rank"], "tied": r["tied"], "population": f["population"],
                        "votes": f["votes"], "n": len(f["votes"])})
        tied = None
        if overflow:
            names = [cities[k]["names"][-1]["name"] if not k.startswith("?") else k[1:] for k in overflow]
            tied = {"population": figs[overflow[0]]["population"], "names": names}
        return out, len(figs), tied

    est["citations"][combined.DIGITIZED] = combined.DIGITIZED_CITATION

    # --- historical (Chandler) -------------------------------------------------
    for year in HISTORICAL_YEARS:
        rows = ch[ch.year == year].sort_values("population", ascending=False)
        if len(rows) < MIN_RECORDED_CITIES:
            errors.append(f"{year_label(year)}: only {len(rows)} cities recorded (< {MIN_RECORDED_CITIES})")
            continue
        ranked, overflow = rank_with_ties(list(zip(rows.key, rows.population)))
        entries = []
        for r in ranked:
            cid = resolve(by_chandler, r["key"], "Chandler", year, r["key"])
            if cid:
                entries.append({"id": cid, "rank": r["rank"], "tied": r["tied"],
                                "population": r["population"]})
        snap = {"year": year, "label": year_label(year), "source": "chandler",
                "recordedCities": int(len(rows)), "cities": entries}
        if overflow:
            snap["tiedForNext"] = {
                "population": int(rows[rows.key == overflow[0]].population.iloc[0]),
                "names": [k.split("|")[0] for k in overflow],
            }
        for e in entries:
            fix = fixes.get((by_chandler_rev.get(e["id"]), year))
            if fix:
                e["correction"] = fix
        comb, n, tied = combined_entries(year)
        snap["alternates"] = {"combined": comb}
        snap["combinedCities"] = n
        if tied:
            snap["combinedTiedForNext"] = tied
        snapshots.append(snap)

    # --- years only the combined historians cover --------------------------------
    for year in COMBINED_ONLY_YEARS:
        comb, n, tied = combined_entries(year)
        snapshots.append({"year": year, "label": year_label(year), "source": "combined",
                          "combinedCities": n, "cities": comb, **({"tiedForNext": tied} if tied else {})})
    snapshots.sort(key=lambda s: s["year"])

    # --- modern (UN WUP 2018, national definitions) -----------------------------
    for year in MODERN_YEARS:
        rows = w18[w18.year == year].sort_values("population", ascending=False)
        ranked, _ = rank_with_ties(list(zip(rows.code, rows.population)))
        entries = []
        for r in ranked:
            label = rows[rows.code == r["key"]].city.iloc[0]
            cid = resolve(by_wup18, r["key"], "WUP2018", year, label)
            if cid:
                entries.append({"id": cid, "rank": r["rank"], "tied": r["tied"],
                                "population": r["population"], "sourceName": label})
        snap = {"year": year, "label": year_label(year) + (" (projection)" if year > 2018 else ""),
                "source": "wup2018", "cities": entries}
        alt = w25[(w25.year == year) & (w25["rank"] <= TOP_N)].sort_values("rank")
        if len(alt):
            snap["alternates"] = {"wup2025": [
                {"id": resolve(by_wup25, r.code, "WUP2025", year, r.city), "rank": int(r.rank),
                 "population": int(r.population), "sourceName": r.city,
                 "plausibility": r.plausibility}
                for r in alt.itertuples()
            ]}
        snapshots.append(snap)

    # --- names, blurbs, other historians' estimates --------------------------------

    for snap in snapshots:
        year = snap["year"]
        for entry in snap["cities"] + [e for alt in snap.get("alternates", {}).values() for e in alt]:
            if entry["id"]:
                entry["name"] = era_name(cities[entry["id"]], year)
        for entry in snap["cities"] + snap.get("alternates", {}).get("combined", []):
            # Every other historian's figure for this city in this year, with citations.
            others = [e for e in est["byCity"].get(entry["id"], []) if e["year"] == year]
            if others:
                entry["estimates"] = others
            sp = estimates.spread(entry["population"], others)
            if sp:
                entry["spread"] = sp
        year_blurbs = blurbs.get("snapshots", {}).get(str(year), {})
        if year_blurbs.get("note"):
            snap["note"] = year_blurbs["note"]
        for entry in snap["cities"] + snap.get("alternates", {}).get("combined", []):
            b = year_blurbs.get("cities", {}).get(entry["id"])
            if b:
                if not b.get("sources"):
                    errors.append(f"{snap['label']}: blurb for {entry['id']} has no sources")
                entry.update({k: v for k, v in b.items() if k in ("blurb", "polity", "sources")})
                if b.get("image") and not args.no_enrich:
                    spec = b["image"]
                    img = enrich.image("/" + spec["file"].removeprefix("File:"))
                    if img:
                        img.update({k: v for k, v in spec.items() if k in ("caption", "kind")})
                        entry["image"] = img
                    else:
                        errors.append(f"{snap['label']}: image {spec['file']!r} for {entry['id']} "
                                      f"not found on Commons or has no licence")
        if year_blurbs.get("note") and not year_blurbs.get("noteSources"):
            errors.append(f"{snap['label']}: note has no noteSources")
        if year_blurbs.get("noteSources"):
            snap["noteSources"] = year_blurbs["noteSources"]
        if year in leaders:
            others = []
            for historian, lead in leaders[year].items():
                if historian.startswith("Chandler"):
                    continue
                cid = alias_index.get(lead["name"].lower())
                others.append({"historian": historian, "id": cid,
                               "name": era_name(cities[cid], year) if cid else lead["name"],
                               "population": lead["population"]})
            if others:
                snap["otherEstimates"] = others

    # --- per-city population series (for trajectories) ------------------------------
    used = sorted({e["id"] for s in snapshots for e in s["cities"] if e["id"]}
                  | {e["id"] for s in snapshots for alt in s.get("alternates", {}).values() for e in alt if e["id"]})
    city_out = {}
    for cid in used:
        c = cities[cid]
        series = {}
        pts = ch[ch.key.isin(c.get("chandler", []))].groupby("year").population.sum()
        if len(pts):
            series["chandler"] = [[int(y), int(p)] for y, p in pts.items()]
        pts = w18[w18.code.isin(c.get("wup2018", [])) & (w18.year <= 2025)].groupby("year").population.sum()
        if len(pts):
            series["wup2018"] = [[int(y), int(p)] for y, p in pts.items()]
        # F18 only holds each year's top 100, so this series can have gaps.
        pts = w25[w25.code.isin(c.get("wup2025", [])) & (w25.year <= 2025)].groupby("year").population.sum()
        if len(pts):
            series["wup2025"] = [[int(y), int(p)] for y, p in pts.items()]
        if est["byCity"].get(cid):
            series["estimates"] = est["byCity"][cid]
        city_out[cid] = {
            "id": cid, "name": c["names"][-1]["name"], "country": c["country"],
            "region": c["region"], "names": c["names"], "series": series,
        }
        if "unLabel" in c:
            city_out[cid]["unLabel"] = c["unLabel"]

    if not args.no_enrich:
        print(f"enriching {len(city_out)} cities from Wikipedia/Commons (cached) ...")
        for cid, out in city_out.items():
            c = cities[cid]
            s = enrich.summary(c["wikipedia"])
            if not s:
                errors.append(f"{cid}: Wikipedia article {c['wikipedia']!r} not found")
                continue
            out["wikipedia"] = {k: s[k] for k in ("title", "url", "qid", "description", "extract", "revision")}
            if s.get("revision"):
                # Permalink to the exact article revision the text was taken from.
                out["wikipedia"]["permalink"] = (
                    f"https://en.wikipedia.org/w/index.php?oldid={s['revision']}")
            if s.get("coordinates"):
                out["coordinates"] = s["coordinates"]
            images = []
            for spec in c.get("images", []):
                img = enrich.image("/" + spec["file"].removeprefix("File:"))
                if not img:
                    errors.append(f"{cid}: curated image {spec['file']!r} not found or unlicensed")
                    continue
                img.update({k: v for k, v in spec.items() if k in ("from", "to", "caption", "kind")})
                images.append(img)
            if not c.get("skipLeadImage"):
                lead = enrich.image(s.get("image_source"))
                if lead:
                    lead.update({"kind": "modern", "caption": f"{s['title']} today (Wikipedia lead image)"})
                    images.append(lead)
            out["images"] = images

    # --- validation -----------------------------------------------------------------
    warnings = validate.run(ch, snapshots, leaders, cities, alias_index, city_out,
                            enriched=not args.no_enrich)
    warnings += validate.disagreements(snapshots, est)

    # Before 1950 the default ranking is "all historians" (one method across the
    # whole timeline); Chandler's own ranking stays available as an alternate.
    for snap in snapshots:
        if snap["source"] == "chandler":
            chandler_list = snap["cities"]
            snap["cities"] = snap["alternates"].pop("combined")
            snap["alternates"]["chandler"] = chandler_list
            snap["source"] = "combined"
            if "tiedForNext" in snap:
                snap["chandlerTiedForNext"] = snap.pop("tiedForNext")
            if "combinedTiedForNext" in snap:
                snap["tiedForNext"] = snap.pop("combinedTiedForNext")

    # Reviewed warnings marked "caveat" are shown to readers on that snapshot.
    reviews = validate.load_reviews(CURATED / "reviewed.csv")
    # "manual" rows attach a hand-researched caveat straight to a snapshot label.
    for r in reviews:
        if r["category"] == "manual" and r["verdict"] == "caveat":
            snap = next((s for s in snapshots if s["label"] == r["match"]), None)
            if not snap:
                errors.append(f"reviewed.csv: manual caveat for unknown snapshot {r['match']!r}")
            else:
                snap.setdefault("caveats", []).append(r["note"])
    for cat, msg in warnings:
        r = validate.review_for(msg, cat, reviews)
        if r and r["verdict"] == "caveat":
            label = msg.split(":", 1)[0]
            snap = next(s for s in snapshots if s["label"] == label)
            snap.setdefault("caveats", []).append(r["note"])

    OUT.mkdir(parents=True, exist_ok=True)
    timeline = {
        "generated": date.today().isoformat(),
        "sources": SOURCES,
        "regions": registry["regions"],
        "citations": est["citations"],
        "snapshots": snapshots,
    }
    if not args.no_enrich:  # a partial build must never overwrite the published data
        (OUT / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1))
        (OUT / "cities.json").write_text(json.dumps(city_out, ensure_ascii=False, indent=1))
    validate.write_report(REPORT, snapshots, cities, corrections, warnings, errors, blurbs, reviews)

    print(f"wrote {len(snapshots)} snapshots, {len(city_out)} cities; "
          f"{len(warnings)} warnings, {len(errors)} errors -> {REPORT.relative_to(REPORT.parents[1])}")
    for e in errors:
        print("ERROR:", e, file=sys.stderr)
    return 1 if errors else 0
