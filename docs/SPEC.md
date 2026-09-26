# Spec: City Timeline

## What this is

A single-page interactive visualization. A horizontal slider scrubs through
years from antiquity to today. At each stop, show the 5 largest cities in
the world at that moment: name, population, a size-scaled visual (bar or
circle), a short blurb, and 1-2 photos.

No backend, no database, no user accounts. Static site. All data
precomputed into JSON files at build time; the deployed app just reads
JSON and renders.

## Data sourcing (do this first, before any UI work)

Two eras need two different sources — don't try to force one dataset to
cover both.

**Pre-1950 (ancient era through early 20th century):**
Source is Wikipedia's "List of largest cities throughout history"
(https://en.wikipedia.org/wiki/List_of_largest_cities_throughout_history).
It's a curated table spanning ~7000 BC to 2000 AD, citing three historians
who often disagree with each other (Tertius Chandler, George Modelski, Ian
Morris). Important: these are estimates, not censuses, and the source
material itself flags uncertainty, especially pre-1800s. Do not present
these numbers as precise. Parse this table (it's structured but has merged
cells and multi-source rows — expect to write a scraper and then hand-review
the output rather than trusting a fully automated parse). Where sources
disagree, pick one consistently (prefer Chandler, it's the most complete
series) and note the source per data point.

**1950-present:**
Source is UN World Urbanization Prospects
(https://population.un.org/wup/) — real census-based data, available as
downloadable CSV, yearly granularity, covers "urban agglomeration"
population for major cities worldwide. Use this instead of Wikipedia for
the modern era; it's a real dataset, not a wiki table.

**Per-city facts and photos (both eras):**
Wikipedia REST API, fetched per city, only for cities that actually appear
in a top-5 slot (don't bulk-fetch every city that ever existed):
- Summary/blurb: `GET https://en.wikipedia.org/api/rest_v1/page/summary/{title}`
- Images: MediaWiki API `pageimages` + `images` props, or pull from
  Wikimedia Commons for historical photos where the city's current skyline
  photo would be misleading (e.g. don't show a 2024 Rome photo for 200 AD
  Rome — either find a historical illustration/ruin photo via Commons, or
  clearly label modern photos as "modern-day site").
- Cache every API response to disk (`data/cache/`) — don't re-fetch on
  every build. Wikipedia content is CC BY-SA and images on Commons carry
  their own individual licenses; store and display attribution per image,
  don't strip it.

**Build pipeline:** a `scripts/build-data.js` (or Python) that runs
offline, produces `data/timeline.json` — one file, structure like:

```json
[
  { "year": 1900, "cities": [
      { "name": "London", "population": 6480000, "source": "UN/Chandler",
        "blurb": "...", "images": [{ "url": "...", "attribution": "..." }] }
  ]}
]
```

The deployed app never calls Wikipedia live — it just reads this file.

## Scope for v1 (don't build everything at once)

**Phase 1 (MVP):**
- ~25-30 snapshot years chosen for interesting inflection points (not
  literally every year Wikipedia has) — e.g. 1500 BC, 500 BC, 1 AD, 500,
  1000, 1300, 1500, 1600, 1700, 1750, 1800, 1850, 1875, 1900, 1925, 1950,
  1960, 1970, 1980, 1990, 2000, 2010, 2020, 2025.
- Horizontal slider (drag or click-to-jump between snapshot years).
- 5 cards per year: name, population number, a bar or circle sized
  relative to the largest city that year, one blurb sentence.
- Plain static HTML/CSS/JS or a minimal React app — no framework bloat.

**Phase 2:**
- Photos per city (from the cached Wikipedia/Commons data).
- Autoplay button — steps through years automatically ("bar chart race"
  mode) instead of manual scrub only.
- Smooth transition/animation between snapshots.

**Phase 3 (nice-to-haves, pick what's fun):**
- Pin a specific city and see its full population trajectory across all
  years, even years it's not top-5 (small line chart).
- Toggle "city proper" vs "metro/urban agglomeration" population — these
  diverge hugely for modern megacities (e.g. Tokyo) and the definition in
  use should always be visible on screen, not just in a footnote.
- Color-code cities by region/continent so shifts in global urban
  dominance (Middle East/Asia in antiquity → Europe in the industrial era
  → Asia again now) are visible at a glance.
- Overlay markers for historical events (Black Death, fall of Rome,
  Industrial Revolution) near the years they affected population.
- Visual "confidence" indicator (dotted outline, muted color) on any
  pre-1800 estimate, since the source data itself is contested there.

## Non-goals

- No user accounts, no backend API, no live scraping in production.
- Don't try to get single-year precision before ~1800 — the source data
  doesn't support it; snapshot years are fine.
- Don't over-build the charting — a slider + 5 cards is the whole product;
  resist scope creep into a general data-viz dashboard.

## Tech suggestion

Static site (Vite + vanilla JS, or Vite + React if you want component
structure), deployed anywhere static (Netlify/Vercel/GitHub Pages). Data
pipeline is a separate offline script, not part of the deployed bundle.
