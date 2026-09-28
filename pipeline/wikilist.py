"""Parse Wikipedia's "List of largest cities throughout history" table.

It only gives the single largest city per year per historian (Morris 2010,
Modelski 2003, Chandler 1987), so it is used for two things:
  1. Cross-checking the digitized Chandler dataset's #1 against Chandler's
     #1 as transcribed on Wikipedia.
  2. Surfacing where the three historians disagree about the leader.
"""
import re

from .fetch import download

HISTORIANS = ["Morris (2010)", "Modelski (2003)", "Chandler (1987)"]


def _clean(cell: str) -> str:
    cell = re.sub(r"<ref[^>]*/>", "", cell)
    cell = re.sub(r"<ref[^>]*>.*?</ref>", "", cell)
    cell = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", cell)
    cell = re.sub(r"<br\s*/?>", " ", cell)
    cell = re.sub(r"<[^>]+>", "", cell)
    cell = cell.split("|")[-1]  # drop wikitable attributes (align=..|, rowspan=..|)
    return cell.replace("'''", "").strip()


def _year(text: str) -> int | None:
    m = re.fullmatch(r"BC[- ]?(\d+)", text)
    if m:
        return -int(m.group(1))
    return int(text) if text.isdigit() else None


def _pop(text: str) -> int | None:
    m = re.search(r"\d[\d,]*", text)
    return int(m.group(0).replace(",", "")) if m else None


def load() -> dict[int, dict[str, dict]]:
    """{year: {historian: {"name", "country", "population"}}}"""
    text = download("wiki_largest").read_text()
    body = text.split('{| class="wikitable', 1)[1].split("\n|}", 1)[0]
    leaders: dict[int, dict[str, dict]] = {}
    for line in body.splitlines():
        if not line.startswith("|") or line.startswith("|-") or line.startswith("|+"):
            continue
        cells = [_clean(c) for c in line.lstrip("|").split("||")]
        if len(cells) != 10:
            continue  # continuation rows for rowspan'd ties
        year = _year(cells[0])
        if year is None:
            continue
        for i, historian in enumerate(HISTORIANS):
            pop, name, country = cells[1 + 3 * i: 4 + 3 * i]
            if name:
                leaders.setdefault(year, {})[historian] = {
                    "name": name, "country": country, "population": _pop(pop),
                }
    return leaders
