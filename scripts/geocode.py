#!/usr/bin/env python3
"""
Geocode the unique stop names in data/sources/extracted.json to coordinates.
Seeded with known Iceland places; falls back to OpenStreetMap Nominatim
(rate-limited, per usage policy). Caches to data/sources/geocache.json.

Usage: python scripts/geocode.py
"""
import os, re, json, time, unicodedata, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "data", "sources")
EXTRACTED = os.path.join(SRC, "extracted.json")
CACHE = os.path.join(SRC, "geocache.json")

def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())

# known coordinates (lat, lng) — normalized-key seed
SEED_RAW = {
    "Reykjavik": (64.1466, -21.9426), "Keflavik Airport": (63.985, -22.605),
    "Thingvellir": (64.2559, -21.1295), "Silfra": (64.2558, -21.1188),
    "Geysir": (64.3104, -20.3024), "Gullfoss": (64.3271, -20.1199),
    "Kerid": (64.0411, -20.8856), "Bruarfoss": (64.264, -20.515),
    "Faxafoss": (64.157, -20.310), "Fridheimar": (64.138, -20.236),
    "Secret Lagoon": (64.1377, -20.3097), "Fludir": (64.1377, -20.3097),
    "Seljalandsfoss": (63.6156, -19.9886), "Skogafoss": (63.5320, -19.5114),
    "Skogar": (63.530, -19.511), "Reynisfjara": (63.4041, -19.0448),
    "Vik": (63.4186, -19.0060), "Dyrholaey": (63.4009, -19.1273),
    "Solheimajokull": (63.5316, -19.3706), "Solheimasandur Plane Wreck": (63.4591, -19.3636),
    "Plane Wreck": (63.4591, -19.3636), "Eyjafjallajokull": (63.63, -19.62),
    "Katla Ice Cave": (63.4833, -19.0029), "Myrdalsjokull": (63.66, -19.05),
    "Jokulsarlon": (64.0784, -16.2306), "Diamond Beach": (64.0447, -16.1793),
    "Fjallsarlon": (64.0128, -16.3853), "Skaftafell": (64.0159, -16.9666),
    "Svartifoss": (64.0276, -16.9752), "Vatnajokull": (64.0159, -16.9666),
    "Falljokull": (64.007, -16.86), "Hofn": (64.2539, -15.2082),
    "Djupivogur": (64.6558, -14.2793), "Hvolsvollur": (63.7513, -20.2225),
    "Kirkjufell": (64.9271, -23.3060), "Kirkjufellsfoss": (64.9268, -23.3096),
    "Arnarstapi": (64.7699, -23.6236), "Djupalonssandur": (64.7538, -23.9007),
    "Snaefellsjokull": (64.8080, -23.7767), "Stykkisholmur": (65.0745, -22.7275),
    "Ingjaldsholl": (64.8869, -23.744), "Grundarfjordur": (64.9223, -23.2544),
    "Budir": (64.8213, -23.3855), "Londrangar": (64.7360, -23.7890),
    "Ytri Tunga": (64.7967, -23.0906),
    "Blue Lagoon": (63.8804, -22.4495), "Sky Lagoon": (64.1163, -21.960),
    "Grindavik": (63.8424, -22.4370), "Reykjanes": (63.819, -22.688),
    "Landmannalaugar": (63.9903, -19.0578), "Hjalparfoss": (64.113, -19.826),
    "Haifoss": (64.211, -19.686), "Langjokull": (64.750, -20.000),
    "Gljufrabui": (63.622, -19.988), "Myvatn": (65.6039, -16.9959),
    "Akureyri": (65.6835, -18.1002), "Godafoss": (65.6828, -17.5496),
    "Lofthellir": (65.550, -16.720), "Dettifoss": (65.8149, -16.3847),
    "Krafla": (65.716, -16.769), "Grjotagja": (65.626, -16.883),
    "Snaefellsnes": (64.870, -23.400), "South Coast": (63.55, -19.50),
    "Golden Circle": (64.28, -20.30), "Hveragerdi": (64.0004, -21.1900),
    "Reykjadalur": (64.024, -21.212),
    # extras seen in the 3 new operators
    "Laugaras": (64.100, -20.687), "Eystrahorn": (64.2497, -14.567),
    "Hvalnes": (64.401, -14.535), "Reynisdrangar": (63.397, -19.038),
    "Stjornarfoss": (63.784, -18.060), "Faxafloi": (64.30, -22.10),
    "FlyOver Iceland": (64.1552, -21.9380), "Raufarholshellir": (63.933, -21.475),
    "Crystal Ice Cave": (64.048, -16.380), "Lofthellir": (65.550, -16.720),
    "Lofthellir Cave": (65.550, -16.720),
}
SEED = {norm(k): v for k, v in SEED_RAW.items()}

def seed_lookup(nm):
    cands = [nm]
    low = nm.lower().strip()
    for suf in ("national park","geothermal area","volcanic crater","glacier lagoon",
                "ice cave","lava tunnel","fissure","waterfall","crater","lighthouse","glacier"):
        if low.endswith(suf): cands.append(low[:-len(suf)].strip().strip(","))
    if "," in nm:
        cands += [nm.split(",")[0], nm.split(",")[-1]]
    for c in cands:
        if norm(c) in SEED: return SEED[norm(c)]
    return None

def nominatim(name):
    q = name if name.lower().endswith("iceland") else name + ", Iceland"
    url = "https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + \
          subprocess.list2cmdline([q]).strip('"').replace(" ", "%20").replace(",", "%2C")
    r = subprocess.run(["curl","-s","--max-time","25","-A","travelMengting-geocoder/1.0 (route map)",
                        "-H","Accept-Language: en", url], capture_output=True, text=True)
    try:
        j = json.loads(r.stdout)
        if j: return (round(float(j[0]["lat"]),5), round(float(j[0]["lon"]),5))
    except Exception:
        pass
    return None

def main():
    tours = json.load(open(EXTRACTED, encoding="utf-8"))
    names = []
    for t in tours:
        for s in t.get("stops", []):
            if s.get("name"): names.append(s["name"].strip())
    uniq = sorted(set(names))
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}

    seeded = hit = miss = new = 0
    for nm in uniq:
        if nm in cache and cache[nm]: hit += 1; continue
        sc = seed_lookup(nm)
        if sc:
            cache[nm] = list(sc); seeded += 1; continue
        coord = nominatim(nm); new += 1
        cache[nm] = list(coord) if coord else None
        if not coord: miss += 1
        time.sleep(1.1)   # Nominatim policy: <=1 req/sec

    json.dump(cache, open(CACHE, "w"), ensure_ascii=False, indent=1)
    matched = sum(1 for nm in uniq if cache.get(nm))
    print(f"unique stop names: {len(uniq)} | matched: {matched} | unmatched: {len(uniq)-matched}")
    print(f"(seed:{seeded} cache-hit:{hit} nominatim-queries:{new})")
    missing = [nm for nm in uniq if not cache.get(nm)]
    if missing: print("UNMATCHED:", ", ".join(missing))

if __name__ == "__main__":
    main()
