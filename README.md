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

Phase 1 MVP: slider + cards render from a hand-curated `public/data/timeline.json`
(16 snapshot years, 100 AD-2025). Pre-1950 entries are single-city only —
see the TODO in `scripts/build-data.js` and per-year `note` fields in the
data for why, and what a real automated pipeline needs to do instead.
Photos (Phase 2) and the rest of Phase 3 are not started.

## Getting started

```bash
npm install
npm run dev
```
