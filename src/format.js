export function yearLabel(year) {
  if (year < 0) return `${-year} BC`;
  return year < 1000 ? `AD ${year}` : String(year);
}

export function eraOf(year) {
  if (year < 500) return "Antiquity";
  if (year < 1500) return "Middle Ages";
  if (year < 1800) return "Early modern";
  if (year < 1950) return "Industrial age";
  return "Modern";
}

/** Estimates get a tilde and rounding that doesn't pretend to precision. */
export function population(n, { estimate = false } = {}) {
  if (n >= 1e6) {
    const m = n / 1e6;
    return `${estimate ? "~" : ""}${m.toFixed(m >= 10 ? 1 : 2)} million`;
  }
  return `${estimate ? "~" : ""}${Math.round(n / 1000).toLocaleString("en-US")},000`;
}

export function compact(n) {
  if (n >= 1e6) return `${(n / 1e6).toFixed(n >= 1e7 ? 0 : 1)}M`;
  return `${Math.round(n / 1000)}k`;
}

export function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

export function eraName(city, year) {
  for (const entry of city.names) {
    if (entry.to === undefined || year <= entry.to) return entry.name;
  }
  return city.names.at(-1).name;
}

/** Commons thumbnails come in standard widths; cards only need a small one. */
export function thumbUrl(img, width = 330) {
  return img.url.includes("/thumb/") ? img.url.replace(/\/\d+px-([^/]+)$/, `/${width}px-$1`) : img.url;
}
