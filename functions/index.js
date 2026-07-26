// Cloud Functions for IcelandTravel. Deploy: firebase deploy --only functions
// Requires the Blaze plan. Callables are admin-only (email check).
//
// The OpenAI key is NEVER stored in this repo. Set it as a Functions secret:
//   firebase functions:secrets:set OPENAI_API_KEY      (paste the key at the prompt)
// The function reads it at runtime via OPENAI_API_KEY.value().
const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { defineSecret } = require("firebase-functions/params");
const { initializeApp } = require("firebase-admin/app");
const { getFirestore } = require("firebase-admin/firestore");

initializeApp();
const db = getFirestore();
const ADMIN_EMAIL = "yyfnhk@gmail.com";        // keep in sync with firestore.rules
const REGION = "australia-southeast1";
const OPENAI_API_KEY = defineSecret("OPENAI_API_KEY");

function requireAdmin(req) {
  if (!req.auth || req.auth.token.email !== ADMIN_EMAIL)
    throw new HttpsError("permission-denied", "admin only");
}

// ---------- refresh live prices from source APIs ----------
async function priceFor(src) {
  if (!src) return null;
  if (src.provider === "bokun") {
    const url = `https://widgets.bokun.io/widgets/${src.channel}/activity/${src.pid}` +
                `?availabilityRequired=1&currency=ISK&sessionId=srv&lang=en_GB`;
    const a = (await (await fetch(url)).json()).activity;
    return a && a.nextDefaultPrice != null ? Math.round(a.nextDefaultPrice) : null;
  }
  if (src.provider === "adventures") {
    const url = `https://api.adventures.is//v1.0/en/activity/${src.aid}?wp=CNAA&currency=USD&invsys=Bokun`;
    const a = await (await fetch(url)).json();
    return a && a.nextDefaultPrice != null ? Math.round(a.nextDefaultPrice) : null;
  }
  return null;
}
exports.refreshPrices = onCall({ region: REGION, timeoutSeconds: 540, memory: "512MiB" }, async (req) => {
  requireAdmin(req);
  const snap = await db.collection("tours").get();
  let updated = 0, failed = 0, unchanged = 0;
  for (const d of snap.docs) {
    const t = d.data();
    try {
      const p = await priceFor(t.src);
      if (p == null) { failed++; continue; }
      if (p !== t.price) { await d.ref.update({ price: p }); updated++; } else unchanged++;
    } catch (e) { failed++; }
  }
  return { total: snap.size, updated, unchanged, failed };
});

// ---------- AI import: fetch a tour URL, extract structured fields ----------
const EXTRACT_PROMPT = `You extract structured data about ONE Iceland day tour from the page text below.
Return ONLY a JSON object with these fields (use null / "" / [] when unknown):
- short: concise English title, <= 54 chars
- name: full tour title
- name_zh: Chinese title if the page is Chinese, else ""
- price: the per-person "from" price as a plain NUMBER (no symbols/commas), else null
- currency: ISO code of that price ("ISK","USD","EUR","CNY","GBP"), default "ISK"
- hours: tour duration in hours as a number, else null
- rating: review rating number (0-5), else 0
- region: EXACTLY one of ["South Coast","Golden Circle","Snæfellsnes","West Iceland","Highland","East Iceland","North Iceland","Westfjords","Reykjanes","Activity"]
  ("West Iceland" = Silver Circle / Borgarfjörður: Hraunfossar, Deildartunguhver, Húsafell, Reykholt, Víðgelmir.)
- operator: short lowercase operator key inferred from the URL domain. Prefer one of
  ["trollis","magicicelandtravel","bustravel","adventures","nicetravel"]; if the domain is none of these,
  use the domain's second-level name (e.g. grayline.is -> "grayline"). else ""
- waypoints: ORDERED array of the real geographic stops the tour visits, each {name, lat, lng}.
  name = canonical Icelandic place name spelled in English (e.g. Thingvellir, Geysir, Gullfoss, Seljalandsfoss, Skogafoss, Reynisfjara, Vik, Jokulsarlon, Kirkjufell). lat/lng = your best-known coordinates for that place (decimal degrees). EXCLUDE the Reykjavik hotel pickup/dropoff. Only include places actually visited.`;

exports.aiImport = onCall(
  { region: REGION, secrets: [OPENAI_API_KEY], timeoutSeconds: 120, memory: "512MiB" },
  async (req) => {
    requireAdmin(req);
    const url = ((req.data && req.data.url) || "").trim();
    if (!/^https?:\/\/\S+$/.test(url)) throw new HttpsError("invalid-argument", "provide a valid http(s) url");
    let html;
    try { html = await (await fetch(url, { headers: { "User-Agent": "Mozilla/5.0" } })).text(); }
    catch (e) { throw new HttpsError("unavailable", "could not fetch url: " + e.message); }
    const text = html
      .replace(/<script[\s\S]*?<\/script>/gi, " ").replace(/<style[\s\S]*?<\/style>/gi, " ")
      .replace(/<[^>]+>/g, " ").replace(/&[a-z#0-9]+;/gi, " ").replace(/\s+/g, " ").trim().slice(0, 14000);

    const r = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + OPENAI_API_KEY.value() },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        temperature: 0,
        response_format: { type: "json_object" },
        messages: [
          { role: "system", content: "You output only valid JSON. No prose." },
          { role: "user", content: EXTRACT_PROMPT + "\n\nURL: " + url + "\n\nPAGE TEXT:\n" + text },
        ],
      }),
    });
    if (!r.ok) throw new HttpsError("internal", "OpenAI " + r.status + ": " + (await r.text()).slice(0, 300));
    const j = await r.json();
    let data;
    try { data = JSON.parse(j.choices?.[0]?.message?.content || "{}"); }
    catch (e) { throw new HttpsError("internal", "model returned non-JSON"); }
    data.url = url;
    if (Array.isArray(data.waypoints))
      data.waypoints = data.waypoints
        .filter((w) => w && w.name && isFinite(+w.lat) && isFinite(+w.lng))
        .map((w) => ({ name: String(w.name), lat: +w.lat, lng: +w.lng }));
    return data;
  }
);

// ---------- discover: given a LISTING page, return the individual tour detail URLs ----------
// (Must run server-side: the admin browser can't fetch the operator site because of CORS.)
// The admin then fans out aiImport across these URLs in parallel and diffs the results vs Firestore.
const DISCOVER_PROMPT = `From the day-tour LISTING page's candidate links below, return ONLY a JSON object
{"urls":[...]} containing the absolute URLs of the INDIVIDUAL single-day-tour DETAIL pages (one per tour).
Rules:
- Include only single day-tour product/detail pages on this same site.
- EXCLUDE multi-day tours, and any blog / info / about / FAQ / contact / cart / account / category /
  listing / tag pages, and duplicates.
- Return absolute URLs exactly as given. Cap at 60.`;

exports.discoverListing = onCall(
  { region: REGION, secrets: [OPENAI_API_KEY], timeoutSeconds: 120, memory: "512MiB" },
  async (req) => {
    requireAdmin(req);
    const listing = ((req.data && req.data.listing) || "").trim();
    if (!/^https?:\/\/\S+$/.test(listing)) throw new HttpsError("invalid-argument", "provide a valid listing url");
    let base;
    try { base = new URL(listing); } catch (e) { throw new HttpsError("invalid-argument", "bad url"); }
    let html;
    try { html = await (await fetch(listing, { headers: { "User-Agent": "Mozilla/5.0" } })).text(); }
    catch (e) { throw new HttpsError("unavailable", "could not fetch listing: " + e.message); }

    // collect same-origin absolute hrefs (strip #fragment/?query, normalise trailing slash)
    const hrefs = new Set();
    const re = /href\s*=\s*["']([^"']+)["']/gi;
    let m;
    while ((m = re.exec(html))) {
      let h;
      try { h = new URL(m[1], listing); } catch (e) { continue; }
      if (h.origin !== base.origin) continue;
      if (!/^https?:$/.test(h.protocol)) continue;
      hrefs.add(h.origin + h.pathname.replace(/\/+$/, "") + "/");
    }
    const candidates = [...hrefs].filter((u) => u !== base.origin + "/").slice(0, 300);
    if (!candidates.length) return { listing, origin: base.origin, operator: "", count: 0, urls: [] };

    const r = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + OPENAI_API_KEY.value() },
      body: JSON.stringify({
        model: "gpt-4o-mini", temperature: 0, response_format: { type: "json_object" },
        messages: [
          { role: "system", content: "You output only valid JSON. No prose." },
          { role: "user", content: DISCOVER_PROMPT + "\n\nSITE: " + base.origin + "\n\nCANDIDATE LINKS:\n" + candidates.join("\n") },
        ],
      }),
    });
    if (!r.ok) throw new HttpsError("internal", "OpenAI " + r.status + ": " + (await r.text()).slice(0, 300));
    const j = await r.json();
    let data;
    try { data = JSON.parse(j.choices?.[0]?.message?.content || "{}"); }
    catch (e) { throw new HttpsError("internal", "model returned non-JSON"); }
    let urls = Array.isArray(data.urls) ? data.urls.filter((u) => typeof u === "string" && u.startsWith(base.origin)) : [];
    urls = [...new Set(urls.map((u) => u.replace(/\/+$/, "") + "/"))].slice(0, 60);
    const host = base.hostname.replace(/^www\./, "");
    const operator = host.split(".").slice(0, -1).join("").replace(/[^a-z0-9]/gi, "").toLowerCase();
    return { listing, origin: base.origin, operator, count: urls.length, urls };
  }
);

// ---------- discover via sitemap.xml (works even for JS-rendered listings like troll.is/magic) ----------
// Follows a sitemap or sitemap-index, collecting <loc> page URLs that match `pattern` (a regex).
exports.discoverSitemap = onCall(
  { region: REGION, timeoutSeconds: 120, memory: "512MiB" },
  async (req) => {
    requireAdmin(req);
    const sm = ((req.data && req.data.sitemap) || "").trim();
    const patSrc = (req.data && req.data.pattern) || "";
    if (!/^https?:\/\/\S+$/.test(sm)) throw new HttpsError("invalid-argument", "provide a sitemap url");
    let re = null;
    if (patSrc) { try { re = new RegExp(patSrc, "i"); } catch (e) { throw new HttpsError("invalid-argument", "bad pattern regex"); } }
    const seen = new Set(), out = new Set();
    async function crawl(url, depth) {
      if (depth > 2 || seen.has(url) || out.size > 800) return;
      seen.add(url);
      let xml = "";
      try { xml = await (await fetch(url, { headers: { "User-Agent": "Mozilla/5.0" } })).text(); } catch (e) { return; }
      const locs = [...xml.matchAll(/<loc>\s*([^<\s]+)\s*<\/loc>/gi)].map((m) => m[1].replace(/&amp;/g, "&"));
      const subs = locs.filter((u) => /\.xml(\.gz)?(\?|$)/i.test(u));
      for (const p of locs) {
        if (/\.xml(\.gz)?(\?|$)/i.test(p)) continue;               // it's a sub-sitemap, not a page
        if (!re || re.test(p)) out.add(p.replace(/\/+$/, "") + "/");
      }
      for (const s of subs.slice(0, 25)) { if (out.size > 800) break; await crawl(s, depth + 1); }
    }
    await crawl(sm, 0);
    return { sitemap: sm, count: out.size, urls: [...out].slice(0, 400) };
  }
);
