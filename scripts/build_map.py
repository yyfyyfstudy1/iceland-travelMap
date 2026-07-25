#!/usr/bin/env python3
"""
Build a self-contained interactive map (troll_tours_map.html) of all 12 troll.is
day tours: each route drawn on an embedded Iceland outline, colored by region,
with its departure price. Reads data/tours.json + data/iceland.geojson.

Usage: python scripts/build_map.py
"""
import os, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOURS = json.load(open(os.path.join(ROOT, "data", "tours.json"), encoding="utf-8"))
ICELAND = json.load(open(os.path.join(ROOT, "data", "iceland.geojson"), encoding="utf-8"))
OUT = os.path.join(ROOT, "troll_tours_map.html")

REYK = {"name": "Pickup in Reykjavik", "lat": 64.14202864719405, "lng": -21.926494177316346}

# curated stops for the 3 tours that ship no geo itinerary (single-destination activities)
FALLBACK = {
    "snorkeling-in-silfra-with-transfer-from-reykjavik": [
        REYK, {"name": "Silfra Fissure (Þingvellir)", "lat": 64.2558, "lng": -21.1188},
        {"name": "Back to Reykjavík", "lat": REYK["lat"], "lng": REYK["lng"]}],
    "riding-and-hiking-in-the-valley-reykjadalur": [
        REYK, {"name": "Reykjadalur Valley", "lat": 64.024, "lng": -21.212},
        {"name": "Back to Reykjavík", "lat": REYK["lat"], "lng": REYK["lng"]}],
    "landmannalaugar-super-jeep-day-tour-from-reykjavik": [
        REYK,
        {"name": "Hjálparfoss", "lat": 64.113, "lng": -19.826},
        {"name": "Háifoss", "lat": 64.211, "lng": -19.686},
        {"name": "Landmannalaugar", "lat": 63.9903, "lng": -19.0578},
        {"name": "Back to Reykjavík", "lat": REYK["lat"], "lng": REYK["lng"]}],
}

# per-slug display metadata: short label + region
SHORT = {
    "golden-circle-bruarfoss-kerid":                        ("Golden Circle + Brúarfoss & Kerið", "Golden Circle"),
    "snaefellsnes-peninsula":                               ("Snæfellsnes Peninsula", "Snæfellsnes"),
    "south-coast-glacier-hike":                             ("South Coast + Glacier Hike", "South Coast"),
    "snaefellsnes-peninsula-chinese-day-tour":              ("Snæfellsnes 斯奈山 (中文团)", "Snæfellsnes"),
    "snorkeling-in-silfra-with-transfer-from-reykjavik":    ("Silfra Snorkeling", "Activity"),
    "riding-and-hiking-in-the-valley-reykjadalur":          ("Reykjadalur Riding + Hiking", "Activity"),
    "golden-circle-blue-lagoon":                            ("Golden Circle + Blue Lagoon", "Golden Circle"),
    "golden-circle-snorkeling-in-silfra":                   ("Golden Circle + Silfra Snorkel", "Golden Circle"),
    "south-coast-katla":                                    ("South Coast + Katla Ice Cave", "South Coast"),
    "landmannalaugar-super-jeep-day-tour-from-reykjavik":   ("Landmannalaugar Super Jeep", "Highland"),
    "vip-private-golden-circle-day-tour":                   ("VIP Golden Circle (Private)", "Golden Circle"),
    "south-coast-optional-glacier-hike-katla-private-tour": ("VIP South Coast (Private)", "South Coast"),
}

tours = []
for t in TOURS:
    slug = t["slug"]
    wps = t["waypoints"] if t["waypoints"] else FALLBACK.get(slug, [])
    short, region = SHORT[slug]
    tours.append({
        "no": t["no"], "operator": "trollis",
        "short": short, "name": t["name"], "name_zh": "",
        "price": t["listed_price_usd"], "currency": "USD", "unit": t["unit"],
        "hours": t["hours"], "rating": t["rating"], "type": t["type"],
        "note": t["note"], "url": t["url"], "region": region,
        "vip": t["no"] in (11, 12),
        "approx": not bool(t["waypoints"]),
        "waypoints": [{"name": w["name"], "lat": w["lat"], "lng": w["lng"]} for w in wps],
    })

# --- append the 3 external operators (routes geocoded from place names, approximate) ---
SRC = json.load(open(os.path.join(ROOT, "data", "sources", "sources_tours.json"), encoding="utf-8"))
no = len(tours)
for s in SRC:
    no += 1
    tours.append({
        "no": no, "operator": s["operator"],
        "short": s["name"][:54], "name": s["name"], "name_zh": s.get("name_zh", ""),
        "price": s.get("price"), "currency": s.get("currency", ""), "unit": s.get("unit", "每人"),
        "hours": s.get("hours"), "rating": s.get("rating"), "type": "",
        "note": s.get("note", ""), "url": s["url"], "region": s["region"],
        "vip": False, "approx": True,
        "waypoints": [dict({"name": w["name"], "lat": w["lat"], "lng": w["lng"]},
                           **({"zh": w["zh"]} if w.get("zh") else {})) for w in s["waypoints"]],
    })

html = open(os.path.join(HERE, "map_template.html"), encoding="utf-8").read()
html = html.replace("/*__ICELAND__*/null", json.dumps(ICELAND))
html = html.replace("/*__TOURS__*/null", json.dumps(tours, ensure_ascii=False))
open(OUT, "w", encoding="utf-8").write(html)
print("wrote", OUT, f"({os.path.getsize(OUT)} bytes) with {len(tours)} tours")
