// Callable Cloud Function: re-fetch each tour's live "from" price from its source
// (Bókun for troll/bus/magic, api.adventures.is for adventures) and update Firestore.
// Runs server-side (no browser CORS limits). Deploy: firebase deploy --only functions
// Requires the Blaze plan.
const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { initializeApp } = require("firebase-admin/app");
const { getFirestore } = require("firebase-admin/firestore");

initializeApp();
const db = getFirestore();
const ADMIN_EMAIL = "yyfnhk@gmail.com";   // keep in sync with firestore.rules

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

exports.refreshPrices = onCall(
  { region: "australia-southeast1", timeoutSeconds: 540, memory: "512MiB" },
  async (req) => {
    if (!req.auth || req.auth.token.email !== ADMIN_EMAIL)
      throw new HttpsError("permission-denied", "admin only");
    const snap = await db.collection("tours").get();
    let updated = 0, failed = 0, unchanged = 0;
    for (const d of snap.docs) {
      const t = d.data();
      try {
        const p = await priceFor(t.src);
        if (p == null) { failed++; continue; }
        if (p !== t.price) { await d.ref.update({ price: p }); updated++; }
        else unchanged++;
      } catch (e) { failed++; }
    }
    return { total: snap.size, updated, unchanged, failed };
  }
);
