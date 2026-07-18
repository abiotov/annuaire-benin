/* Worker Cloudflare : interprète LLM de secours pour la recherche de l'atlas.
 *
 * Rôle strictement limité : traduire une question française libre en
 * intention structurée (action, secteur, communes, métrique). Les chiffres
 * sont TOUJOURS calculés par la page depuis ses agrégats : le LLM ne peut
 * pas halluciner une réponse, seulement mal router une question.
 *
 * Garde-fous : clé API en secret Cloudflare (jamais dans le code ni la page),
 * CORS restreint à l'atlas, limite de débit par IP, sortie plafonnée,
 * validation du JSON retourné. La clé Gemini est au palier gratuit : le pire
 * abus possible épuise un quota gratuit, jamais un budget.
 */
"use strict";

const ALLOWED_ORIGINS = new Set([
  "https://abiotov.github.io",
  "http://localhost:8744",
  "http://127.0.0.1:8744",
]);
const MODEL = "gemini-2.5-flash-lite";
const RATE_LIMIT_PER_MINUTE = 8;

const SECTORS = {
  "finance-mobile-money": "transfert d'argent, mobile money",
  "commerce-telephonie-electronique": "téléphonie, GSM, électronique, électroménager",
  "commerce-alimentaire": "alimentation, boissons, vivriers",
  "commerce-mode-beaute": "vêtements, textile, cosmétiques, bijoux",
  "commerce-agricole": "produits agricoles et forestiers, anacarde",
  "commerce-construction-quincaillerie": "quincaillerie, matériaux, plomberie",
  "commerce-maison-loisirs": "maison, bureau, papeterie, loisirs",
  "commerce-auto-moto": "automobile, moto, pièces détachées",
  "commerce-divers": "commerce divers",
  "energie-eau": "énergie, gaz, charbon, solaire, eau",
  "informatique-numerique": "informatique, logiciels, numérique",
  "btp-construction": "BTP, construction, rénovation",
  "industrie-transformation": "industrie, transformation, fabrication",
  "agriculture-elevage-peche": "agriculture, élevage, pêche",
  "transport-logistique": "transport, logistique, livraison",
  "restauration-hotellerie-tourisme": "restaurants, hôtels, tourisme",
  "immobilier": "immobilier",
  "services-professionnels": "conseil, juridique, comptabilité",
  "services-beaute": "coiffure, esthétique",
  "services-location": "location de matériel et d'espaces",
  "services-divers": "entretien, nettoyage, pressing, réparation",
  "medias-communication": "médias, édition, audiovisuel",
  "education-formation": "éducation, formation, auto-école",
  "sante-medical": "santé, médical, pharmacie",
  "assurance-finance": "assurance",
};
const ACTIONS = new Set(["count", "top", "profile", "density", "spec", "compare"]);

const buckets = new Map(); // ip -> {count, reset} ; par isolat, suffisant en dissuasion

function rateLimited(ip) {
  const now = Date.now();
  const bucket = buckets.get(ip);
  if (!bucket || now > bucket.reset) {
    buckets.set(ip, { count: 1, reset: now + 60_000 });
    return false;
  }
  bucket.count += 1;
  return bucket.count > RATE_LIMIT_PER_MINUTE;
}

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
  };
}

function buildPrompt(question) {
  const sectors = Object.entries(SECTORS)
    .map(([id, hint]) => `${id} (${hint})`).join(" ; ");
  return `Tu traduis une question sur l'économie du Bénin en intention JSON.
Actions possibles : count (compter), top (classement de communes), profile
(profil d'une commune), density (pour 1 000 habitants), spec (spécialisation,
sur/sous-représentation), compare (comparer exactement 2 communes).
Secteurs possibles (utilise l'identifiant exact, null si aucun) : ${sectors}.
Les communes sont les 77 communes du Bénin, en MAJUSCULES (ex. COTONOU,
PARAKOU, ABOMEY-CALAVI, SEME-PODJI). 0, 1 ou 2 communes.
Si la question EXCLUT une commune (« en dehors de X », « sauf X »), mets-la
dans "exclure" et pas dans "communes".
Réponds UNIQUEMENT ce JSON : {"action": "...", "sector": "..."|null,
"communes": ["..."], "exclure": ["..."], "confiance": 0.0-1.0}
Question : ${question}`;
}

async function parseWithGemini(question, apiKey) {
  // trim : un secret posé via un pipe shell peut embarquer un retour
  // chariot, qui casserait l'URL (constaté : 400 Bad Request).
  const url = "https://generativelanguage.googleapis.com/v1beta/models/"
    + `${MODEL}:generateContent?key=${apiKey.trim()}`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: [{ parts: [{ text: buildPrompt(question) }] }],
      generationConfig: {
        temperature: 0,
        maxOutputTokens: 200,
        responseMimeType: "application/json",
      },
    }),
  });
  if (!response.ok) {
    const detail = (await response.text()).slice(0, 300);
    throw new Error(`gemini ${response.status}: ${detail}`);
  }
  const body = await response.json();
  const text = (body.candidates?.[0]?.content?.parts || [])
    .map(part => part.text || "").join("");
  const parsed = JSON.parse(text);

  const action = ACTIONS.has(parsed.action) ? parsed.action : null;
  const sector = SECTORS[parsed.sector] ? parsed.sector : null;
  const clean = list => (Array.isArray(list)
    ? list.filter(c => typeof c === "string").map(c => c.toUpperCase()).slice(0, 2)
    : []);
  if (!action) throw new Error("action invalide");
  return { action, sector, communes: clean(parsed.communes), exclure: clean(parsed.exclure) };
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    if (!ALLOWED_ORIGINS.has(origin)) {
      return new Response(JSON.stringify({ error: "origine non autorisée" }),
        { status: 403, headers: { "Content-Type": "application/json" } });
    }
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }
    if (request.method !== "POST") {
      return new Response(JSON.stringify({ error: "POST attendu" }),
        { status: 405, headers: corsHeaders(origin) });
    }
    const ip = request.headers.get("CF-Connecting-IP") || "?";
    if (rateLimited(ip)) {
      return new Response(JSON.stringify({ error: "trop de requêtes" }),
        { status: 429, headers: corsHeaders(origin) });
    }
    let question;
    try {
      question = String((await request.json()).q || "").slice(0, 300).trim();
    } catch {
      question = "";
    }
    if (!question) {
      return new Response(JSON.stringify({ error: "question vide" }),
        { status: 400, headers: corsHeaders(origin) });
    }
    try {
      const intent = await parseWithGemini(question, env.GEMINI_API_KEY);
      return new Response(JSON.stringify(intent), { headers: corsHeaders(origin) });
    } catch (error) {
      return new Response(JSON.stringify({ error: String(error.message || error) }),
        { status: 502, headers: corsHeaders(origin) });
    }
  },
};
