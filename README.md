# City Timeline

An interactive horizontal slider that scrubs through history. At each stop,
see the world's largest cities at that moment: population, a size-scaled
bar, a short blurb, and (source permitting) a note on confidence.

No backend — static site, data precomputed at build time from historical
sources (see below), read as static JSON at runtime.

Full spec: [`docs/SPEC.md`](docs/SPEC.md). Read it before opening a PR —
it covers data sourcing (and its caveats), phased scope, and explicit
non-goals so we don't scope-creep into a general dashboard.

## Status

**Data pipeline done; UI being redesigned.** `public/data/` is generated from
real sources by `pipeline/`, not written by hand:

- **1360 BC to 1925:** Chandler (1987), as digitized by Reba et al. (2016). A
  genuine top 5 for 24 benchmark years, with documented corrections.
- **1950 to 2025:** UN World Urbanization Prospects 2018 (urban agglomerations),
  plus the UN's 2025 Degree-of-Urbanisation ranking as an alternative from 1980.
- **Per city:** era-appropriate names (Edo, Chang'an, Constantinople…),
  region, coordinates, Wikipedia summary pinned to a revision, licensed
  images with attribution, and full population history across all sources.
- **Per city per year:** sourced blurb, polity, and period image
  (`data/curated/blurbs/`).

Every fact is attributable. See [`docs/SOURCES.md`](docs/SOURCES.md). Each
build writes [`data/build-report.md`](data/build-report.md) with the rankings,
corrections, automated checks, and where historians disagree.

## Getting started

```bash
npm install
npm run dev          # app
npm run data         # rebuild public/data/ from sources (needs uv; caches downloads in data/cache/)
```

## Data layout

| Path | What |
|---|---|
| `pipeline/` | Python build: fetch → rank → enrich → validate → write |
| `data/curated/` | Hand-reviewed inputs: city registry, corrections, warning reviews, blurbs |
| `data/sources.lock.json` | URL, retrieval date and SHA-256 of every raw source file |
| `data/build-report.md` | Output of the last build, for review |
| `public/data/timeline.json` | Snapshots: ranked cities, sources, notes, caveats, other historians' estimates |
| `public/data/cities.json` | Per city: names by era, region, Wikipedia, images, population series |
