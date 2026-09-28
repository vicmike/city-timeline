# Blurbs: editorial text per snapshot

One JSON file per era. The build (`python -m pipeline`) merges them by
snapshot year, and a year may appear in only one file. Populations and
rankings come from the source data, never from these files. These files
supply only the words and pictures shown next to them.

## Format

```json
{
  "snapshots": {
    "800": {
      "note": "Optional, at most 40 words: one sentence of big-picture context for the year.",
      "noteSources": [{"title": "Abbasid Caliphate - Wikipedia", "url": "https://en.wikipedia.org/wiki/Abbasid_Caliphate#Golden_Age"}],
      "cities": {
        "baghdad": {
          "polity": "Abbasid Caliphate",
          "blurb": "One or two sentences, at most 40 words, about this city at this moment.",
          "sources": [{"title": "Baghdad - Wikipedia", "url": "https://en.wikipedia.org/wiki/Baghdad#Foundation"}],
          "image": {
            "file": "File:Some_Commons_File.jpg",
            "kind": "period",
            "caption": "Short caption saying what the image shows and when it was made."
          }
        }
      }
    }
  }
}
```

Keys under `cities` are the ids from `data/curated/cities.json`.

## Rules

- **Every factual claim must appear in a source you actually opened.** Cite
  that page in `sources`, with a `#Section` anchor where possible. English
  Wikipedia is preferred. Britannica, UNESCO, museum or university pages are
  fine. Never write from memory without a source that states the fact.
- **Be specific to the moment.** Say what was happening in that city around
  that year: who ruled it, what was being built, what had just happened. Don't
  give a generic description of the modern city.
- **No population figures in blurbs.** The card already shows the sourced
  number. Don't contradict the ranking either.
- **`polity`** is the state that controlled the city at that date, such as
  "Abbasid Caliphate", "Tokugawa shogunate (Japan)" or "United Kingdom". Use the
  name the linked Wikipedia article uses.
- **Images (optional but wanted):** a Wikimedia Commons file showing the city
  as it was around that time.
  - `kind`: `period` (made at the time or close to it: artwork, map, early
    photo), `reconstruction` (a modern model or illustration of the historical
    city), or `site` (a photo of what survives today, such as ruins or old
    buildings).
  - Never use a modern skyline for a historical year. For years from 1950 on,
    prefer a photo taken in that decade.
  - Check that the file exists and has licence metadata before using it:
    `https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=extmetadata&titles=File:NAME`
    The `LicenseShortName` field must be present. The build fails if it
    isn't.
  - The caption must say what the image shows and when it was made.
- Keep text plain: no markdown and no HTML.
- When calling Wikipedia or Commons APIs directly, identify with the User-Agent
  `CityTimelineBuild/0.2 (https://github.com/vicmike/city-timeline)`. Never put
  an email address or any other personal information in a request.
