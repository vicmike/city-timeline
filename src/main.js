const slider = document.getElementById("year-slider");
const yearDisplay = document.getElementById("year-display");
const yearNote = document.getElementById("year-note");
const cardsEl = document.getElementById("cards");
const ticksEl = document.getElementById("slider-ticks");

function formatPopulation(n) {
  return n.toLocaleString("en-US");
}

function render(snapshot) {
  yearDisplay.textContent = snapshot.label;
  yearNote.textContent = snapshot.note || "";

  const maxPop = Math.max(...snapshot.cities.map((c) => c.population));

  cardsEl.innerHTML = "";
  for (const city of snapshot.cities) {
    const pct = Math.round((city.population / maxPop) * 100);
    const card = document.createElement("article");
    card.className = "card";
    card.innerHTML = `
      <div class="card-top">
        <span class="card-name">${city.rank}. ${city.name}${city.country ? ", " + city.country : ""}</span>
        <span class="card-pop">${formatPopulation(city.population)}</span>
      </div>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
      <p class="card-blurb">${city.blurb || ""}</p>
      <div class="card-source">Source: ${city.source}${city.confidence === "low" ? " · estimate, disputed" : ""}</div>
    `;
    cardsEl.appendChild(card);
  }
}

async function init() {
  const res = await fetch("/data/timeline.json");
  const timeline = await res.json();

  slider.max = String(timeline.length - 1);
  slider.value = String(timeline.length - 1); // default to most recent

  // sparse tick labels so they don't overlap
  const tickStep = Math.ceil(timeline.length / 8);
  ticksEl.innerHTML = timeline
    .map((s, i) => (i % tickStep === 0 ? `<span>${s.label}</span>` : ""))
    .join("");

  slider.addEventListener("input", () => {
    render(timeline[Number(slider.value)]);
  });

  render(timeline[Number(slider.value)]);
}

init();
