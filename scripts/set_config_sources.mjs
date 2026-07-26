// Seed/update Firestore config/sources from data/firebase/config_sources.json via REST
// (firebase CLI refresh token; writes as project owner, bypasses rules).
import { readFileSync } from "node:fs";
import { homedir } from "node:os";

const PROJECT = "icelandtravel-5ad81";
const CLIENT_ID = "563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com";
const CLIENT_SECRET = "j9iVZfS8kkCEFUPaAeJV0sAi";

const cfg = JSON.parse(readFileSync(`${homedir()}/.config/configstore/firebase-tools.json`, "utf8"));
const tok = await (await fetch("https://oauth2.googleapis.com/token", {
  method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({ client_id: CLIENT_ID, client_secret: CLIENT_SECRET, refresh_token: cfg.tokens.refresh_token, grant_type: "refresh_token" }),
})).json();
if (!tok.access_token) { console.error("token exchange failed", tok); process.exit(1); }

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

const doc = JSON.parse(readFileSync(new URL("../data/firebase/config_sources.json", import.meta.url), "utf8"));
const url = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/config/sources`;
const r = await fetch(url, { method: "PATCH", headers: { Authorization: "Bearer " + tok.access_token, "Content-Type": "application/json" }, body: JSON.stringify({ fields: toFields(doc) }) });
if (!r.ok) { console.error("write failed", r.status, (await r.text()).slice(0, 400)); process.exit(1); }
console.log("config/sources written ✓  operators:", Object.keys(doc.operators).join(", "));
