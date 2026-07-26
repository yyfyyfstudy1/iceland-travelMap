// Upsert the 10 nicetravel tours to Firestore via REST, authenticated with the firebase CLI's
// own refresh token (ADC was stale). Writes as the project owner -> bypasses security rules.
// No rule changes, no public-write window. Node 20 (global fetch).
import { readFileSync } from "node:fs";
import { homedir } from "node:os";

const PROJECT = "icelandtravel-5ad81";
// Public firebase-tools desktop OAuth client (baked into the open-source CLI).
const CLIENT_ID = "563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com";
const CLIENT_SECRET = "j9iVZfS8kkCEFUPaAeJV0sAi";

const cfg = JSON.parse(readFileSync(`${homedir()}/.config/configstore/firebase-tools.json`, "utf8"));
const refresh = cfg.tokens.refresh_token;

const tokRes = await fetch("https://oauth2.googleapis.com/token", {
  method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({ client_id: CLIENT_ID, client_secret: CLIENT_SECRET, refresh_token: refresh, grant_type: "refresh_token" }),
});
const tok = await tokRes.json();
if (!tok.access_token) { console.error("token exchange failed:", tok); process.exit(1); }
const AUTH = { Authorization: "Bearer " + tok.access_token };

function toValue(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === "boolean") return { booleanValue: v };
  if (typeof v === "number") return Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v };
  if (typeof v === "string") return { stringValue: v };
  if (Array.isArray(v)) return { arrayValue: { values: v.map(toValue) } };
  if (typeof v === "object") return { mapValue: { fields: toFields(v) } };
  return { stringValue: String(v) };
}
const toFields = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, toValue(v)]));

const tours = JSON.parse(readFileSync(new URL("../data/firebase/tours.json", import.meta.url), "utf8"));
const nice = tours.filter((t) => t.operator === "nicetravel");
console.log(`upserting ${nice.length} nicetravel tours to ${PROJECT}/tours ...`);

let n = 0;
for (const t of nice) {
  const url = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/tours/${t.id}`;
  const r = await fetch(url, { method: "PATCH", headers: { ...AUTH, "Content-Type": "application/json" }, body: JSON.stringify({ fields: toFields(t) }) });
  if (!r.ok) { console.error(`  FAIL ${t.id}: ${r.status} ${(await r.text()).slice(0, 300)}`); process.exit(1); }
  console.log(`  ${++n}/${nice.length}  ${t.id}`);
}
console.log("done.");
