// TODO(follow-up): this is a stub. data/timeline.json is currently hand-curated
// (see docs/SPEC.md "Data sourcing" and the git history of this file for
// provenance notes). A real build-data.js should:
//
//   1. Parse https://en.wikipedia.org/wiki/List_of_largest_cities_throughout_history
//      for pre-1950 entries. Note this page tracks only the single largest
//      city per source per year, not a top-5 ranking — getting a genuine
//      top-5 for antiquity/medieval years needs Chandler's full city-rank
//      tables (Four Thousand Years of Urban Growth), not just this page.
//   2. Pull the UN World Urbanization Prospects CSV (population.un.org/wup)
//      for 1950-present top-N urban agglomeration rankings, replacing the
//      hand-recalled approximations currently in data/timeline.json.
//   3. Fetch per-city summaries/images from the Wikipedia REST API
//      (Phase 2 — see docs/SPEC.md), caching responses under data/cache/.
//   4. Write the merged result to public/data/timeline.json in the existing shape.
//
// Until this exists, edit public/data/timeline.json directly.

throw new Error("build-data.js is not implemented yet — see comments above");
