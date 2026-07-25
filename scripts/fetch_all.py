#!/usr/bin/env python3
"""
Fetch all 12 troll.is day-tour pages, extract price + itinerary waypoints (from
schema.org JSON-LD), merge with curated metadata, and write data/tours.json.

Usage:  python scripts/fetch_all.py
Requires: curl on PATH.  (No third-party deps.)
"""
import os, sys, json, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HTML_DIR = os.path.join(ROOT, "data", "html")
OUT_JSON = os.path.join(ROOT, "data", "tours.json")
sys.path.insert(0, HERE)
from parse_itinerary import extract

BASE = "https://troll.is/day-tour/"

# Curated metadata from the /day-tour/ archive listing (fields JSON-LD doesn't carry).
# slug: (no, listed_price_usd, unit, hours, rating, product_type, note)
META = {
    "golden-circle-bruarfoss-kerid":                        (1,  106,    "每人", 8,  4.8, "Troll.is Original", ""),
    "snaefellsnes-peninsula":                               (2,  140,    "每人", 12, 4.9, "Troll.is Original", ""),
    "south-coast-glacier-hike":                             (3,  179,    "每人", 12, 5.0, "Troll.is Original", ""),
    "snaefellsnes-peninsula-chinese-day-tour":              (4,  179,    "每人", 12, 4.9, "Troll.is Original", "中文向导"),
    "snorkeling-in-silfra-with-transfer-from-reykjavik":    (5,  223,    "每人", 6,  5.0, "—",                 ""),
    "riding-and-hiking-in-the-valley-reykjadalur":          (6,  225.44, "每人", 9,  4.5, "Trusted Partner",   ""),
    "golden-circle-blue-lagoon":                            (7,  253.8,  "每人", 11, 4.8, "Trusted Partner",   ""),
    "golden-circle-snorkeling-in-silfra":                   (8,  289,    "每人", 10, 5.0, "Troll.is Original", ""),
    "south-coast-katla":                                    (9,  299,    "每人", 12, 5.0, "Troll.is Original", ""),
    "landmannalaugar-super-jeep-day-tour-from-reykjavik":   (10, 350,    "每人", 13, 4.9, "Troll.is Original", "仅夏季 Summer"),
    "vip-private-golden-circle-day-tour":                   (11, 1350,   "每人", 8,  4.7, "—",                 "私人VIP · Spring Sale 特价"),
    "south-coast-optional-glacier-hike-katla-private-tour": (12, 1800,   "每团", 12, 5.0, "Troll.is Original", "私人VIP · 特价 · 整团报价"),
}

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"

def fetch(slug):
    path = os.path.join(HTML_DIR, slug + ".html")
    if os.path.exists(path) and os.path.getsize(path) > 10000:
        return path
    url = BASE + slug + "/"
    subprocess.run(["curl", "-s", "--max-time", "40", "-A", UA, url, "-o", path], check=True)
    return path

def main():
    os.makedirs(HTML_DIR, exist_ok=True)
    tours = []
    for slug, m in META.items():
        no, price, unit, hours, rating, ptype, note = m
        path = fetch(slug)
        parsed = extract(path)
        tours.append({
            "no": no,
            "slug": slug,
            "name": parsed["name"] or slug,
            "listed_price_usd": price,
            "jsonld_price": parsed["price"],
            "currency": parsed["currency"] or "USD",
            "unit": unit,
            "hours": hours,
            "rating": rating,
            "type": ptype,
            "note": note,
            "url": BASE + slug + "/",
            "waypoints": parsed["waypoints"],
        })
    tours.sort(key=lambda t: t["no"])
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(tours, f, ensure_ascii=False, indent=2)

    # report
    print(f"{'#':>2}  {'price':>7}  {'jld':>6}  {'wp':>3}  name")
    for t in tours:
        jld = t["jsonld_price"] if t["jsonld_price"] is not None else "-"
        flag = "" if (t["jsonld_price"] in (None, t["listed_price_usd"])) else "  <-- price mismatch"
        print(f"{t['no']:>2}  {t['listed_price_usd']:>7}  {str(jld):>6}  {len(t['waypoints']):>3}  {t['name'][:52]}{flag}")
    print("\nsaved", OUT_JSON)

if __name__ == "__main__":
    main()
