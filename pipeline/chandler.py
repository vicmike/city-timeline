"""Chandler (1987) as digitized by Reba, Reitsma & Seto (2016).

The digitized CSV is wide: one row per city, one column per year
(BC_430, AD_1000, ...). It contains transcription/geocoding errors, so every
load applies data/curated/chandler_corrections.csv, whose rows each carry a
reviewed reason.
"""
import csv

import pandas as pd

from .config import CURATED
from .fetch import download

META_COLS = ["City", "OtherName", "Country", "Latitude", "Longitude", "Certainty"]


def col_to_year(col: str) -> int:
    era, num = col.split("_")
    return -int(num) if era == "BC" else int(num)


def year_to_col(year: int) -> str:
    return f"BC_{-year}" if year < 0 else f"AD_{year}"


def source_key(city: str, country: str) -> str:
    """Chandler city names are not unique (two Syracuses), so key on both."""
    return f"{city}|{country}"


def load() -> tuple[pd.DataFrame, list[dict]]:
    """Return (long dataframe: key, city, country, year, population, lat, lon),
    and the list of corrections that were applied."""
    raw = pd.read_csv(download("chandler"), encoding="latin-1", low_memory=False)
    year_cols = [c for c in raw.columns if c not in META_COLS]
    for c in year_cols:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    for c in ("Latitude", "Longitude"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    raw = raw.copy()
    raw["key"] = [source_key(a, b) for a, b in zip(raw.City, raw.Country)]

    long = raw.melt(
        id_vars=["key", "City", "Country", "Latitude", "Longitude"],
        value_vars=year_cols, var_name="col", value_name="population",
    ).dropna(subset=["population"])
    long["year"] = long.col.map(col_to_year)
    long = long.drop(columns="col").rename(
        columns={"City": "city", "Country": "country", "Latitude": "lat", "Longitude": "lon"}
    )

    applied = []
    with open(CURATED / "chandler_corrections.csv", newline="") as fh:
        for row in csv.DictReader(fh, skipinitialspace=True):
            if not row["key"] or row["key"].startswith("#"):
                continue
            year = int(row["year"])
            mask = (long.key == row["key"]) & (long.year == year)
            if row["action"] == "drop":
                if not mask.any():
                    raise ValueError(f"correction targets missing value: {row}")
                long = long[~mask]
            elif row["action"] == "set":
                value = float(row["value"])
                if mask.any():
                    long.loc[mask, "population"] = value
                else:
                    ref = long[long.key == row["key"]].iloc[0]
                    long = pd.concat([long, pd.DataFrame([{
                        "key": row["key"], "city": ref.city, "country": ref.country,
                        "lat": ref.lat, "lon": ref.lon, "population": value, "year": year,
                    }])], ignore_index=True)
            else:
                raise ValueError(f"unknown correction action: {row}")
            applied.append(row)
    return long.reset_index(drop=True), applied
