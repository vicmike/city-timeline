import "@fontsource-variable/fraunces";
import "./style.css";
import { createMap } from "./map.js";
import { createScrubber } from "./scrubber.js";
import { figure, renderDetail } from "./detail.js";
import { eraOf, escapeHtml, population, thumbUrl, yearLabel } from "./format.js";

const $ = (id) => document.getElementById(id);

const [timeline, cities] = await Promise.all([
  fetch(`${import.meta.env.BASE_URL}data/timeline.json`).then((r) => r.json()),
  fetch(`${import.meta.env.BASE_URL}data/cities.json`).then((r) => r.json()),
]);
const snapshots = timeline.snapshots;
const regions = timeline.regions;
const state = { index: snapshots.length - 1, definition: "wup2018" };

// ---------------------------------------------------------------- theme
const themeBtn = $("theme-btn");
function applyTheme(t) {
  if (t) document.documentElement.dataset.theme = t;
  const dark = t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  themeBtn.textContent = dark ? "☀" : "☾";
}
let savedTheme = null;
try { savedTheme = localStorage.getItem("theme"); } catch {}
applyTheme(savedTheme);
themeBtn.addEventListener("click", () => {
  const dark = document.documentElement.dataset.theme
    ? document.documentElement.dataset.theme === "dark"
    : matchMedia("(prefers-color-scheme: dark)").matches;
  const next = dark ? "light" : "dark";
  applyTheme(next);
  try { localStorage.setItem("theme", next); } catch {}
});

// ---------------------------------------------------------------- layout
$("context").innerHTML = `
  <div class="year-block">
    <div class="era-label" id="era-label"></div>
    <div class="year" id="year"></div>
  </div>
  <div class="map" id="map"></div>
  <div class="legend regions" id="region-legend"></div>
  <div class="year-notes" id="year-notes"></div>`;

const map = createMap($("map"), { onSelect: openCity });

// ---------------------------------------------------------------- helpers
function activeEntries(snap) {
  if (state.definition === "wup2025" && snap.alternates?.wup2025) {
    return snap.alternates.wup2025.map((e) => ({ ...e, tied: false, alternate: true }));
  }
  return snap.cities;
}

function sourceKey(snap) {
  return state.definition === "wup2025" && snap.alternates?.wup2025 ? "wup2025" : snap.source;
}

function cite(sources, start = 1) {
  return (sources ?? []).map((s, i) =>
    `<a class="cite" href="${s.url}" target="_blank" rel="noopener" title="${escapeHtml(s.title)}">${start + i}</a>`).join("");
}

// ---------------------------------------------------------------- render
function render() {
  const snap = snapshots[state.index];
  const entries = activeEntries(snap);
  const src = timeline.sources[sourceKey(snap)];
  const estimate = snap.source === "chandler";

  $("era-label").textContent = eraOf(snap.year);
  $("year").textContent = yearLabel(snap.year);
  document.title = `${yearLabel(snap.year)} · City Timeline`;

  const used = new Set(entries.map((e) => cities[e.id]?.region));
  $("region-legend").innerHTML = Object.entries(regions).filter(([k]) => used.has(k))
    .map(([k, v]) => `<span><i style="--c:var(--region-${k})"></i>${v}</span>`).join("");

  // Notes, caveats, other historians.
  const others = (snap.otherEstimates ?? []).filter((o) => o.id !== snap.cities[0].id);
  $("year-notes").innerHTML = `
    ${snap.note ? `<p class="note">${escapeHtml(snap.note)} ${cite(snap.noteSources)}</p>` : ""}
    ${(snap.caveats ?? []).map((c) => `
      <p class="caveat"><span class="caveat-tag">Data caveat</span>${escapeHtml(c)}</p>`).join("")}
    ${others.length ? `
      <div class="others">
        <span class="others-tag">Other historians' #1</span>
        ${others.map((o) => `<span>${escapeHtml(o.historian)}: <b>${escapeHtml(o.name)}</b>${
          o.population ? ` ~${o.population.toLocaleString("en-US")}` : ""}</span>`).join("")}
        <a class="cite" href="https://en.wikipedia.org/wiki/List_of_largest_cities_throughout_history"
           target="_blank" rel="noopener" title="List of largest cities throughout history - Wikipedia">W</a>
      </div>` : ""}`;

  // Ranking header: source + definition, and the definition toggle when there is a choice.
  const hasAlt = Boolean(snap.alternates?.wup2025);
  $("ranking-head").innerHTML = `
    ${hasAlt ? `
      <div class="toggle" role="radiogroup" aria-label="City definition">
        <button role="radio" aria-checked="${state.definition === "wup2018"}" data-def="wup2018">Each country's definition</button>
        <button role="radio" aria-checked="${state.definition === "wup2025"}" data-def="wup2025">One global definition</button>
      </div>` : ""}
    <p class="source-line">
      <b>${escapeHtml(src.label)}</b> · ${escapeHtml(src.definition)}
      ${snap.recordedCities ? ` Ranked from ${snap.recordedCities} cities recorded for this year.` : ""}
      ${snap.tiedForNext ? ` ${snap.tiedForNext.names.length} more tie next at ~${snap.tiedForNext.population.toLocaleString("en-US")}.` : ""}
    </p>`;

  renderCards(entries, { estimate, snap });
  map.update(entries.map((e) => {
    const c = cities[e.id];
    return { id: e.id, name: e.name, rank: e.rank, population: e.population, region: c.region,
             lat: c.coordinates?.lat, lon: c.coordinates?.lon };
  }));

  history.replaceState(null, "", `#${snap.year}`);
}

function renderCards(entries, { estimate, snap }) {
  const list = $("cards");
  const max = Math.max(...entries.map((e) => e.population));

  // FLIP: remember where each city's card was so a re-ranked city slides.
  const before = new Map([...list.children].map((el) => [el.dataset.id, el.getBoundingClientRect().top]));

  list.innerHTML = entries.map((e) => {
    const c = cities[e.id];
    const today = c.name !== e.name ? `today ${escapeHtml(c.name)}, ` : "";
    const img = e.image ?? (e.alternate ? c.images?.[0] : null);
    const blurb = e.blurb ?? c.wikipedia?.description;
    const unLabel = c.unLabel?.[sourceKey(snap)];
    return `
      <li class="card" data-id="${e.id}" style="--c:var(--region-${c.region})">
        <div class="rank">${e.tied ? `<span class="eq" title="Tied">=</span>` : ""}${e.rank}</div>
        <div class="body">
          <div class="title-row">
            <button class="name" type="button" data-open="${e.id}">${escapeHtml(e.name)}</button>
            <span class="where">${today}${escapeHtml(c.country)}</span>
          </div>
          ${e.polity ? `<div class="polity"><i></i>${escapeHtml(e.polity)}</div>`
                     : `<div class="polity"><i></i>${escapeHtml(regions[c.region])}</div>`}
          <div class="measure">
            <div class="bar"><span style="width:${(e.population / max) * 100}%"></span></div>
            <div class="pop">${population(e.population, { estimate })}${
              e.correction ? `<span class="adjusted" title="${escapeHtml(e.correction)}">adjusted</span>` : ""}</div>
          </div>
          ${unLabel ? `<p class="fine">UN figure covers the ${escapeHtml(unLabel)}.</p>` : ""}
          ${blurb ? `<p class="blurb">${escapeHtml(blurb)} ${
            e.blurb ? cite(e.sources)
                    : cite([{ title: `${c.wikipedia.title} - Wikipedia`, url: c.wikipedia.permalink }])}</p>` : ""}
        </div>
        ${img ? `<button class="thumb" type="button" data-open="${e.id}" aria-label="More about ${escapeHtml(e.name)}">
            <img src="${thumbUrl(img)}" alt="" loading="lazy" onload="this.classList.add('ok')">
            <span class="kind kind-${img.kind}">${{ period: "Period", reconstruction: "Reconstruction", site: "Site today", modern: "Today" }[img.kind] ?? ""}</span>
          </button>` : ""}
      </li>`;
  }).join("");

  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  for (const el of list.children) {
    const prev = before.get(el.dataset.id);
    const now = el.getBoundingClientRect().top;
    if (prev === undefined) {
      el.animate([{ opacity: 0, transform: "translateY(8px)" }, { opacity: 1, transform: "none" }],
        { duration: 380, easing: "cubic-bezier(.2,.7,.2,1)" });
    } else if (prev !== now) {
      el.animate([{ transform: `translateY(${prev - now}px)` }, { transform: "none" }],
        { duration: 480, easing: "cubic-bezier(.2,.7,.2,1)" });
    }
  }
  list.querySelectorAll(".bar span").forEach((bar) => {
    bar.animate([{ transform: "scaleX(0.92)", opacity: 0.6 }, { transform: "none", opacity: 1 }],
      { duration: 420, easing: "ease-out" });
  });
}

function openCity(id) {
  const snap = snapshots[state.index];
  const entry = activeEntries(snap).find((e) => e.id === id);
  renderDetail($("detail"), { city: cities[id], entry, snapshot: snap, timeline, regions });
}

// ---------------------------------------------------------------- sources sheet
function openSources() {
  const d = $("sources");
  d.innerHTML = `
    <form method="dialog" class="sheet-close"><button aria-label="Close">×</button></form>
    <h2>Sources</h2>
    <p>Every number and sentence here links to where it came from. The numbered links after each
      blurb are its sources; tap an image for its artist and licence. The full list, the corrections we made
      to the raw data and the automated checks are in the project repository
      (<code>docs/SOURCES.md</code>, <code>data/build-report.md</code>).</p>
    ${Object.values(timeline.sources).map((s) => `
      <section class="source">
        <h3>${escapeHtml(s.label)}</h3>
        <p>${escapeHtml(s.citation)}</p>
        ${s.definition ? `<p class="muted">${escapeHtml(s.definition)}</p>` : ""}
        <p class="fine"><a href="${s.url}" target="_blank" rel="noopener">${escapeHtml(s.url)}</a> · ${escapeHtml(s.license)}</p>
      </section>`).join("")}
    <p class="fine">Data built ${escapeHtml(timeline.generated)}.</p>`;
  d.showModal();
}

// ---------------------------------------------------------------- events
const scrubber = createScrubber($("scrubber"), snapshots, {
  onChange(i) { state.index = i; render(); },
});

document.addEventListener("click", (e) => {
  const open = e.target.closest("[data-open]");
  if (open) openCity(open.dataset.open);
  const jump = e.target.closest("[data-year]");
  if (jump) {
    $("detail").close();
    scrubber.set(snapshots.findIndex((s) => String(s.year) === jump.dataset.year));
  }
  const def = e.target.closest("[data-def]");
  if (def) { state.definition = def.dataset.def; render(); }
});
$("sources-btn").addEventListener("click", openSources);
$("sources-btn-2").addEventListener("click", openSources);
for (const d of document.querySelectorAll("dialog")) {
  d.addEventListener("click", (e) => { if (e.target === d) d.close(); }); // backdrop click
}
$("cards").addEventListener("mouseover", (e) => map.highlight(e.target.closest(".card")?.dataset.id));
$("cards").addEventListener("mouseleave", () => map.highlight(null));
document.addEventListener("keydown", (e) => {
  if (e.target.closest("input, textarea, dialog[open], .track") || e.metaKey || e.ctrlKey) return;
  if (e.key === "ArrowRight") scrubber.set(state.index + 1);
  if (e.key === "ArrowLeft") scrubber.set(state.index - 1);
});

// Start from the URL hash (#1700), else the most recent snapshot.
const fromHash = snapshots.findIndex((s) => String(s.year) === decodeURIComponent(location.hash.slice(1)));
state.index = fromHash >= 0 ? fromHash : snapshots.length - 1;
scrubber.set(state.index, { silent: true });
render();
addEventListener("hashchange", () => {
  const i = snapshots.findIndex((s) => String(s.year) === decodeURIComponent(location.hash.slice(1)));
  if (i >= 0 && i !== state.index) scrubber.set(i);
});
