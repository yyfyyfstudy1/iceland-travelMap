// Seed config/rates in Firestore from open.er-api.com (ISK base). Web SDK; needs
// the tours/config write rule temporarily open (the deploy flow handles that).
import { readFileSync } from "node:fs";
import { initializeApp } from "firebase/app";
import { getFirestore, doc, setDoc } from "firebase/firestore";

const cfg = JSON.parse(readFileSync(new URL("../data/firebase/web_config.json", import.meta.url), "utf8"));
const CURS = ["ISK","AUD","USD","EUR","CNY","GBP"];
const d = await (await fetch("https://open.er-api.com/v6/latest/ISK")).json();
if (d.result !== "success") { console.error("FX failed"); process.exit(1); }
const rates = {}; CURS.forEach(c => { if (d.rates[c] != null) rates[c] = d.rates[c]; });
const db = getFirestore(initializeApp(cfg));
await setDoc(doc(db, "config", "rates"), { base:"ISK", rates, updated:new Date().toISOString(), source:"open.er-api.com" });
console.log("seeded config/rates:", JSON.stringify(rates));
process.exit(0);
