"""Parse Wikipedia's "Historical urban community sizes" tables into
per-city, per-year estimates, each tied to the citation(s) Wikipedia gives.

The page tabulates many historians side by side (Chandler, Modelski, Morris,
de Vries, Chandler & Fox, and one-off scholarly sources), so it is how we get
more than one estimate per city-year before 1950. Every value keeps its
citation(s); values Wikipedia gives with no citation are recorded as
"unsourced" and never used for anything that counts.

We rely on Wikipedia's transcription of these works; we have not checked each
figure against the original books. docs/SOURCES.md says so.
"""
import hashlib
import re

from .fetch import cached_json, download

PAGE = "Historical_urban_community_sizes"

NUM = r"\d{1,3}(?:,\d{3})+|\d+"
REF_NAMED = re.compile(r'<ref\s+name\s*=\s*"?([^"/>]+?)"?\s*/>')
REF_DEF = re.compile(r'<ref(?:\s+name\s*=\s*"?([^"/>]+?)"?)?\s*>(.*?)</ref>', re.S)
SFN = re.compile(r"\{\{sfn\|([^}]*)\}\}")


# ------------------------------------------------------------------ citations
def _template_fields(tpl: str) -> dict:
    fields = {}
    for part in re.split(r"\|(?![^\[]*\]\])", tpl.strip("{}")):
        if "=" in part:
            k, v = part.split("=", 1)
            fields[k.strip().lower()] = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", v.strip())
    return fields


def _describe(body: str) -> dict:
    f = _template_fields(body) if "{{" in body else {}
    author = f.get("last") or f.get("last1") or f.get("author") or f.get("author1") or ""
    first = f.get("first") or f.get("first1") or ""
    year = (re.search(r"\d{4}", f.get("date", "") + " " + f.get("year", "")) or [None])[0]
    title = f.get("title") or re.sub(r"<[^>]+>|\{\{[^}]*\}\}", "", body).strip()[:160]
    url = f.get("url") or ""
    return {
        "author": (f"{first} {author}".strip() if author else ""),
        "authorKey": author.split(",")[0].strip(),
        "year": year,
        "title": title,
        "work": f.get("journal") or f.get("work") or f.get("website") or f.get("publisher") or "",
        "url": url,
        "archiveUrl": f.get("archive-url") or "",
    }


def _bibliography(text: str) -> dict:
    """Full {{cite ...}} entries in the References section, keyed "Last Year"
    so {{sfn|Last|Year|p=..}} short citations can be resolved."""
    out = {}
    refs = text.split("== References ==", 1)[-1]
    for m in re.finditer(r"\{\{[Cc]ite [^{}]*(?:\{\{[^{}]*\}\}[^{}]*)*\}\}", refs):
        d = _describe(m.group(0))
        last = d["authorKey"]
        if last and d["year"]:
            out[f"{last} {d['year']}"] = d
    return out


# ------------------------------------------------------------------ cells
def _year(header: str) -> int | None:
    h = re.sub(r"<[^>]+>|\[\[|\]\]|data-sort-type=\"?number\"?\s*\|", " ", header)
    h = re.sub(r"<ref.*", "", h).replace("!", " ")
    m = re.search(r"(\d{1,4})\s*(BC|BCE)", h) or re.search(r"(BC|BCE)\s*(\d{1,4})", h)
    if m:
        n = next(g for g in m.groups() if g.isdigit())
        return -int(n)
    m = re.search(r"(?:AD|CE)?\s*(\d{1,4})\s*(?:AD|CE)?\s*$", h.strip())
    return int(m.group(1)) if m else None


def _parse_cell(raw: str, refdefs: dict, bib: dict, anon: dict) -> tuple[list[dict], bool]:
    """Return (estimates, unparsed?). An estimate is {low, high, refs}."""
    text = raw
    # Replace citations with tokens we can position against numbers.
    def named(m):
        return f" ⟦{m.group(1).strip()}⟧ "
    def inline(m):
        name, body = m.group(1), m.group(2)
        if name:
            refdefs.setdefault(name.strip(), _describe(body))
            return f" ⟦{name.strip()}⟧ "
        key = "anon:" + hashlib.sha1(body.encode()).hexdigest()[:8]
        anon[key] = _describe(body)
        return f" ⟦{key}⟧ "
    def sfn(m):
        parts = [p for p in m.group(1).split("|") if "=" not in p]
        page = next((p.split("=", 1)[1] for p in m.group(1).split("|") if p.startswith(("p=", "pp="))), "")
        authors, year = parts[:-1], parts[-1] if parts else ""
        key = f"sfn:{' & '.join(authors)} {year}"
        if key not in anon:
            base = bib.get(f"{authors[0]} {year}") if authors else None
            anon[key] = dict(base or {"author": " & ".join(authors), "authorKey": authors[0] if authors else "",
                                      "year": year, "title": "", "work": "", "url": "", "archiveUrl": ""})
            anon[key]["authorKey"] = " & ".join(authors)
        return f" ⟦{key}{'#p' + page if page else ''}⟧ "

    text = REF_DEF.sub(inline, text)
    text = REF_NAMED.sub(named, text)
    text = SFN.sub(sfn, text)
    text = re.sub(r"\{\{[^}]*\}\}|<[^>]+>|\[\[[^\]]*\]\]|'''?", " ", text)

    tokens = re.findall(rf"⟦[^⟧]+⟧|{NUM}|[–—-]|[^\s⟦\d–—-]+", text)
    if not tokens:
        return [], False
    # Walk tokens: numbers (optionally "a–b" ranges) followed by their refs.
    estimates, i, unparsed = [], 0, False
    while i < len(tokens):
        t = tokens[i]
        if re.fullmatch(NUM, t):
            low = high = int(t.replace(",", ""))
            j = i + 1
            refs = []
            while j < len(tokens) and tokens[j].startswith("⟦"):
                refs.append(tokens[j][1:-1]); j += 1
            if j + 1 < len(tokens) and re.fullmatch(r"[–—-]", tokens[j]) and re.fullmatch(NUM, tokens[j + 1]):
                other = int(tokens[j + 1].replace(",", ""))
                k = j + 2
                refs2 = []
                while k < len(tokens) and tokens[k].startswith("⟦"):
                    refs2.append(tokens[k][1:-1]); k += 1
                if refs and refs2:
                    # "94,000[A]–200,000[B]": two separately cited estimates.
                    estimates.append({"low": low, "high": low, "refs": refs})
                    estimates.append({"low": other, "high": other, "refs": refs2})
                else:
                    # "150,000–160,000[A][B]": one range, cited jointly.
                    estimates.append({"low": min(low, other), "high": max(low, other), "refs": refs or refs2})
                i = k
                continue
            estimates.append({"low": low, "high": high, "refs": refs})
            i = j
        elif t.startswith("⟦") or re.fullmatch(r"[–—-]|c\.?|ca\.?|~|<|>|\?|,|\(|\)|;|or|to|and", t, re.I):
            i += 1
        else:
            unparsed = True
            i += 1
    return [e for e in estimates if e["low"] >= 100], unparsed


# ------------------------------------------------------------------ tables
def load() -> dict:
    """Return {"revision", "rows": [{city, link, location, year, low, high, refs}],
    "citations": {refKey: {...}}, "unparsed": [..]}"""
    text = download("wiki_community_sizes").read_text()
    rev = cached_json("wikipedia/revision", PAGE, "https://en.wikipedia.org/w/api.php",
                      action="query", prop="revisions", titles=PAGE.replace("_", " "),
                      rvprop="ids|timestamp", format="json", formatversion="2")
    revision = rev["query"]["pages"][0]["revisions"][0] if rev else {}

    refdefs = {name.strip(): _describe(body) for name, body in REF_DEF.findall(text) if name}
    bib = _bibliography(text)
    anon: dict = {}
    rows, unparsed = [], []

    for table in re.findall(r"\{\|.*?\n\|\}", text, re.S):
        lines = table.split("\n")
        headers = [l for l in lines if l.startswith("!")]
        years = [_year(h) for h in headers]
        if sum(y is not None for y in years) < 2:
            continue
        # Rows are separated by "|-"; each cell is its own "|..." line.
        for block in "\n".join(lines).split("\n|-")[1:]:
            cells = [c[1:] for c in block.split("\n") if c.startswith("|") and not c.startswith(("|}", "|+"))]
            if len(cells) < 3:
                continue
            link = re.search(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]", cells[0])
            city = (link.group(2) or link.group(1)) if link else re.sub(r"<[^>]+>|'''?", "", cells[0]).strip()
            target = link.group(1).strip() if link else None
            loc_col = next((i for i, h in enumerate(headers) if re.search(r"Location|Country|Region", h)), None)
            location = (re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]|<[^>]+>", r"\1", cells[loc_col]).strip()
                        if loc_col is not None and loc_col < len(cells) else "")
            for year, cell in zip(years, cells):
                if year is None or not cell.strip():
                    continue
                ests, bad = _parse_cell(cell, refdefs, bib, anon)
                if bad and not ests:
                    unparsed.append(f"{city} {year}: {cell[:80]}")
                for e in ests:
                    rows.append({"city": city.strip(), "link": target, "location": location,
                                 "year": year, **e})

    citations = {**refdefs, **anon}
    return {"revision": revision, "rows": rows, "citations": citations, "unparsed": unparsed}


# ------------------------------------------------------------------ grouping
# Map a citation to the historian/dataset it represents, so the UI can show
# "Morris: 800,000" rather than a Wikipedia footnote name.
GROUPS = [
    ("chandler-1987", "Chandler (1987)", lambda k, c: k.lower() == "chandler" or (c.get("authorKey") == "Chandler" and c.get("year") == "1987")),
    ("chandler-fox-1974", "Chandler & Fox (1974)", lambda k, c: "Chandler & Fox" in k or (c.get("authorKey") == "Chandler" and c.get("year") == "1974")),
    ("citypops", "citypops dataset (etext.org)", lambda k, c: k.lower() == "etext" or "citypops" in c.get("url", "")),
    ("modelski", "Modelski", lambda k, c: k.lower().startswith("modelski") or c.get("authorKey") == "Modelski"),
    ("morris", "Morris", lambda k, c: k.lower() == "morris" or c.get("authorKey") == "Morris"),
    ("de-vries-1984", "de Vries (1984)", lambda k, c: "de Vries" in k or c.get("authorKey") == "de Vries"),
]


def group_of(ref: str, citations: dict) -> tuple[str, str]:
    key = ref.split("#p", 1)[0]
    c = citations.get(key, {})
    for gid, label, test in GROUPS:
        if test(key, c):
            return gid, label
    author = c.get("authorKey") or c.get("author") or ""
    if author:
        slug = re.sub(r"[^a-z0-9]+", "-", f"{author} {c.get('year') or ''}".lower()).strip("-")
        return f"other:{slug}", f"{author}{f' ({c['year']})' if c.get('year') else ''}"
    title = c.get("title") or key
    return f"other:{hashlib.sha1(title.encode()).hexdigest()[:6]}", title[:60]
