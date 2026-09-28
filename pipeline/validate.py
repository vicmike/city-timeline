"""Automated sanity checks on the assembled data, and the human-readable
build report (data/build-report.md) that a reviewer reads before merging
data changes."""
import math
from pathlib import Path

import pandas as pd

SPIKE_FACTOR = 4          # value > 4x both neighbouring observations
SPIKE_WINDOW = 150        # ...when both neighbours are within this many years
GAP_WINDOW = 300          # interpolate across at most this many years each side
DUP_KM = 250              # identical values this close together look like a geocoding duplicate
DUP_TOP = 15            # only check among each year's 15 largest


def _km(lat1, lon1, lat2, lon2) -> float:
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(a))


def _label(year: int) -> str:
    return f"{-year} BC" if year < 0 else f"AD {year}" if year < 1000 else str(year)


def run(ch: pd.DataFrame, snapshots, leaders, cities, alias_index, city_out, enriched: bool):
    warnings: list[tuple[str, str]] = []  # (category, message)
    hist_years = {s["year"] for s in snapshots if s["source"] == "chandler"}

    # 1. Spikes in any Chandler series (catches dropped/extra digits).
    for key, g in ch.sort_values("year").groupby("key"):
        ys, ps = g.year.tolist(), g.population.tolist()
        for i in range(1, len(ys) - 1):
            if (ys[i] - ys[i - 1] <= SPIKE_WINDOW and ys[i + 1] - ys[i] <= SPIKE_WINDOW
                    and ps[i] > SPIKE_FACTOR * max(ps[i - 1], ps[i + 1])):
                warnings.append(("spike", f"{key} {_label(ys[i])}: {ps[i]:,.0f} vs neighbours "
                                          f"{ps[i-1]:,.0f} ({_label(ys[i-1])}) / {ps[i+1]:,.0f} ({_label(ys[i+1])})"))

    # 2. Identical values for nearby cities in the same year (geocoding duplicates).
    for year in sorted(hist_years):
        # Only pairs that could affect the displayed ranking matter.
        rows = ch[ch.year == year].nlargest(DUP_TOP, "population")
        for pop, g in rows.groupby("population"):
            recs = g.to_dict("records")
            for i in range(len(recs)):
                for j in range(i + 1, len(recs)):
                    a, b = recs[i], recs[j]
                    if (pd.notna(a["lat"]) and pd.notna(b["lat"])
                            and _km(a["lat"], a["lon"], b["lat"], b["lon"]) < DUP_KM):
                        warnings.append(("duplicate", f"{_label(year)}: {a['key']} and {b['key']} both "
                                                      f"{pop:,.0f} and < {DUP_KM} km apart"))

    # 3. Gaps: a city missing at a snapshot year whose interpolated size would rank top 5.
    for snap in snapshots:
        if snap["source"] != "chandler":
            continue
        year = snap["year"]
        cutoff = min(e["population"] for e in snap["cities"])
        present = set(ch[ch.year == year].key)
        for key, g in ch[~ch.key.isin(present)].groupby("key"):
            before = g[(g.year < year) & (g.year >= year - GAP_WINDOW)].sort_values("year").tail(1)
            after = g[(g.year > year) & (g.year <= year + GAP_WINDOW)].sort_values("year").head(1)
            if before.empty or after.empty:
                continue
            y0, p0 = before.year.iloc[0], before.population.iloc[0]
            y1, p1 = after.year.iloc[0], after.population.iloc[0]
            est = p0 + (p1 - p0) * (year - y0) / (y1 - y0)
            if est >= cutoff:
                warnings.append(("gap", f"{_label(year)}: {key} not recorded, but interpolating "
                                        f"{_label(y0)} {p0:,.0f} → {_label(y1)} {p1:,.0f} gives ~{est:,.0f}, "
                                        f"which would rank in the top {len(snap['cities'])} "
                                        f"(cut-off {cutoff:,.0f})"))

    # 4. Cross-check our Chandler #1 against Chandler's #1 as transcribed on Wikipedia.
    for snap in snapshots:
        if snap["source"] != "chandler":
            continue
        wiki = leaders.get(snap["year"], {}).get("Chandler (1987)")
        if not wiki:
            continue
        top = snap["cities"][0]
        wiki_id = alias_index.get(wiki["name"].lower())
        if wiki_id != top["id"]:
            warnings.append(("cross-check", f"{snap['label']}: digitized Chandler's #1 is {top['id']} "
                                            f"({top['population']:,}); Wikipedia's Chandler column says "
                                            f"{wiki['name']} ({wiki['population']:,})"))
        elif wiki["population"] and wiki["population"] != top["population"]:
            warnings.append(("cross-check", f"{snap['label']}: {top['id']} is #1 in both, but digitized "
                                            f"value {top['population']:,} ≠ Wikipedia's {wiki['population']:,}"))

    # 5. Enrichment coverage.
    if enriched:
        for cid, c in city_out.items():
            if not c.get("images"):
                warnings.append(("image", f"{cid}: no licensed image"))

    return warnings


def load_reviews(path: Path) -> list[dict]:
    import csv
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def review_for(message: str, category: str, reviews: list[dict]) -> dict | None:
    return next((r for r in reviews if r["category"] == category and r["match"] in message), None)


def write_report(path: Path, snapshots, cities, corrections, warnings, errors, blurbs, reviews):
    L = ["# Data build report", "",
         "Generated by `python -m pipeline`. Review this before merging data changes.", ""]
    if errors:
        L += ["## Errors (build failed)", ""] + [f"- {e}" for e in errors] + [""]

    L += ["## Snapshots", "", "| Year | Source | Recorded | Top cities |", "|---|---|---|---|"]
    for s in snapshots:
        tops = ", ".join(f"{'=' if e['tied'] else ''}{e['rank']}. {e.get('name', e['id'])} "
                         f"{e['population']/1e6:.2f}M" if e["population"] >= 1e6 else
                         f"{'=' if e['tied'] else ''}{e['rank']}. {e.get('name', e['id'])} {e['population']/1e3:.0f}k"
                         for e in s["cities"])
        L.append(f"| {s['label']} | {s['source']} | {s.get('recordedCities', '')} | {tops} |")
    L.append("")

    L += ["## Corrections applied to digitized Chandler", "",
          "From `data/curated/chandler_corrections.csv`.", ""]
    L += [f"- **{c['key']} {_label(int(c['year']))}** — {c['action']} {c['value'] or ''}: {c['reason']}"
          for c in corrections] + [""]

    cats = {"cross-check": "Cross-check vs Wikipedia's Chandler column",
            "gap": "Possible gaps in the digitized data",
            "spike": "Spikes (possible transcription errors)",
            "duplicate": "Possible geocoding duplicates",
            "image": "Images"}
    unreviewed = []
    for cat, title in cats.items():
        items = [(m, review_for(m, cat, reviews)) for c, m in warnings if c == cat]
        if items:
            L += [f"## {title} ({len(items)})", ""]
            for m, r in items:
                if r:
                    L.append(f"- {m}\n  - **Reviewed ({r['verdict']}):** {r['note']}")
                else:
                    L.append(f"- {m}\n  - **UNREVIEWED** - add a row to data/curated/reviewed.csv")
                    unreviewed.append(m)
            L.append("")
    if unreviewed:
        L[4:4] = [f"**{len(unreviewed)} unreviewed warning(s)** - see below.", ""]

    L += ["## Where historians disagree on the #1 city", ""]
    for s in snapshots:
        others = [o for o in s.get("otherEstimates", []) if o["id"] != s["cities"][0]["id"]]
        if others:
            txt = "; ".join(f"{o['historian']}: {o['name']} ({o['population']:,})" if o["population"]
                            else f"{o['historian']}: {o['name']}" for o in others)
            L.append(f"- {s['label']}: Chandler → {s['cities'][0]['name']}; {txt}")
    L.append("")

    missing = [f"{s['label']}: {e['id']}" for s in snapshots for e in s["cities"] if not e.get("blurb")]
    L += [f"## Missing blurbs ({len(missing)})", ""] + [f"- {m}" for m in missing] + [""]
    path.write_text("\n".join(L))
