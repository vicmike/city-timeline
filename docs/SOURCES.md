# Sources

Every number and sentence the app shows should trace back to something on
this page. This file lists the sources. The data files carry the per-fact
links:

| What you see | Where its source is recorded |
|---|---|
| A population figure | `source` on the snapshot in `public/data/timeline.json` (a key in the table below), plus `correction` if we changed the raw value |
| A blurb or polity ("Abbasid Caliphate") | `sources` on that city entry: list of `{title, url}` |
| A year note | `noteSources` on the snapshot |
| "Other historians say…" (the year's #1) | `otherEstimates` on the snapshot, from source `wiki-largest` below |
| Other estimates for a city in a year ("Morris 800k †") | `estimates` on that city entry; each value lists citation ids, resolved in `timeline.json` → `citations` |
| A caveat | `caveats` on the snapshot; reasoning in `data/curated/reviewed.csv` |
| City description / extract | `wikipedia.permalink` in `public/data/cities.json` (exact article revision) |
| A photo | `images[]` in `public/data/cities.json`: file page, artist, licence |

The raw downloads are pinned (URL, retrieval date, SHA-256) in
[`data/sources.lock.json`](../data/sources.lock.json). Each build writes
[`data/build-report.md`](../data/build-report.md), which lists every automated
check, every correction, and where the historians disagree.

## Population data

### `chandler`: Chandler (1987), digitized by Reba, Reitsma & Seto (2016)
- **Used for:** rankings from 1360 BC to 1925, and the pre-1950 part of each city's history.
- **Original work:** Tertius Chandler, *Four Thousand Years of Urban Growth: An Historical Census*. Lewiston, NY: Edwin Mellen Press, 1987. ISBN 0-88946-207-0.
- **Digitization:** Meredith Reba, Femke Reitsma & Karen C. Seto, "Spatializing 6,000 years of global urbanization from 3700 BC to AD 2000", *Scientific Data* 3, 160034 (2016). https://doi.org/10.1038/sdata.2016.34
- **File:** `chandlerV2.csv`, figshare https://doi.org/10.6084/m9.figshare.2059494. Licence CC BY 4.0.
- **Definition:** a continuously built-up area including suburbs. These are historians' estimates, not censuses, and the uncertainty is large before about 1800.
- **Caveats:** the digitization has transcription and geocoding errors, and some cities are missing for some years. We fix only errors we can document, in [`data/curated/chandler_corrections.csv`](../data/curated/chandler_corrections.csv). Each row there gives its reason and evidence. We use only benchmark years where at least 10 cities are recorded, so AD 100 is excluded (4 cities recorded) and so is AD 900 (known gaps).

### `wup2018`: UN World Urbanization Prospects, 2018 Revision
- **Used for:** rankings from 1950 to 2025, and the post-1950 part of each city's history.
- **Citation:** United Nations, Department of Economic and Social Affairs, Population Division (2018). *World Urbanization Prospects: The 2018 Revision*, Online Edition. File 22: Annual Population of Urban Agglomerations with 300,000 Inhabitants or More in 2018, 1950–2035.
- **URL:** https://population.un.org/wup/ (Archive → WUP2018-Excel-files.zip). Licence CC BY 3.0 IGO.
- **Definition:** "urban agglomeration" as each country defines it, so definitions vary between countries. Values after 2018, including the 2020 and 2025 snapshots, are UN projections.

### `wup2025`: UN World Urbanization Prospects, 2025 Revision (Degree of Urbanisation)
- **Used for:** the alternative ranking attached to each snapshot from 1980 onward (`alternates.wup2025`).
- **Citation:** United Nations, DESA, Population Division (2025). *World Urbanization Prospects: The 2025 Revision*, Online Edition. File 18: The 100 Largest Cities Ranked by Population Size at Each Point in Time, 1975–2050.
- **URL:** https://population.un.org/wup/ (Downloads → Cities). Licence CC BY 3.0 IGO.
- **Definition:** a "city" under the Degree of Urbanisation: a contiguous area of 1 km² grid cells with at least 1,500 people/km² and at least 50,000 people in total, applied the same way in every country. It produces a very different top 5 from national definitions. In 2025, Jakarta is #1 and Tokyo #3.

## Cross-checks and other historians

### `wiki-largest`: Wikipedia, "List of largest cities throughout history"
- https://en.wikipedia.org/wiki/List_of_largest_cities_throughout_history
- Gives the single largest city per year according to three historians:
  - Ian Morris, *Social Development* (2010), http://www.ianmorris.org/docs/social-development.pdf (archived: https://web.archive.org/web/20110726164950/http://www.ianmorris.org/docs/social-development.pdf)
  - George Modelski, *World Cities: –3000 to 2000*. Washington DC: Faros2000, 2003. ISBN 0-9676230-1-4.
  - Tertius Chandler (1987), as above.
- **Used for:** (1) the `otherEstimates` shown when Morris or Modelski name a different #1 city from Chandler; (2) an automatic check that our digitized Chandler #1 matches Chandler's #1 as Wikipedia transcribes it.

### `hucs`: Wikipedia, "Historical urban community sizes"
- https://en.wikipedia.org/wiki/Historical_urban_community_sizes (the build records the exact revision used and links every value to that permalink)
- Tables giving city sizes from 3700 BC to 2000, many historians side by side, **each value with its own citation**: Morris, Modelski, Chandler (1987), Chandler & Fox (1974), de Vries (1984), the citypops dataset (etext.org), and dozens of one-off scholarly works (Wickham, Scheidel, Wilson and others).
- **Used for:**
  - Every estimate we show beside the main figure on a card ("Historians disagree: 150k–800k").
  - The extra historians' lines and points in each city's population chart.
  - Evidence for specific corrections, such as Rome in 200 BC.
  - Two automatic checks (below).
- **How it's handled:** `pipeline/wikisizes.py` parses every table. A value keeps the citation(s) attached to it in the wikitext. Ranges are split only where each end has its own citation; otherwise the range stays with all its citations together. Values Wikipedia gives with no citation are kept as "uncited" and are never plotted, used in ranges, or used in checks.
- **Caveat:** we rely on Wikipedia's transcription of these works. We have not checked each figure against the original book.

## How facts are checked

Attribution (where a number came from) is not the same as verification (whether the number is right). Before 1950 there are no censuses, so "right" means "what the historians estimate", and they often disagree. What the build does:

1. **Faithful copying:** raw files are pinned by checksum; automatic checks catch transcription spikes, geocoding duplicates, and gaps; every fix is a cited row in `chandler_corrections.csv`.
2. **Chandler against Chandler:** our ranking uses the Reba et al. digitization. Where Wikipedia also cites a Chandler figure for the same city and year, the two are compared. Mismatches are listed in the build report as transcription questions to settle against the book.
3. **Chandler against other historians:** every ranked city-year is compared with all the cited estimates for it. Where they differ by more than 2×, the card says "Historians disagree" and shows the range and each source. Rome in AD 361 is an example: Chandler 150k, Morris 800k.
4. **The #1 city** is checked against Wikipedia's list of largest cities by year (Morris, Modelski, Chandler).

## How rankings before 1950 are made

The default ranking is **All historians (median)** (`pipeline/combined.py`). For each city and year:

1. Each historian or work that gives a figure casts one vote. A figure cited jointly to several historians, such as "1,000,000 [Morris][Modelski]", counts as a vote from each of them.
2. Chandler's figures reach us three ways: the Reba et al. digitization, figures Wikipedia cites to Chandler, and the citypops dataset built on Chandler's numbers. These collapse into **one** Chandler vote, which uses the digitized value. A value Wikipedia gives with no citation never votes.
3. The city's figure is the median of its votes. Cities are ranked by that median, and ties are kept.

Every card lists the votes behind its median, each linked to its citation. A figure resting on a single source is labelled "One source only".

Why a median by default: using one method for the whole timeline stops figures jumping between sources. Chandler alone would put Rome at 150k in AD 361, while the next year with data (AD 400) has only Morris's 800k. The median also reduces the pull of any single outlier.

**Chandler (1987)** remains available through the toggle for the 23 years where he has a full table. Six years (100 BC, AD 1, 100, 200, 300 and 400) exist only in the combined ranking, because Chandler has no usable table for them.

Known limits:
- Many figures rest on one or two sources.
- Coverage varies by region. The Wikipedia tables are richest for Europe and China.
- We take Wikipedia's transcriptions on trust.

## Descriptive text and images

### `wikipedia`: English Wikipedia
- Per-city summaries come from the REST API (`/api/rest_v1/page/summary/{title}`). Each city in `cities.json` has the article URL and a permalink to the exact revision used. Text licence: CC BY-SA 4.0.
- Blurbs are our own wording, but every blurb lists the pages it was checked against in its `sources` field. Blurbs without sources fail the build.

### Wikimedia Commons images
- Each image stores its Commons file page, artist, credit line, licence name and licence URL, all read from the file's own metadata. Images with no licence metadata are dropped, never shown without attribution.
- Wikipedia's lead image for a city is usually a *modern* photo. It is tagged `kind: "modern"` so the UI can label it "modern-day" on historical snapshots. Period images chosen by hand in `data/curated/cities.json` carry their own `kind` and date range.

## Hand-curated files

| File | Contains | How it's sourced |
|---|---|---|
| `data/curated/cities.json` | Maps each source's city names to one city; Wikipedia article; region; historical names by era | Era names and dates follow each city's Wikipedia article |
| `data/curated/chandler_corrections.csv` | Documented fixes to the digitized Chandler data | A reason and evidence on every row |
| `data/curated/reviewed.csv` | A verdict on each automated warning, plus hand-researched caveats (`manual` rows) | Reasoning and sources on every row; `caveat` rows are shown to readers |
| `data/curated/blurbs/*.json` | Per-year notes, blurbs, polities | `sources` / `noteSources` required |
