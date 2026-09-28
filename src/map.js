import { geoEqualEarth, geoGraticule10, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import land110 from "world-atlas/land-110m.json";

const land = feature(land110, land110.objects.land);
const graticule = geoGraticule10();
const W = 640;
const H = 360;
const MIN_SPAN = 38; // degrees; keeps a lone cluster from zooming in absurdly

/**
 * A small locator map that re-frames itself around the current top cities,
 * so the eye follows where urban weight sits (Mesopotamia → China → Europe →
 * the Americas → Asia again) without a legend doing the work.
 */
export function createMap(root, { onSelect }) {
  root.innerHTML = `
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Map of the largest cities">
      <defs><clipPath id="map-clip"><rect width="${W}" height="${H}" rx="10"/></clipPath></defs>
      <g clip-path="url(#map-clip)">
        <rect class="sea" width="${W}" height="${H}"/>
        <path class="graticule"/>
        <path class="land"/>
        <g class="dots"></g>
        <g class="labels"></g>
      </g>
    </svg>`;
  const svg = root.querySelector("svg");
  const landEl = svg.querySelector(".land");
  const gratEl = svg.querySelector(".graticule");
  const dotsEl = svg.querySelector(".dots");
  const labelsEl = svg.querySelector(".labels");

  const projection = geoEqualEarth();
  const path = geoPath(projection);
  let view = { lon: 30, lat: 25, span: 180 };
  let frame = null;
  let current = [];

  function target(points) {
    const lons = points.map((p) => p.lon);
    const lats = points.map((p) => p.lat);
    const v = {
      lon: (Math.max(...lons) + Math.min(...lons)) / 2,
      lat: (Math.max(...lats) + Math.min(...lats)) / 2,
      span: Math.max(MIN_SPAN, (Math.max(...lons) - Math.min(...lons)) * 1.35),
    };
    // Widen until every city (plus room for its circle and label) is inside the frame.
    const PAD_X = 70, PAD_Y = 34;
    for (let i = 0; i < 20; i++) {
      configure(v);
      const xy = points.map((p) => projection([p.lon, p.lat]));
      const fits = xy.every(([x, y]) => x > PAD_X && x < W - PAD_X && y > PAD_Y && y < H - PAD_Y);
      if (fits || v.span >= 200) break;
      v.span *= 1.12;
    }
    return v;
  }

  function configure(v) {
    // Rotate so the cluster is centred, then scale so `span` degrees fill the width.
    projection.rotate([-v.lon, 0]).center([0, v.lat]).translate([W / 2, H / 2])
      .scale((W / (v.span * Math.PI / 180)) * 0.92);
    // Never show empty space beyond the poles: slide the frame back inside the world.
    const top = projection([v.lon, 89.9])[1];
    const bottom = projection([v.lon, -89.9])[1];
    let dy = 0;
    if (top > 0) dy = -top;
    else if (bottom < H) dy = H - bottom;
    if (dy) projection.translate([W / 2, H / 2 + dy]);
  }

  function applyView(v) {
    configure(v);
    landEl.setAttribute("d", path(land));
    gratEl.setAttribute("d", path(graticule));
    draw();
  }

  function draw() {
    const max = Math.max(...current.map((c) => c.population));
    const rMax = 26;
    const placed = current
      .map((c) => {
        const [x, y] = projection([c.lon, c.lat]);
        return { ...c, x, y, r: Math.max(4, rMax * Math.sqrt(c.population / max)) };
      })
      .sort((a, b) => b.r - a.r);

    dotsEl.innerHTML = placed.map((c) => `
      <g class="dot" data-id="${c.id}" tabindex="-1">
        <circle cx="${c.x}" cy="${c.y}" r="${c.r}" style="--c:var(--region-${c.region})"/>
        <circle class="core" cx="${c.x}" cy="${c.y}" r="2.5"/>
      </g>`).join("");

    // Labels: to the right of the dot, nudged down past earlier labels they'd collide with.
    const boxes = [];
    const labels = [...placed].sort((a, b) => a.y - b.y).map((c) => {
      let lx = c.x + c.r + 6;
      let ly = c.y + 4;
      const w = 9 + c.name.length * 6.6;
      if (lx + w > W - 6) lx = c.x - c.r - 6 - w;
      for (const b of boxes) {
        if (lx < b.x + b.w && lx + w > b.x && Math.abs(ly - b.y) < 15) ly = b.y + 15;
      }
      boxes.push({ x: lx, y: ly, w });
      return `<text x="${lx}" y="${ly}" data-id="${c.id}"><tspan class="n">${c.rank}</tspan> ${c.name}</text>`;
    });
    labelsEl.innerHTML = labels.join("");
  }

  svg.addEventListener("click", (e) => {
    const id = e.target.closest("[data-id]")?.dataset.id;
    if (id) onSelect(id);
  });

  function update(cities) {
    current = cities.filter((c) => c.lat !== undefined);
    if (!current.length) return;
    const to = target(current);
    const from = { ...view };
    cancelAnimationFrame(frame);
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const t0 = performance.now();
    const dur = reduce ? 0 : 700;
    const dLon = ((to.lon - from.lon + 540) % 360) - 180; // shortest way round
    const step = (now) => {
      const t = dur ? Math.min(1, (now - t0) / dur) : 1;
      const e = t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
      view = {
        lon: from.lon + dLon * e,
        lat: from.lat + (to.lat - from.lat) * e,
        span: from.span * (to.span / from.span) ** e,
      };
      applyView(view);
      if (t < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
  }

  function highlight(id) {
    svg.querySelectorAll("[data-id]").forEach((el) => el.classList.toggle("hl", el.dataset.id === id));
  }

  return { update, highlight };
}
