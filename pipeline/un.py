"""UN World Urbanization Prospects.

- WUP 2018, File 22: annual population of urban agglomerations (each
  country's own definition), 1950-2035. Primary modern series: it is the only
  UN city series that reaches back to 1950.
- WUP 2025, File 18: 100 largest "cities" under the Degree of Urbanisation
  (a single satellite-grid-based definition applied to every country),
  1975-2050 in 5-year steps. Published as an alternate ranking because the
  two definitions produce very different top-5s (Jakarta vs Tokyo in 2025).
"""
import pandas as pd

from .fetch import download


def load_wup2018() -> pd.DataFrame:
    df = pd.read_excel(download("wup2018_zip"), header=16)
    years = [c for c in df.columns if isinstance(c, int)]
    long = df.melt(
        id_vars=["City Code", "Urban Agglomeration", "Country or area", "Latitude", "Longitude"],
        value_vars=years, var_name="year", value_name="population",
    )
    long["population"] = (long.population * 1000).round().astype("int64")
    return long.rename(columns={
        "City Code": "code", "Urban Agglomeration": "city",
        "Country or area": "country", "Latitude": "lat", "Longitude": "lon",
    })


def load_wup2025() -> pd.DataFrame:
    df = pd.read_excel(download("wup2025_f18"), "Data", header=0)
    df["population"] = (df.Population * 1000).round().astype("int64")
    return df.rename(columns={
        "City_Code": "code", "City_Name": "city", "Location": "country",
        "Year": "year", "Rank_Order": "rank",
        "PWCent_Latitude": "lat", "PWCent_Longitude": "lon",
        "Pop_plausibility": "plausibility",
    })[["code", "city", "country", "year", "rank", "population", "lat", "lon", "plausibility"]]
