"""Paths, source URLs, and snapshot-year choices for the data pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
CURATED = ROOT / "data" / "curated"
OUT = ROOT / "public" / "data"
REPORT = ROOT / "data" / "build-report.md"
MANIFEST = ROOT / "data" / "sources.lock.json"

USER_AGENT = "CityTimelineBuild/0.2 (offline data pipeline; https://github.com/vicmike/city-timeline)"

UN_BASE = "https://population.un.org/wup/assets/Download"
SOURCES = {
    # Reba, Reitsma & Seto (2016), digitized Chandler (1987). CC BY 4.0.
    "chandler": {
        "url": "https://ndownloader.figshare.com/files/5407640",
        "path": CACHE / "historical" / "chandlerV2.csv",
    },
    # UN WUP 2018: urban agglomerations (national definitions), annual 1950-2035.
    "wup2018_zip": {
        "url": f"{UN_BASE}/Archive/WUP2018-Excel-files.zip",
        "path": CACHE / "un" / "WUP2018.zip",
        "member": "WUP2018-F22-Cities_Over_300K_Annual.xls",
    },
    # UN WUP 2025: cities by Degree of Urbanisation, 100 largest, 1975-2050.
    "wup2025_f18": {
        "url": f"{UN_BASE}/Cities/WUP2025-F18-DEGURBA-100_Largest_Cities.xlsx",
        "path": CACHE / "un" / "F18.xlsx",
    },
    # Wikipedia multi-historian city-size tables (Morris, Modelski, Chandler, de Vries, ...).
    "wiki_community_sizes": {
        "url": "https://en.wikipedia.org/w/index.php?title=Historical_urban_community_sizes&action=raw",
        "path": CACHE / "wikipedia" / "Historical_urban_community_sizes.wikitext",
    },
    # Wikipedia per-year leaders by Chandler / Morris / Modelski, for cross-checks.
    "wiki_largest": {
        "url": "https://en.wikipedia.org/w/index.php?title=List_of_largest_cities_throughout_history&action=raw",
        "path": CACHE / "wikipedia" / "List_of_largest_cities_throughout_history.wikitext",
    },
}

# Chandler benchmark years with enough digitized coverage (>=10 cities) to
# rank a genuine top 5. AD 100 is deliberately absent: only 4 cities are
# recorded that year in the digitized dataset. AD 900 is absent because the
# digitized table is missing several cities that plainly belong in its top 5
# (Kaifeng, Heian-kyo, Luoyang; see data/build-report.md gap checks).
HISTORICAL_YEARS = [
    -1360, -650, -430, -200, 361, 500, 622, 800, 1000, 1100, 1200,
    1300, 1400, 1500, 1600, 1700, 1750, 1800, 1825, 1850, 1875, 1900, 1925,
]
MIN_RECORDED_CITIES = 10

# Years Chandler has no usable table for, but where the other historians
# together give a real top 5 (see pipeline/combined.py). Ranked by the
# "all historians" median only.
COMBINED_ONLY_YEARS = [-100, 1, 100, 200, 300, 400]

# From 1950 the UN series takes over.
MODERN_YEARS = [1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020, 2025]

TOP_N = 5
# If cities tie with #5, include them too (up to this many cards) rather
# than silently dropping one; the UI marks tied ranks.
MAX_WITH_TIES = 7
