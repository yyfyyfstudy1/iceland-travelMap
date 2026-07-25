// Upload data/firebase/tours.json into Firestore collection "tours".
// Usage:
//   npm i firebase-admin
//   # auth: either a service-account key ...
//   export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/serviceAccount.json
//   # ... or Application Default Credentials: gcloud auth application-default login
//   node scripts/upload_firestore.mjs <projectId>
import { readFileSync } from "node:fs";
import { initializeApp, applicationDefault, cert } from "firebase-admin/app";
import { getFirestore } from "firebase-admin/firestore";

const projectId = process.argv[2] || process.env.GCLOUD_PROJECT;
if (!projectId) { console.error("usage: node scripts/upload_firestore.mjs <projectId>"); process.exit(1); }

const keyPath = process.env.GOOGLE_APPLICATION_CREDENTIALS;
initializeApp({
  credential: keyPath ? cert(JSON.parse(readFileSync(keyPath, "utf8"))) : applicationDefault(),
  projectId,
});
const db = getFirestore();

const tours = JSON.parse(readFileSync(new URL("../data/firebase/tours.json", import.meta.url), "utf8"));
console.log(`uploading ${tours.length} tours to projects/${projectId}/tours ...`);

let n = 0;
for (let i = 0; i < tours.length; i += 400) {           // batched writes (<=500/batch)
  const batch = db.batch();
  for (const t of tours.slice(i, i + 400)) {
    batch.set(db.collection("tours").doc(t.id), t);      // waypoints stored as an array field
    n++;
  }
  await batch.commit();
  console.log(`  committed ${n}/${tours.length}`);
}
console.log("done.");
process.exit(0);
