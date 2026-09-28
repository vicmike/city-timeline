import { compact, escapeHtml, eraName, population, yearLabel } from "./format.js";

const SERIES = [
  { key: "chandler", label: "Chandler (1987), historians' estimate", cls: "s-chandler" },
  { key: "wup2018", label: "UN WUP 2018, national definition", cls: "s-wup2018" },
  { key: "wup2025", label: "UN WUP 2025, Degree of Urbanisation", cls: "s-wup2025" },
];

export function renderDetail(dialog, { city, entry, snapshot, timeline, regions }) {
  const year = snapshot.year;
  const img = entry?.image ?? city.images?.[0];
  const names = [...new Set(city.names.map((n) => n.name))];
  const appearances = timeline.snapshots.filter((s) => s.cities.some((c) => c.id === city.id));

  dialog.innerHTML = `
    <form method="dialog" class="sheet-close"><button aria-label="Close">×</button></form>
    <header class="detail-head">
      <span class="swatch" style="--c:var(--region-${city.region})"></span>
      <div>
        <h2>${escapeHtml(eraName(city, year))}</h2>
        <p class="muted">${names.length > 1 ? `Also ${escapeHtml(names.filter((n) => n !== eraName(city, year)).join(", "))} · ` : ""}${escapeHtml(city.country)} · ${escapeHtml(regions[city.region])}</p>
      </div>
    </header>
    ${img ? figure(img) : ""}
    <section>
      <h3>Population over time</h3>
      <div class="chart" id="traj"></div>
      <p class="fine">Log scale. Time is spaced like the timeline above, one step per snapshot, not to scale.
        Figures come from different sources with different definitions of a city; where they overlap,
        the gap shows how much the definition matters.</p>
    </section>
    <section>
      <h3>Top-five appearances</h3>
      <p class="appear">${appearances.map((s) => {
        const c = s.cities.find((x) => x.id === city.id);
        return `<button type="button" data-year="${s.year}" class="${s.year === year ? "on" : ""}">${yearLabel(s.year)} <b>#${c.rank}</b></button>`;
      }).join("")}</p>
    </section>
    ${city.wikipedia ? `
    <section>
      <h3>From Wikipedia</h3>
      <p>${escapeHtml(city.wikipedia.extract)}</p>
      <p class="fine">From <a href="${city.wikipedia.url}" target="_blank" rel="noopener">${escapeHtml(city.wikipedia.title)}</a>
        (<a href="${city.wikipedia.permalink}" target="_blank" rel="noopener">revision used</a>), CC BY-SA 4.0.</p>
    </section>` : ""}`;

  drawChart(dialog.querySelector("#traj"), city, year, timeline.snapshots.map((s) => s.year));
  if (!dialog.open) dialog.showModal();
}

export function figure(img) {
  const label = { period: "Period image", reconstruction: "Reconstruction", site: "The site today", modern: "Modern-day photo" }[img.kind] ?? "";
  return `
    <figure class="photo">
      <img src="${img.url}" alt="${escapeHtml(img.caption ?? img.description ?? "")}"
           width="${img.width}" height="${img.height}">
      <figcaption>
        ${label ? `<span class="kind kind-${img.kind}">${label}</span>` : ""}
        ${escapeHtml(img.caption ?? img.description ?? "")}
        <span class="credit">${escapeHtml(shortArtist(img.artist))} ·
          <a href="${img.page}" target="_blank" rel="noopener">${escapeHtml(img.license)}</a> · Wikimedia Commons</span>
      </figcaption>
    </figure>`;
}

/** Commons "Artist" fields are sometimes whole bios; keep the name part. */
function shortArtist(a) {
  if (!a) return "Unknown artist";
  const cut = a.length > 48 ? a.split(/\s\(|\. |;/)[0] : a;
  return cut.length > 60 ? `${cut.slice(0, 57)}…` : cut;
}

/** Piecewise-linear position over snapshot years, matching the scrubber. */
function timeScale(years) {
  return (y) => {
    if (y <= years[0]) return (y - years[0]) / (years[1] - years[0]);
    for (let i = 0; i < years.length - 1; i++) {
      if (y <= years[i + 1]) return i + (y - years[i]) / (years[i + 1] - years[i]);
    }
    const n = years.length - 1;
    return n + (y - years[n]) / (years[n] - years[n - 1]);
  };
}

function drawChart(root, city, year, snapYears) {
  const series = SERIES.filter((s) => city.series[s.key]?.length);
  const pts = series.flatMap((s) => city.series[s.key].map(([y, p]) => ({ s, y, p })));
  if (!pts.length) { root.innerHTML = `<p class="muted">No series data.</p>`; return; }

  const W = 560, H = 220, m = { t: 12, r: 14, b: 26, l: 48 };
  const x0 = Math.min(...pts.map((d) => d.y), year), x1 = Math.max(...pts.map((d) => d.y), year);
  const lo = Math.min(...pts.map((d) => d.p)), hi = Math.max(...pts.map((d) => d.p));
  const ly0 = Math.floor(Math.log10(lo)), ly1 = Math.ceil(Math.log10(hi));
  const pos = timeScale(snapYears);
  const p0 = pos(x0), p1 = pos(x1);
  const X = (y) => m.l + ((pos(y) - p0) / Math.max(1e-6, p1 - p0)) * (W - m.l - m.r);
  const Y = (p) => H - m.b - ((Math.log10(p) - ly0) / Math.max(1, ly1 - ly0)) * (H - m.t - m.b);

  const yTicks = [];
  for (let e = ly0; e <= ly1; e++) yTicks.push(10 ** e);
  const xTicks = pickTicks(snapYears.filter((y) => y >= x0 && y <= x1), X);

  root.innerHTML = `
    <div class="legend">${series.map((s) => `<span class="${s.cls}"><i></i>${s.label}</span>`).join("")}</div>
    <svg viewBox="0 0 ${W} ${H}" class="traj" role="img"
         aria-label="Population of ${escapeHtml(city.name)} over time, log scale">
      ${yTicks.map((t) => `<line class="grid" x1="${m.l}" x2="${W - m.r}" y1="${Y(t)}" y2="${Y(t)}"/>
        <text class="axis" x="${m.l - 6}" y="${Y(t) + 4}" text-anchor="end">${compact(t)}</text>`).join("")}
      ${xTicks.map((t) => `<text class="axis" x="${X(t)}" y="${H - 6}" text-anchor="middle">${yearLabel(t)}</text>`).join("")}
      <line class="now" x1="${X(year)}" x2="${X(year)}" y1="${m.t}" y2="${H - m.b}"/>
      ${series.map((s) => {
        const d = city.series[s.key];
        const line = d.map(([y, p], i) => `${i ? "L" : "M"}${X(y).toFixed(1)},${Y(p).toFixed(1)}`).join("");
        const dots = d.length < 40 ? d.map(([y, p]) => `<circle cx="${X(y)}" cy="${Y(p)}" r="3"/>`).join("") : "";
        return `<g class="${s.cls}"><path d="${line}"/>${dots}</g>`;
      }).join("")}
      <g class="hover" visibility="hidden"><line y1="${m.t}" y2="${H - m.b}"/><circle r="4.5"/></g>
      <rect class="hit" x="${m.l}" y="0" width="${W - m.l - m.r}" height="${H}"/>
    </svg>
    <div class="tip" hidden></div>`;

  const svg = root.querySelector("svg");
  const hover = svg.querySelector(".hover");
  const tip = root.querySelector(".tip");
  svg.querySelector(".hit").addEventListener("pointermove", (e) => {
    const r = svg.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const py = ((e.clientY - r.top) / r.height) * H;
    const near = pts.reduce((a, d) => {
      const dist = Math.abs(X(d.y) - px) + Math.abs(Y(d.p) - py) * 0.25;
      return dist < a.dist ? { d, dist } : a;
    }, { dist: Infinity }).d;
    hover.setAttribute("visibility", "visible");
    hover.querySelector("line").setAttribute("x1", X(near.y));
    hover.querySelector("line").setAttribute("x2", X(near.y));
    hover.querySelector("circle").setAttribute("cx", X(near.y));
    hover.querySelector("circle").setAttribute("cy", Y(near.p));
    tip.hidden = false;
    tip.innerHTML = `<b>${yearLabel(near.y)}</b> ${population(near.p, { estimate: near.s.key === "chandler" })}<br><span>${near.s.label}</span>`;
    const left = (X(near.y) / W) * r.width;
    tip.style.left = `${Math.min(Math.max(left, 70), r.width - 70)}px`;
    tip.style.top = `${(Y(near.p) / H) * r.height - 12}px`;
  });
  svg.querySelector(".hit").addEventListener("pointerleave", () => {
    hover.setAttribute("visibility", "hidden");
    tip.hidden = true;
  });
}

function pickTicks(years, X) {
  // Label snapshot years, skipping any that would crowd the previous label.
  const out = [];
  for (const y of years) {
    if (!out.length || X(y) - X(out.at(-1)) > 58) out.push(y);
  }
  return out;
}
