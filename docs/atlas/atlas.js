/* Atlas économique du Bénin : logique de la page.
   Données injectées par build.py dans window.__ATLAS__ (agrégats seulement). */
"use strict";

const P = window.__ATLAS__;
const fmt = n => n.toLocaleString("fr-FR");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const isDark = () => {
  const forced = document.documentElement.getAttribute("data-theme");
  return forced ? forced === "dark" : darkQuery.matches;
};
const icon = name => `<svg class="ic" aria-hidden="true"><use href="#i-${name}"/></svg>`;
const FLAG = '<svg class="flag" viewBox="0 0 15 10" aria-hidden="true"><rect width="15" height="5" y="0" fill="#fcd116"/><rect width="15" height="5" y="5" fill="#e8112d"/><rect width="6" height="10" fill="#008751"/></svg>';

/* ---------- Échelles de couleur ---------- */
const SEQ_LIGHT = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"];
const SEQ_DARK = ["#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"];
/* Divergente pour la spécialisation : bleu = sous-représenté, gris = conforme
   à la moyenne nationale, rouge = sur-représenté. Seuils fixes, comparables
   d'un secteur à l'autre (contrairement aux quantiles du volume). */
const SPEC_CUTS = [0.33, 0.5, 0.8, 1.25, 2, 3];
const DIV_LIGHT = ["#0d366b", "#3987e5", "#9ec5f4", "#d8d7d1", "#f0a9a8", "#d03b3b", "#7f1d1d"];
const DIV_DARK = ["#9ec5f4", "#6da7ec", "#3987e5", "#4a4a47", "#c0504f", "#e05a59", "#f2a09f"];
const seqRamp = () => (isDark() ? SEQ_DARK : SEQ_LIGHT);
const divRamp = () => (isDark() ? DIV_DARK : DIV_LIGHT);

/* ---------- État ---------- */
const communes = Object.keys(P.communes);
const ranks = {};
communes.slice().sort((a, b) => P.communes[b].total - P.communes[a].total)
  .forEach((name, i) => { ranks[name] = i + 1; });
const nationalShare = {};
for (const [id, s] of Object.entries(P.sectors)) nationalShare[id] = s.total / P.total_entities;

let currentSector = "";
let metric = "vol";           // vol | hab | spec
let currentView = "map";      // map | table | sectors
let selected = null;
let pinned = null;            // commune épinglée pour comparaison
let sortState = { k: "v", dir: -1 };
let lastBins = {};

/* ---------- Métriques ---------- */
function valueOf(name) {
  const c = P.communes[name];
  const count = currentSector ? (c.sectors[currentSector] || 0) : c.total;
  if (metric === "vol") return count;
  if (metric === "hab") return c.pop ? (count / c.pop) * 1000 : 0;
  // Spécialisation : sans secteur choisi, la métrique n'a pas de sens.
  if (!currentSector || !c.total) return null;
  return (count / c.total) / nationalShare[currentSector];
}
function fmtV(v) {
  if (v === null) return "–";
  if (metric === "vol") return fmt(v);
  if (metric === "hab") return v.toLocaleString("fr-FR", { maximumFractionDigits: 1 });
  return v.toLocaleString("fr-FR", { maximumFractionDigits: 2 }) + "×";
}
const METRIC_LABEL = {
  vol: "Entreprises", hab: "Pour 1 000 hab.", spec: "Spécialisation",
};
const metricReady = () => metric !== "spec" || Boolean(currentSector);

function thresholds() {
  if (metric === "spec") return SPEC_CUTS;
  const values = communes.map(valueOf).filter(v => v > 0).sort((a, b) => a - b);
  const bins = seqRamp().length;
  if (!values.length) return [];
  return Array.from({ length: bins - 1 }, (_, i) =>
    values[Math.min(values.length - 1, Math.floor(((i + 1) / bins) * values.length))]);
}
const rampFor = () => (metric === "spec" ? divRamp() : seqRamp());
function binOf(v, cuts) {
  let bin = 0;
  while (bin < cuts.length && v >= cuts[bin]) bin += 1;
  return bin;
}

/* ---------- Ligne de statistiques du héros ---------- */
const located = P.total_entities - P.unlocated;
const TILES = [
  [P.total_entities, "entreprises"],
  [located, "localisées"],
  [communes.length, "communes"],
  [Object.keys(P.sectors).length, "secteurs"],
];
document.getElementById("tiles").innerHTML = TILES.map(([v, l]) =>
  `<span class="stat"><b class="v" data-target="${v}">0</b><span>${l}</span></span>`).join("");
function countUp(el) {
  const target = Number(el.dataset.target);
  if (reduceMotion) { el.textContent = fmt(target); return; }
  const t0 = performance.now(), dur = 1100;
  (function tick(t) {
    const p = Math.min(1, (t - t0) / dur);
    el.textContent = fmt(Math.round(target * (1 - Math.pow(1 - p, 3))));
    if (p < 1) requestAnimationFrame(tick);
  })(t0);
}
document.querySelectorAll("#tiles .v").forEach(countUp);

/* ---------- URL partageable ---------- */
function readHash() {
  const params = new URLSearchParams(location.hash.slice(1));
  const c = params.get("c");
  if (c && P.communes[c]) selected = c;
  const s = params.get("s");
  if (s && P.sectors[s]) currentSector = s;
  const mode = params.get("mode");
  if (["vol", "hab", "spec"].includes(mode)) metric = mode;
  const cmp = params.get("cmp");
  if (cmp && P.communes[cmp]) pinned = cmp;
  const v = params.get("v");
  const view = ["3d", "table", "sectors"].includes(v) ? v
    : (params.get("m") === "3d" ? "3d" : "map");  // compat anciens liens m=3d
  return { view };
}
function writeHash() {
  const params = new URLSearchParams();
  if (selected) params.set("c", selected);
  if (currentSector) params.set("s", currentSector);
  if (metric !== "vol") params.set("mode", metric);
  if (pinned) params.set("cmp", pinned);
  if (currentView !== "map") params.set("v", currentView);
  history.replaceState(null, "", params.size ? "#" + params.toString() : location.pathname);
}

/* ---------- Contrôles ---------- */
const sectorSel = document.getElementById("sectorSel");
for (const [id, s] of Object.entries(P.sectors)) {
  const opt = document.createElement("option");
  opt.value = id;
  opt.textContent = `${s.label} (${fmt(s.total)})`;
  sectorSel.appendChild(opt);
}
sectorSel.addEventListener("change", () => { currentSector = sectorSel.value; render(); writeHash(); });

const metricButtons = document.querySelectorAll(".seg [data-metric]");
metricButtons.forEach(btn => btn.addEventListener("click", () => {
  metric = btn.dataset.metric;
  metricButtons.forEach(b => b.setAttribute("aria-pressed", String(b === btn)));
  render();
  writeHash();
}));

const datalist = document.getElementById("communesList");
communes.forEach(name => {
  const opt = document.createElement("option");
  opt.value = name;
  datalist.appendChild(opt);
});
const searchBox = document.getElementById("communeSearch");
searchBox.addEventListener("change", () => {
  const name = searchBox.value.trim().toUpperCase();
  if (P.communes[name]) { runQuery(name); searchBox.value = ""; }
});
searchBox.addEventListener("keydown", event => {
  if (event.key === "Enter" && searchBox.value.trim()) {
    runQuery(searchBox.value);
  }
});
document.querySelectorAll("#examples button").forEach(btn =>
  btn.addEventListener("click", () => { searchBox.value = btn.textContent; runQuery(btn.textContent); }));

/* ---------- Recherche en langage naturel (interpréteur embarqué) ----------
   Pas de LLM : la page est statique et publique, une clé API y serait
   exposée. Un lexique mot-clé -> secteur dérivé de la table de
   classification, la liste des 77 communes et une petite grammaire
   d'intentions suffisent, et la réponse pilote directement la carte. */
const foldQ = text => text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
/* Reconnaissance des communes avec frontières de mots : sans elles,
   « azerty » contiendrait la commune ZE (constaté par le harnais). */
const communeMatchers = [];
{
  const escape = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  communes.forEach(name => {
    const folded = foldQ(name);
    const compact = folded.replace(/[-' ]/g, "");
    communeMatchers.push({ name, len: folded.length, compact: false,
      re: new RegExp(`(^|[^a-z0-9])${escape(folded)}($|[^a-z0-9])`) });
    if (compact !== folded) {
      communeMatchers.push({ name, len: compact.length, compact: true,
        re: new RegExp(`(^|[^a-z0-9])${escape(compact)}($|[^a-z0-9])`) });
    }
  });
}
const sectorLabelByFold = Object.fromEntries(
  Object.entries(P.sectors).map(([id, s]) => [foldQ(s.label), id]));

function findCommunes(query) {
  const compact = query.replace(/[-' ]/g, "");
  const found = new Map();  // nom -> longueur du match
  for (const matcher of communeMatchers) {
    if (matcher.re.test(matcher.compact ? compact : query)) {
      found.set(matcher.name, Math.max(found.get(matcher.name) || 0, matcher.len));
    }
  }
  return [...found.entries()].sort((a, b) => b[1] - a[1]).map(([name]) => name);
}
const ord = n => (n === 1 ? "1\u02b3\u1d49" : `${n}\u1d49`);
function findSector(query) {
  for (const [folded, id] of Object.entries(sectorLabelByFold)) {
    if (query.includes(folded)) return id;
  }
  const words = query.match(/[a-z]{3,}/g) || [];
  let best = null;
  for (const word of words) {
    for (const candidate of [word, word.replace(/s$/, "")]) {
      if (P.lexicon[candidate]) {
        if (!best || candidate.length > best[0].length) best = [candidate, P.lexicon[candidate]];
      }
    }
    if (!best && word.length >= 5) {
      for (const [key, id] of Object.entries(P.lexicon)) {
        if ((key.startsWith(word) || word.startsWith(key))
            && (!best || key.length > best[0].length)) best = [key, id];
      }
    }
  }
  return best && best[1];
}
const sectorRank = (sector, name) => {
  const sorted = communes.slice()
    .sort((a, b) => (P.communes[b].sectors[sector] || 0) - (P.communes[a].sectors[sector] || 0));
  return sorted.indexOf(name) + 1;
};
function specTop(sector, count) {
  return communes
    .map(name => {
      const c = P.communes[name];
      const lq = c.total >= 200 ? ((c.sectors[sector] || 0) / c.total) / nationalShare[sector] : 0;
      return [name, lq];
    })
    .sort((a, b) => b[1] - a[1]).slice(0, count);
}
const lqFmt = v => v.toLocaleString("fr-FR", { maximumFractionDigits: 1 }) + "×";

function runQuery(raw) {
  const query = foldQ(raw);
  const allCommunes = findCommunes(query);
  // Deux communes, ou une exclusion (« en dehors de X ») : au-delà de la
  // grammaire locale, l'interprète LLM prend le relais.
  const wantsExclude = /hors de|en dehors|sauf |excepte|a part /.test(query);
  if ((allCommunes.length >= 2 || wantsExclude) && !interpreting) {
    askInterpreter(raw);
    return;
  }
  const commune = allCommunes[0] || null;
  const sector = findSector(query);
  const wantsHab = /densit|1 ?000|habitant/.test(query);
  const wantsSpec = /specialis|represent|concentr/.test(query);
  const wantsTop = /le plus|plus de|quelle commune|classement|top /.test(query) || /^ou\b|\bou\b/.test(query);
  const wantsProfile = /que fait|secteurs|profil|principales? activit/.test(query);

  if ((!sector && (wantsSpec || wantsTop) && !commune)
      || (!commune && !sector && !wantsHab && !wantsProfile)) {
    if (interpreting) fallbackMessage(raw);
    else askInterpreter(raw);
    return;
  }

  showMapView();
  if (sector) { currentSector = sector; sectorSel.value = sector; }
  metric = wantsSpec && sector ? "spec" : (wantsHab ? "hab" : "vol");
  metricButtons.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.metric === metric)));
  if (commune && selected !== commune) selectCommune(commune);
  render();
  writeHash();

  const label = sector ? P.sectors[sector].label : null;
  let text;
  if (wantsSpec && sector) {
    const top = specTop(sector, 3);
    text = `<b>${label}</b> est le plus sur-représenté à ` +
      top.map(([n, v]) => `${n} (<b>${lqFmt(v)}</b> la moyenne nationale)`).join(", ") +
      `. <span class="muted">Communes d'au moins 200 entreprises ; la carte est passée
      en vue spécialisation.</span>`;
  } else if (sector && commune) {
    const count = P.communes[commune].sectors[sector] || 0;
    text = `<b>${commune}</b> compte <b>${fmt(count)}</b> entreprises « ${label} », ` +
      `${ord(sectorRank(sector, commune))} commune du pays sur ce secteur.`;
  } else if (sector && wantsTop) {
    const top = communes.slice()
      .sort((a, b) => (P.communes[b].sectors[sector] || 0) - (P.communes[a].sectors[sector] || 0))
      .slice(0, 3);
    text = `Le plus de « ${label} » : ` +
      top.map((n, i) => `${i + 1}. ${n} (<b>${fmt(P.communes[n].sectors[sector] || 0)}</b>)`).join(", ") + ".";
  } else if (sector) {
    text = `<b>${fmt(P.sectors[sector].total)}</b> entreprises « ${label} » au Bénin.
      <span class="muted">La carte montre leur répartition ; ajoutez une commune à
      votre question pour un chiffre local.</span>`;
  } else if (commune && wantsHab) {
    const c = P.communes[commune];
    text = `<b>${commune}</b> : <b>${perThousand(c)}</b> entreprises pour 1 000 habitants
      (${fmt(c.total)} entreprises, ${fmt(c.pop)} habitants en 2013).`;
  } else if (commune) {
    const c = P.communes[commune];
    const top = Object.entries(c.sectors).sort((a, b) => b[1] - a[1]).slice(0, 3);
    text = `<b>${commune}</b> : <b>${fmt(c.total)}</b> entreprises,
      ${ord(ranks[commune])} commune sur ${communes.length}. Principaux secteurs : ` +
      top.map(([id, n]) => `${P.sectors[id].label} (<b>${fmt(n)}</b>)`).join(", ") + ".";
  } else {
    text = `La carte est passée en vue « pour 1 000 habitants ».`;
  }
  showAnswer(text);
}
/* Repli LLM : quand la grammaire locale ne comprend pas, un Worker
   Cloudflare (clé côté serveur, jamais dans cette page) traduit la
   question en intention structurée ; les chiffres restent calculés ici,
   depuis les agrégats. Hors ligne ou Worker muet : message pédagogique. */
const NLQ_ENDPOINT = "https://annuaire-nlq.abiotov.workers.dev";
const AI_NOTE = '<span class="muted">question interprétée par IA (Gemini), chiffres calculés depuis les données</span>';
let interpreting = false;

function fallbackMessage(raw) {
  showAnswer(`Je n'ai pas compris « ${raw.trim()} ». <span class="muted">Essayez :
    « combien de quincailleries à Porto-Novo ? », « où l'immobilier est-il
    sur-représenté ? », « que fait-on à Natitingou ? »</span>`);
}

async function askInterpreter(raw) {
  if (!NLQ_ENDPOINT.startsWith("http")) { fallbackMessage(raw); return; }
  showAnswer('<span class="muted">analyse de la question...</span>');
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 6000);
    const response = await fetch(NLQ_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ q: raw }),
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!response.ok) throw new Error("worker " + response.status);
    executeStructured(await response.json(), raw);
  } catch {
    fallbackMessage(raw);
  }
}

function executeStructured(intent, raw) {
  const sector = P.sectors[intent.sector] ? intent.sector : null;
  const names = (intent.communes || []).filter(n => P.communes[n]);
  const label = sector ? P.sectors[sector].label : null;

  if (intent.action === "compare" && names.length === 2) {
    if (sector) { currentSector = sector; sectorSel.value = sector; }
    showMapView();
    pinned = names[0];
    if (selected !== names[1]) selectCommune(names[1]); else renderPanel();
    render();
    writeHash();
    const [a, b] = names.map(n => P.communes[n]);
    // La question portait peut-être sur un secteur précis : la réponse
    // compare ce secteur, les totaux ne viennent qu'en contexte.
    let text;
    if (sector) {
      const na = a.sectors[sector] || 0;
      const nb = b.sectors[sector] || 0;
      const lead = na === nb ? "Égalité" : (na > nb ? names[0] : names[1]) + " devant";
      text = `${lead} : <b>${names[0]}</b> compte <b>${fmt(na)}</b> entreprises
        « ${label} » contre <b>${fmt(nb)}</b> à <b>${names[1]}</b>
        <span class="muted">(totaux toutes activités : ${fmt(a.total)} et ${fmt(b.total)})</span>.
        Détail dans le panneau.`;
    } else {
      text = `<b>${names[0]}</b> (${fmt(a.total)} entreprises) face à
        <b>${names[1]}</b> (${fmt(b.total)}) : détail dans le panneau.`;
    }
    showAnswer(text + " " + AI_NOTE);
    return;
  }

  const excluded = (intent.exclure || []).filter(n => P.communes[n]);
  if (intent.action === "top" && sector) {
    currentSector = sector;
    sectorSel.value = sector;
    metric = "vol";
    metricButtons.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.metric === metric)));
    showMapView();
    if (selected) selectCommune(null);
    render();
    writeHash();
    const top = communes.filter(n => !excluded.includes(n))
      .sort((a, b) => (P.communes[b].sectors[sector] || 0) - (P.communes[a].sectors[sector] || 0))
      .slice(0, 3);
    const suffix = excluded.length ? ` (hors ${excluded.join(" et ")})` : "";
    showAnswer(`Le plus de « ${label} »${suffix} : `
      + top.map((n, i) => `${i + 1}. ${n} (<b>${fmt(P.communes[n].sectors[sector] || 0)}</b>)`).join(", ")
      + ". " + AI_NOTE);
    return;
  }

  if (!sector && !names.length) { fallbackMessage(raw); return; }
  const rebuilt = [
    intent.action === "count" ? "combien de" : "",
    intent.action === "top" ? "quelle commune a le plus de" : "",
    intent.action === "density" ? "densité" : "",
    intent.action === "spec" ? "spécialisation" : "",
    intent.action === "profile" ? "que fait-on" : "",
    label || "",
    names[0] ? "à " + names[0] : "",
  ].filter(Boolean).join(" ");
  interpreting = true;
  try {
    runQuery(rebuilt);
  } finally {
    interpreting = false;
  }
  const current = document.getElementById("answerTxt").innerHTML;
  showAnswer(current + " " + AI_NOTE);
}

const answerCard = document.getElementById("answer");
function showAnswer(html) {
  document.getElementById("answerTxt").innerHTML = html;
  answerCard.style.display = "block";
  answerCard.classList.remove("show");
  void answerCard.offsetWidth;
  answerCard.classList.add("show");
}
function hideAnswer() { answerCard.style.display = "none"; }
document.getElementById("answerClose").addEventListener("click", hideAnswer);
document.getElementById("randomBtn").addEventListener("click", () => {
  const pool = communes.filter(n => n !== selected);
  selectCommune(pool[Math.floor(Math.random() * pool.length)]);
  showMapView();
});

/* ---------- Export CSV des agrégats ---------- */
document.getElementById("csvBtn").addEventListener("click", () => {
  const lines = ["commune;population_2013;total_entreprises;secteur;entreprises"];
  for (const [name, c] of Object.entries(P.communes)) {
    for (const [id, n] of Object.entries(c.sectors)) {
      lines.push(`${name};${c.pop};${c.total};${P.sectors[id].label};${n}`);
    }
  }
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "annuaire-benin-agregats.csv";
  link.click();
  URL.revokeObjectURL(link.href);
});

/* ---------- Thème ---------- */
const themeBtn = document.getElementById("themeBtn");
const THEMES = [["auto", "Auto"], ["light", "Clair"], ["dark", "Sombre"]];
let themeIdx = Math.max(0, THEMES.findIndex(([t]) => t === (localStorage.getItem("atlas-theme") || "auto")));
function applyTheme() {
  const [mode, label] = THEMES[themeIdx];
  if (mode === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", mode);
  themeBtn.querySelector("span").textContent = label;
  localStorage.setItem("atlas-theme", mode);
  render();
}
themeBtn.addEventListener("click", () => { themeIdx = (themeIdx + 1) % THEMES.length; applyTheme(); });
darkQuery.addEventListener("change", () => { if (THEMES[themeIdx][0] === "auto") render(); });

/* ---------- Carte Leaflet ---------- */
const map = L.map("map", { scrollWheelZoom: false, zoomSnap: 0.25 });
map.fitBounds(P.country_bounds, { padding: [8, 8] });
map.on("focus click", () => map.scrollWheelZoom.enable());
map.on("blur", () => map.scrollWheelZoom.disable());
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: '© contributeurs <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);
L.control.scale({ imperial: false }).addTo(map);

const layers = {};
let geoLayer = null, geoData = null, maskLayer = null;

function maskStyle() {
  return {
    color: css("--baseline"), weight: 1, opacity: 0.6,
    fillColor: css("--page"), fillOpacity: isDark() ? 0.72 : 0.62,
    fillRule: "evenodd", interactive: false,
  };
}
function baseStyle(fillColor) {
  return {
    color: isDark() ? "#0d0d0d" : "#fcfcfb",
    weight: 1.2, fillOpacity: 0.72,
    fillColor: fillColor || "var(--zero)",
  };
}
function fillOf(name) {
  const v = valueOf(name);
  if (v === null || v === 0) return null;  // neutre
  return rampFor()[lastBins[name]];
}
function styleLayer(name) {
  const layer = layers[name];
  if (!layer) return;
  const style = baseStyle(fillOf(name));
  if (name === selected) { style.color = css("--accent"); style.weight = 3; }
  layer.setStyle(style);
  if (name === selected) layer.bringToFront();
}

fetch("communes.geojson")
  .then(r => r.json())
  .then(collection => {
    geoData = collection;
    geoLayer = L.geoJSON(collection, {
      style: feature => feature.properties.name === "__mask__" ? maskStyle() : baseStyle(0),
      onEachFeature: (feature, layer) => {
        const name = feature.properties.name;
        if (name === "__mask__") { maskLayer = layer; return; }
        layers[name] = layer;
        layer.on("mousemove", e => showTip(e.originalEvent, name));
        layer.on("mouseover", () => { if (name !== selected) layer.setStyle({ weight: 2.6 }); layer.bringToFront(); });
        layer.on("mouseout", () => { hideTip(); styleLayer(name); });
        layer.on("click", () => selectCommune(name));
      },
    }).addTo(map);
    render();
  })
  .catch(() => {
    document.getElementById("legend").innerHTML =
      '<span class="hint">couche de données indisponible (hors ligne ?), le panneau et le tableau restent utilisables</span>';
  });

/* ---------- Rendu global ---------- */
function render() {
  document.getElementById("mapTitle").textContent =
    (currentSector ? P.sectors[currentSector].label : "Toutes les entreprises")
    + (metric === "hab" ? " · pour 1 000 habitants" : metric === "spec" ? " · spécialisation" : "");
  document.getElementById("valHead").textContent = METRIC_LABEL[metric];
  renderPanel();
  renderTable();
  if (currentView === "sectors") renderMinis();
  if (!geoLayer) return;
  const cuts = thresholds();
  lastBins = {};
  for (const name of communes) {
    const v = valueOf(name);
    lastBins[name] = v === null ? -1 : binOf(v, cuts);
    styleLayer(name);
  }
  if (maskLayer) maskLayer.setStyle(maskStyle());
  renderLegend(cuts);
  if (mode3d) update3d();
}

function renderLegend(cuts) {
  const legend = document.getElementById("legend");
  if (!metricReady()) {
    legend.innerHTML = '<span class="hint">choisissez un secteur pour voir sa spécialisation par commune</span>';
    return;
  }
  const colors = rampFor();
  let items;
  if (metric === "spec") {
    const labels = ["< 0,33×", "0,33 à 0,5×", "0,5 à 0,8×",
                    "0,8 à 1,25× (≈ moyenne)", "1,25 à 2×", "2 à 3×", "> 3×"];
    items = colors.map((color, i) =>
      `<span class="item" data-bin="${i}"><span class="sw" style="background:${color}"></span><span class="t">${labels[i]}</span></span>`);
  } else {
    const bounds = [metric === "hab" ? 0.1 : 1, ...cuts];
    items = colors.map((color, i) => {
      const from = bounds[i];
      const to = i < cuts.length ? cuts[i] : null;
      const label = to === null ? `≥ ${fmtV(from)}`
        : `${fmtV(from)} à ${fmtV(to)}`;
      return `<span class="item" data-bin="${i}"><span class="sw" style="background:${color}"></span><span class="t">${label}</span></span>`;
    });
  }
  legend.innerHTML =
    `<span class="item"><span class="sw" style="background:var(--zero)"></span><span class="t">0</span></span>`
    + items.join("")
    + `<span class="hint">survoler une classe pour l'isoler</span>`;
  legend.querySelectorAll(".item[data-bin]").forEach(item => {
    const bin = Number(item.dataset.bin);
    item.addEventListener("mouseenter", () => {
      for (const name of communes) {
        if (lastBins[name] !== bin) layers[name]?.setStyle({ fillOpacity: 0.08 });
      }
    });
    item.addEventListener("mouseleave", () => { for (const name of communes) styleLayer(name); });
  });
}

/* ---------- Panneau ---------- */
function sectorBars(sectorCounts) {
  const top = Object.entries(sectorCounts).sort((a, b) => b[1] - a[1]).slice(0, 10);
  const max = top.length ? top[0][1] : 1;
  return top.map(([id, n]) => `
    <div class="bar-row">
      <span class="name${id === currentSector ? " hl" : ""}">${P.sectors[id].label}</span>
      <span class="bar-track"><span class="bar" data-w="${Math.max(2, 100 * n / max)}"></span></span>
      <span class="val">${fmt(n)}</span>
    </div>`).join("");
}
function animateBars(panel) {
  requestAnimationFrame(() => {
    panel.querySelectorAll(".bar").forEach(bar => { bar.style.width = bar.dataset.w + "%"; });
  });
}
function perThousand(c) {
  return c.pop ? ((c.total / c.pop) * 1000).toLocaleString("fr-FR", { maximumFractionDigits: 1 }) : "?";
}

function comparePanel(panel) {
  const [a, b] = [pinned, selected];
  const ca = P.communes[a], cb = P.communes[b];
  let unionTop = Object.entries(ca.sectors).concat(Object.entries(cb.sectors))
    .sort((x, y) => y[1] - x[1]).map(([id]) => id)
    .filter((id, i, arr) => arr.indexOf(id) === i).slice(0, 6);
  // Le secteur comparé passe en tête, même s'il est petit dans les deux.
  if (currentSector) {
    unionTop = [currentSector, ...unionTop.filter(id => id !== currentSector)].slice(0, 6);
  }
  const max = Math.max(...unionTop.map(id => Math.max(ca.sectors[id] || 0, cb.sectors[id] || 0)));
  const rows = unionTop.map(id => `
    <div class="bar-row">
      <span class="name${id === currentSector ? " hl" : ""}">${P.sectors[id].label}</span>
      <span class="bar-track"><span class="bar" data-w="${Math.max(1, 100 * (ca.sectors[id] || 0) / max)}"></span></span>
      <span class="val">${fmt(ca.sectors[id] || 0)}</span>
      <span class="bar-track"><span class="bar b" data-w="${Math.max(1, 100 * (cb.sectors[id] || 0) / max)}"></span></span>
      <span class="val">${fmt(cb.sectors[id] || 0)}</span>
    </div>`).join("");
  panel.innerHTML = `<h2>${icon("columns")} Comparaison</h2>
    <div class="cmp" style="margin:8px 0 4px">
      <span class="h">${a}</span><span class="h" style="color:var(--muted)">${b}</span>
      <span class="n">${fmt(ca.total)} entreprises</span><span class="n">${fmt(cb.total)} entreprises</span>
      <span class="n">${perThousand(ca)} / 1 000 hab.</span><span class="n">${perThousand(cb)} / 1 000 hab.</span>
      <span class="n">${ord(ranks[a])} sur 77</span><span class="n">${ord(ranks[b])} sur 77</span>
    </div>
    <h3>Secteurs (barre bleue : ${a})</h3>
    ${rows}
    <div class="panel-actions">
      <button id="unpinBtn">${icon("x")} Terminer la comparaison</button>
    </div>`;
  document.getElementById("unpinBtn").addEventListener("click", () => { pinned = null; renderPanel(); writeHash(); });
  animateBars(panel);
}

function renderPanel() {
  const panel = document.getElementById("panel");
  if (pinned && selected && pinned !== selected) return comparePanel(panel);
  if (selected) {
    const c = P.communes[selected];
    const quartiers = (c.quartiers || []).slice(0, 5).map(([q, n]) =>
      `<span class="chip">${q} <b>${fmt(n)}</b></span>`).join("");
    panel.innerHTML = `<h2>${icon("pin")} ${selected}</h2>
      <div class="meta">${fmt(c.total)} entreprises · ${fmt(c.pop)} habitants (2013) ·
      ${perThousand(c)} entreprises pour 1 000 habitants</div>
      <span class="badge">${ord(ranks[selected])} commune sur ${communes.length}</span>
      ${pinned === selected ? '<span class="badge">épinglée : cliquez une autre commune</span>' : ""}
      <h3>10 premiers secteurs</h3>
      ${sectorBars(c.sectors)}
      ${quartiers ? `<h3>Quartiers les plus denses</h3><div class="chips">${quartiers}</div>` : ""}
      <div class="panel-actions">
        <button id="pinBtn">${icon("columns")} ${pinned === selected ? "Désépingler" : "Comparer"}</button>
        <button id="backBtn">${icon("back")} Vue nationale</button>
      </div>`;
    document.getElementById("backBtn").addEventListener("click", () => selectCommune(null));
    document.getElementById("pinBtn").addEventListener("click", () => {
      pinned = pinned === selected ? null : selected;
      renderPanel();
      writeHash();
    });
  } else {
    const national = Object.fromEntries(Object.entries(P.sectors).map(([id, s]) => [id, s.total]));
    panel.innerHTML = `<h2>${FLAG}Bénin entier</h2>
      <div class="meta">${fmt(P.total_entities)} entreprises · 10 premiers secteurs ·
      cliquer une commune pour le détail</div>
      ${sectorBars(national)}`;
  }
  animateBars(panel);
}

function flyTo(bounds) {
  if (reduceMotion) map.fitBounds(bounds, { padding: [30, 30] });
  else map.flyToBounds(bounds, { padding: [30, 30], duration: 0.9 });
}
function selectCommune(name) {
  const previous = selected;
  selected = (name === selected) ? null : name;
  if (previous) styleLayer(previous);
  const target = selected ? P.communes[selected].bounds : P.country_bounds;
  if (selected) styleLayer(selected);
  if (mode3d && ready3d) {
    map3d.fitBounds([[target[0][1], target[0][0]], [target[1][1], target[1][0]]],
      { padding: 60, pitch: map3d.getPitch(), bearing: map3d.getBearing(),
        duration: reduceMotion ? 0 : 1200 });
  } else {
    flyTo(target);
  }
  renderPanel();
  const panel = document.getElementById("panel");
  panel.classList.remove("pulse");
  void panel.offsetWidth;
  panel.classList.add("pulse");
  writeHash();
}

/* ---------- Vue 3D (MapLibre GL vendorisé, chargé à la demande) ---------- */
let mode3d = false, map3d = null, maplibreReady = null, ready3d = false;
const btn3d = document.getElementById("btn3d");
function loadMapLibre() {
  maplibreReady = maplibreReady || new Promise((resolve, reject) => {
    const link = document.createElement("link");
    link.rel = "stylesheet"; link.href = "vendor/maplibre/maplibre-gl.css";
    document.head.appendChild(link);
    const script = document.createElement("script");
    script.src = "vendor/maplibre/maplibre-gl.js";
    script.onload = resolve; script.onerror = reject;
    document.head.appendChild(script);
  });
  return maplibreReady;
}
function props3d() {
  const colors = rampFor();
  const maxV = Math.max(...communes.map(n => valueOf(n) || 0), 1e-9);
  return {
    type: "FeatureCollection",
    features: geoData.features.map(f => {
      const name = f.properties.name;
      if (name === "__mask__") return f;
      const v = valueOf(name);
      return { ...f, properties: {
        name, v,
        h: v === null || v === 0 ? 0 : Math.sqrt(v / maxV) * 60000,
        color: v === null || v === 0 ? css("--zero") : colors[lastBins[name]],
      } };
    }),
  };
}
async function ensure3d(on) {
  mode3d = on;
  document.getElementById("map").style.display = on ? "none" : "block";
  document.getElementById("map3d").style.display = on ? "block" : "none";
  if (!on) { map.invalidateSize(); return; }
  try {
    await loadMapLibre();
    if (!map3d) init3d();
    else { map3d.resize(); update3d(); }
  } catch {
    document.getElementById("legend").innerHTML =
      '<span class="hint">vue 3D indisponible (hors ligne ?)</span>';
  }
}
function init3d() {
  map3d = new maplibregl.Map({
    container: "map3d",
    style: { version: 8, sources: {
      osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
             tileSize: 256,
             attribution: "© contributeurs <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a>" },
    }, layers: [{ id: "osm", type: "raster", source: "osm" }] },
    center: [2.34, 9.3], zoom: 6.1, pitch: 55, bearing: -12,
    attributionControl: { compact: true },
  });
  map3d.addControl(new maplibregl.NavigationControl({ visualizePitch: true }));
  map3d.on("load", () => {
    map3d.addSource("communes", { type: "geojson", data: props3d() });
    map3d.addLayer({ id: "mask3d", type: "fill", source: "communes",
      filter: ["==", ["get", "name"], "__mask__"],
      paint: { "fill-color": css("--page"), "fill-opacity": 0.62 } });
    map3d.addLayer({ id: "prismes", type: "fill-extrusion", source: "communes",
      filter: ["!=", ["get", "name"], "__mask__"],
      paint: {
        "fill-extrusion-color": ["get", "color"],
        "fill-extrusion-height": ["get", "h"],
        "fill-extrusion-base": 0,
        "fill-extrusion-opacity": 0.85,
      } });
    map3d.on("mousemove", "prismes", e => {
      map3d.getCanvas().style.cursor = "pointer";
      showTip(e.originalEvent, e.features[0].properties.name);
    });
    map3d.on("mouseleave", "prismes", () => { map3d.getCanvas().style.cursor = ""; hideTip(); });
    map3d.on("click", "prismes", e => selectCommune(e.features[0].properties.name));
    ready3d = true;
    update3d();
  });
}
function update3d() {
  if (!ready3d || !geoData) return;
  map3d.getSource("communes").setData(props3d());
  map3d.setPaintProperty("mask3d", "fill-color", css("--page"));
  map3d.setPaintProperty("osm", "raster-opacity", isDark() ? 0.35 : 1);
}

/* ---------- Panorama : 25 mini-cartes ---------- */
let miniShapes = null;  // contours normalisés dans [0,1] × [0,1], calculés une fois
function buildMiniShapes() {
  const [[minLat, minLon], [maxLat, maxLon]] = P.country_bounds;
  const cosLat = Math.cos(((minLat + maxLat) / 2) * Math.PI / 180);
  const spanX = (maxLon - minLon) * cosLat, spanY = maxLat - minLat;
  const scale = 1 / Math.max(spanX, spanY);
  miniShapes = {};
  for (const feature of geoData.features) {
    const name = feature.properties.name;
    if (name === "__mask__") continue;
    const geometry = feature.geometry;
    const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    miniShapes[name] = polygons.map(polygon => polygon.map(ring =>
      ring.map(([lon, lat]) => [
        (lon - minLon) * cosLat * scale + (1 - spanX * scale) / 2,
        (maxLat - lat) * scale + (1 - spanY * scale) / 2,
      ])));
  }
}
function valueFor(name, sector) {
  const c = P.communes[name];
  const count = sector ? (c.sectors[sector] || 0) : c.total;
  if (metric === "vol") return count;
  if (metric === "hab") return c.pop ? (count / c.pop) * 1000 : 0;
  if (!sector || !c.total) return null;
  return (count / c.total) / nationalShare[sector];
}
function drawMini(canvas, sector) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  const colors = rampFor();
  let cuts;
  if (metric === "spec") cuts = SPEC_CUTS;
  else {
    const values = communes.map(n => valueFor(n, sector)).filter(v => v > 0).sort((a, b) => a - b);
    cuts = values.length ? Array.from({ length: colors.length - 1 }, (_, i) =>
      values[Math.min(values.length - 1, Math.floor(((i + 1) / colors.length) * values.length))]) : [];
  }
  ctx.strokeStyle = css("--surface-2");
  ctx.lineWidth = 0.6;
  for (const name of communes) {
    const v = valueFor(name, sector);
    ctx.fillStyle = v === null || v === 0 ? css("--zero") : colors[binOf(v, cuts)];
    for (const polygon of miniShapes[name]) {
      ctx.beginPath();
      for (const ring of polygon) {
        ring.forEach(([x, y], i) => {
          if (i === 0) ctx.moveTo(x * w, y * h);
          else ctx.lineTo(x * w, y * h);
        });
        ctx.closePath();
      }
      ctx.fill();
      ctx.stroke();
    }
  }
}
function renderMinis() {
  if (!geoData) return;
  if (!miniShapes) buildMiniShapes();
  const minis = document.getElementById("minis");
  document.getElementById("minisHint").textContent =
    metric === "spec" ? "spécialisation de chaque secteur (bleu : sous-représenté, rouge : sur-représenté)"
      : "cliquer une carte pour explorer ce secteur";
  if (!minis.dataset.built) {
    minis.innerHTML = Object.entries(P.sectors).map(([id, s]) => `
      <div class="mini" data-sector="${id}" role="button" tabindex="0"
           aria-label="Explorer le secteur ${s.label}">
        <canvas width="220" height="200"></canvas>
        <div class="n">${s.label}</div><div class="c">${fmt(s.total)} entreprises</div>
      </div>`).join("");
    minis.dataset.built = "1";
    minis.querySelectorAll(".mini").forEach(card => {
      const open = () => {
        currentSector = card.dataset.sector;
        sectorSel.value = currentSector;
        showMapView();
        render();
        writeHash();
      };
      card.addEventListener("click", open);
      card.addEventListener("keydown", e => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
      });
    });
  }
  minis.querySelectorAll(".mini").forEach(card =>
    drawMini(card.querySelector("canvas"), card.dataset.sector));
}

/* ---------- Tableau ---------- */
function tableRows() {
  return communes.map(name => {
    const c = P.communes[name];
    const top = Object.entries(c.sectors).sort((a, b) => b[1] - a[1])[0];
    return {
      name, v: valueOf(name) ?? -1,
      topLabel: P.sectors[top[0]].label,
      share: c.total ? Math.round(100 * top[1] / c.total) : 0,
    };
  });
}
function renderTable() {
  const rows = tableRows().sort((a, b) => {
    const x = a[sortState.k], y = b[sortState.k];
    return (typeof x === "string" ? x.localeCompare(y) : x - y) * sortState.dir;
  });
  document.getElementById("tableBody").innerHTML = rows.map(r =>
    `<tr data-name="${r.name}"><td>${r.name}</td><td class="num">${fmtV(r.v < 0 ? null : r.v)}</td>
     <td>${r.topLabel}</td><td class="num">${r.share} %</td></tr>`).join("");
  document.querySelectorAll("thead th").forEach(th => {
    th.querySelector(".arrow").textContent =
      th.dataset.k === sortState.k ? (sortState.dir === -1 ? "▼" : "▲") : "";
  });
}
document.querySelectorAll("thead th").forEach(th => {
  th.addEventListener("click", () => {
    sortState = {
      k: th.dataset.k,
      dir: sortState.k === th.dataset.k ? -sortState.dir : (th.dataset.k === "name" ? 1 : -1),
    };
    renderTable();
  });
});
document.getElementById("tableBody").addEventListener("click", event => {
  const row = event.target.closest("tr");
  if (row) { selectCommune(row.dataset.name); showMapView(); }
});

/* ---------- Vues : carte / 3D / tableau / panorama ---------- */
const viewBtn = document.getElementById("viewBtn");
const sectorsBtn = document.getElementById("sectorsBtn");
const btnMap = document.getElementById("btnMap");
const VIEW_BUTTONS = { map: btnMap, "3d": btn3d, table: viewBtn, sectors: sectorsBtn };
function setView(view) {
  currentView = view;
  const inMap = view === "map" || view === "3d";
  document.getElementById("mapView").style.display = inMap ? "block" : "none";
  document.getElementById("tableView").style.display = view === "table" ? "block" : "none";
  document.getElementById("sectorsView").style.display = view === "sectors" ? "block" : "none";
  for (const [key, btn] of Object.entries(VIEW_BUTTONS)) {
    btn.setAttribute("aria-pressed", String(key === view));
  }
  if (inMap) ensure3d(view === "3d");
  if (view === "sectors") renderMinis();
  writeHash();
}
/* Revenir sur la carte sans perdre le mode 3D en cours. */
function showMapView() {
  if (currentView === "table" || currentView === "sectors") setView(mode3d ? "3d" : "map");
}
btnMap.addEventListener("click", () => setView("map"));
btn3d.addEventListener("click", () => setView(currentView === "3d" ? "map" : "3d"));
viewBtn.addEventListener("click", () => setView(currentView === "table" ? (mode3d ? "3d" : "map") : "table"));
sectorsBtn.addEventListener("click", () => setView(currentView === "sectors" ? (mode3d ? "3d" : "map") : "sectors"));

/* ---------- Infobulle ---------- */
const tooltip = document.getElementById("tooltip");
function showTip(event, name) {
  const c = P.communes[name];
  const v = valueOf(name);
  const extra = metric === "vol"
    ? `${ord(ranks[name])}/${communes.length}`
    : `${fmt(currentSector ? (c.sectors[currentSector] || 0) : c.total)} entreprises`;
  tooltip.innerHTML = `<strong>${name}</strong><br>
    <span class="n">${fmtV(v)}</span> · ${METRIC_LABEL[metric].toLowerCase()} · ${extra}<br>
    <span class="hint">cliquer pour le détail</span>`;
  tooltip.style.display = "block";
  const x = Math.min(event.clientX + 14, window.innerWidth - tooltip.offsetWidth - 8);
  const y = Math.min(event.clientY + 14, window.innerHeight - tooltip.offsetHeight - 8);
  tooltip.style.left = x + "px";
  tooltip.style.top = y + "px";
}
function hideTip() { tooltip.style.display = "none"; }

/* ---------- Démarrage ---------- */
const start = readHash();
sectorSel.value = currentSector;
metricButtons.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.metric === metric)));
applyTheme();
if (start.view !== "map") setView(start.view);
if (selected) {
  const name = selected;
  selected = null;
  selectCommune(name);
}
