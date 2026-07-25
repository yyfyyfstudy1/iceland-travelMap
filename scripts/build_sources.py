#!/usr/bin/env python3
"""
Join extracted tours (data/sources/extracted.json) with geocoded coordinates
(data/sources/geocache.json) into map-ready route entries with operator +
approx flags. Writes data/sources/sources_tours.json.

Run after: scripts/geocode.py
"""
import os, json

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "data", "sources")
extracted = json.load(open(os.path.join(SRC, "extracted.json"), encoding="utf-8"))
prefetch  = json.load(open(os.path.join(SRC, "prefetch.json"),  encoding="utf-8"))
geo       = json.load(open(os.path.join(SRC, "geocache.json"),  encoding="utf-8"))

REGION_MAP = {
    "south coast": "South Coast", "golden circle": "Golden Circle",
    "snaefellsnes": "Snæfellsnes", "snæfellsnes": "Snæfellsnes",
    "highland": "Highland", "east iceland": "East Iceland",
    "north iceland": "North Iceland", "reykjanes": "Reykjanes",
    "activity": "Activity",
}
def region_of(r):
    return REGION_MAP.get((r or "").strip().lower(), "Activity")

out, skipped = [], []
for t in extracted:
    if not t: continue
    i = t.get("_i")
    pf = prefetch[i] if (isinstance(i, int) and i < len(prefetch)) else {}
    op = pf.get("operator", "unknown"); url = pf.get("url", "")
    wps = []
    for s in t.get("stops", []):
        nm = (s.get("name") or "").strip()
        c = geo.get(nm)
        if not c: continue
        w = {"name": nm, "lat": c[0], "lng": c[1]}
        if s.get("zh"): w["zh"] = s["zh"]
        # drop consecutive duplicates (same rounded coord)
        if wps and abs(wps[-1]["lat"]-w["lat"]) < 1e-4 and abs(wps[-1]["lng"]-w["lng"]) < 1e-4:
            continue
        wps.append(w)
    if len(wps) < 2:
        skipped.append((op, t.get("name"), len(wps))); continue
    out.append({
        "operator": op,
        "name": t.get("name") or "",
        "name_zh": t.get("name_zh") or "",
        "price": t.get("price"),
        "currency": t.get("currency") or "",
        "unit": "每人",
        "hours": t.get("duration_hours"),
        "rating": None,
        "region": region_of(t.get("region")),
        "note": (t.get("notes") or "")[:40],
        "url": url,
        "approx": True,
        "confidence": t.get("confidence") or "",
        "waypoints": wps,
    })

json.dump(out, open(os.path.join(SRC, "sources_tours.json"), "w"), ensure_ascii=False, indent=1)
from collections import Counter
by_op = Counter(o["operator"] for o in out)
print(f"kept {len(out)} routes | skipped {len(skipped)} (too few geocoded stops)")
for op, n in by_op.items(): print(f"  {op}: {n} routes")
if skipped:
    print("skipped:", "; ".join(f"{op}:{nm}({n})" for op, nm, n in skipped))
