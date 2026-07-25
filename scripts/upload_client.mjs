// One-time migration uploader using the Firebase Web SDK.
// Runs against the public web config; requires the Firestore "tours" write rule
// to be temporarily open (the migration flow opens it, uploads, then re-locks it).
//   node scripts/upload_client.mjs
import { readFileSync } from "node:fs";
import { initializeApp } from "firebase/app";
import { getFirestore, doc, writeBatch } from "firebase/firestore";

const cfg = JSON.parse(readFileSync(new URL("../data/firebase/web_config.json", import.meta.url), "utf8"));
const tours = JSON.parse(readFileSync(new URL("../data/firebase/tours.json", import.meta.url), "utf8"));

const db = getFirestore(initializeApp(cfg));
console.log(`uploading ${tours.length} tours to projects/${cfg.projectId}/tours ...`);

let n = 0;
for (let i = 0; i < tours.length; i += 400) {
  const batch = writeBatch(db);
  for (const t of tours.slice(i, i + 400)) { batch.set(doc(db, "tours", t.id), t); n++; }
  await batch.commit();
  console.log(`  committed ${n}/${tours.length}`);
}
console.log("done.");
process.exit(0);
