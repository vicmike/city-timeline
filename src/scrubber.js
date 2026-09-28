import { eraOf, yearLabel } from "./format.js";

/**
 * Evenly spaced stops (one per snapshot), grouped into era bands. Snapshots
 * are deliberately not on a linear time axis: 3,400 years of antiquity would
 * otherwise crush the last two centuries into a sliver.
 */
export function createScrubber(root, snapshots, { onChange }) {
  let index = 0;
  let playing = null;

  const eras = [];
  snapshots.forEach((s, i) => {
    const era = eraOf(s.year);
    if (!eras.length || eras.at(-1).name !== era) eras.push({ name: era, start: i, end: i });
    else eras.at(-1).end = i;
  });

  // Label only the start of each era (and the ends); the thumb shows the rest.
  const majors = new Set([...eras.map((e) => e.start), snapshots.length - 1]);

  const pct = (i) => (snapshots.length === 1 ? 50 : (i / (snapshots.length - 1)) * 100);

  root.innerHTML = `
    <div class="scrubber-row">
      <button class="play" type="button" aria-label="Play through time"></button>
      <div class="track-wrap">
        <div class="eras">${eras.map((e) => `
          <div class="era" style="left:${pct(e.start)}%;width:${pct(e.end) - pct(e.start)}%">
            <span>${e.name}</span>
          </div>`).join("")}
        </div>
        <div class="track" role="slider" tabindex="0" aria-label="Year"
             aria-valuemin="0" aria-valuemax="${snapshots.length - 1}">
          <div class="rail"></div>
          <div class="fill"></div>
          ${snapshots.map((s, i) => `
            <button class="stop${majors.has(i) ? " major" : ""}" type="button" data-i="${i}" style="left:${pct(i)}%"
                    tabindex="-1" aria-label="${yearLabel(s.year)}">
              <span class="tick"></span>
              <span class="stop-label">${shortLabel(s.year)}</span>
            </button>`).join("")}
          <div class="thumb"><span class="thumb-label"></span></div>
        </div>
      </div>
    </div>`;

  const track = root.querySelector(".track");
  const thumb = root.querySelector(".thumb");
  const thumbLabel = root.querySelector(".thumb-label");
  const fill = root.querySelector(".fill");
  const playBtn = root.querySelector(".play");

  function set(i, { silent = false } = {}) {
    i = Math.max(0, Math.min(snapshots.length - 1, i));
    const changed = i !== index;
    index = i;
    thumb.style.left = `${pct(i)}%`;
    fill.style.width = `${pct(i)}%`;
    thumbLabel.textContent = yearLabel(snapshots[i].year);
    track.setAttribute("aria-valuenow", String(i));
    track.setAttribute("aria-valuetext", yearLabel(snapshots[i].year));
    root.querySelectorAll(".era").forEach((el, j) => {
      el.classList.toggle("current", i >= eras[j].start && i <= eras[j].end);
    });
    root.querySelectorAll(".stop").forEach((el, j) => {
      el.classList.toggle("past", j <= i);
      el.classList.toggle("current", j === i);
    });
    if (!silent && changed) onChange(i);
  }

  function indexAt(clientX) {
    const r = track.getBoundingClientRect();
    return Math.round(((clientX - r.left) / r.width) * (snapshots.length - 1));
  }

  track.addEventListener("pointerdown", (e) => {
    stop();
    track.setPointerCapture(e.pointerId);
    root.classList.add("dragging");
    set(indexAt(e.clientX));
    const move = (ev) => set(indexAt(ev.clientX));
    const up = () => {
      root.classList.remove("dragging");
      track.removeEventListener("pointermove", move);
      track.removeEventListener("pointerup", up);
      track.removeEventListener("pointercancel", up);
    };
    track.addEventListener("pointermove", move);
    track.addEventListener("pointerup", up);
    track.addEventListener("pointercancel", up);
  });

  track.addEventListener("keydown", (e) => {
    const step = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }[e.key];
    if (step) { stop(); set(index + step); e.preventDefault(); }
    if (e.key === "Home") { stop(); set(0); e.preventDefault(); }
    if (e.key === "End") { stop(); set(snapshots.length - 1); e.preventDefault(); }
  });

  function play() {
    if (index === snapshots.length - 1) set(0);
    root.classList.add("playing");
    playBtn.setAttribute("aria-label", "Pause");
    playing = setInterval(() => {
      if (index >= snapshots.length - 1) return stop();
      set(index + 1);
    }, 2200);
  }
  function stop() {
    clearInterval(playing);
    playing = null;
    root.classList.remove("playing");
    playBtn.setAttribute("aria-label", "Play through time");
  }
  playBtn.addEventListener("click", () => (playing ? stop() : play()));

  return { set, get index() { return index; }, stop };
}

function shortLabel(year) {
  if (year < 0) return `${-year} BC`;
  return String(year);
}
