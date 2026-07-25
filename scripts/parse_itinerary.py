#!/usr/bin/env python3
"""Extract tour name, price, and itinerary waypoints (name + lat/lng) from a troll.is tour page's JSON-LD."""
import sys, json, re, html

def load_ldjson(path):
    with open(path, encoding="utf-8") as f:
        txt = f.read()
    blocks = re.findall(r'<script[^>]*type=["\']?application/ld\+json["\']?[^>]*>(.*?)</script>', txt, re.S | re.I)
    out = []
    for b in blocks:
        b = b.strip()
        try:
            out.append(json.loads(b))
        except Exception:
            try:
                out.append(json.loads(html.unescape(b)))
            except Exception:
                pass
    return out

def walk(obj):
    """yield every dict in a nested json structure"""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)

def geo_of(item):
    for d in walk(item):
        if "latitude" in d and "longitude" in d:
            try:
                return float(d["latitude"]), float(d["longitude"])
            except Exception:
                pass
    return None, None

def extract(path):
    data = load_ldjson(path)
    name, price, currency = None, None, None
    waypoints = []
    for doc in data:
        for d in walk(doc):
            t = d.get("@type")
            types = t if isinstance(t, list) else [t]
            # tour name / price
            if "Product" in types or "TouristTrip" in types or "Trip" in types:
                if not name and d.get("name"):
                    name = d["name"]
            if "Offer" in types and d.get("price"):
                price = d.get("price"); currency = d.get("priceCurrency")
            # itinerary list items
            if "ListItem" in types and isinstance(d.get("item"), dict):
                it = d["item"]
                itypes = it.get("@type"); itypes = itypes if isinstance(itypes, list) else [itypes]
                if any(x in ("TouristAttraction", "Place", "LandmarksOrHistoricalBuildings") for x in itypes):
                    lat, lng = geo_of(it)
                    waypoints.append({
                        "position": d.get("position"),
                        "name": it.get("name"),
                        "lat": lat, "lng": lng,
                    })
    # de-dupe by position/name, sort
    seen = set(); uniq = []
    for w in sorted(waypoints, key=lambda x: (x["position"] is None, x["position"] or 0)):
        key = (w["position"], w["name"])
        if key in seen: continue
        seen.add(key); uniq.append(w)
    return {"name": name, "price": price, "currency": currency, "waypoints": uniq}

if __name__ == "__main__":
    res = extract(sys.argv[1])
    print(json.dumps(res, ensure_ascii=False, indent=2))
