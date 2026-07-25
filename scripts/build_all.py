#!/usr/bin/env python3
"""
Assemble the full multi-operator dataset with unified ISK prices and inject into
the MapLibre template -> index.html.

Sources:
  data/tours.json                     troll.is real JSON-LD waypoints
  data/sources/troll_bokun.json       troll.is ISK price/rating/duration (Bokun API)
  data/sources/bus_full.json          bustravel ISK price + agenda coords (Bokun API)
  data/sources/adv_api.json           adventures ISK price (api.adventures.is)
  data/sources/route_extracted.json   LLM-extracted ordered stops (bus + adventures)
  data/sources/gazetteer.json         canonical place name -> [lat,lng]
  data/sources/sources_tours.json     previous data (kept magic tours, unchanged)
"""
import os, json, re, unicodedata

HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
S=lambda *p: os.path.join(ROOT,"data","sources",*p)
def load(p, d=None):
    try: return json.load(open(p,encoding="utf-8"))
    except: return d

REYK={"name":"Pickup in Reykjavik","lat":64.142029,"lng":-21.926494}
def norm(s):
    s=unicodedata.normalize('NFD',s or '').encode('ascii','ignore').decode()
    return re.sub(r'[^a-z0-9]','',s.lower())

GAZ=load(S("gazetteer.json"),{})
NORM={norm(k):v for k,v in GAZ.items()}
def geo(name):
    v=NORM.get(norm(name))
    return {"name":name,"lat":v[0],"lng":v[1]} if v else None

REGION_MAP={"Snaefellsnes":"Snæfellsnes","Reykjavik":"Activity"}
def reg(r): return REGION_MAP.get(r,r or "Activity")
REGION_SIG=[
 ("Snæfellsnes",{"kirkjufell","arnarstapi","snaefellsjokull","djupalonssandur","budir","londrangar","grundarfjordur","stykkisholmur","ytritunga","ingjaldsholl"}),
 ("Westfjords",{"dynjandi","isafjordur","hesteyri","hornstrandir","sudavik","vigur"}),
 ("North Iceland",{"akureyri","myvatn","godafoss","dettifoss","asbyrgi","husavik","grjotagja","namafjall","dimmuborgir","eyjafjordur"}),
 ("East Iceland",{"djupivogur","seydisfjordur","studlagil","stodvarfjordur","eystrahorn","hvalnes"}),
 ("Highland",{"landmannalaugar","thorsmork","kerlingarfjoll","askja","haifoss","hjalparfoss","hekla"}),
 ("Reykjanes",{"bluelagoon","fagradalsfjall","grindavik","krysuvik","seltun","kleifarvatn","gunnuhver","reykjanesviti","sundhnukagigar","skylagoon"}),
 ("South Coast",{"seljalandsfoss","skogafoss","vik","reynisfjara","solheimajokull","dyrholaey","jokulsarlon","diamondbeach","skaftafell","fjallsarlon","fjadrargljufur","katlaicecave","myrdalsjokull"}),
 ("Golden Circle",{"thingvellir","geysir","gullfoss","kerid","bruarfoss","fridheimar","secretlagoon","silfra","faxi","laugarvatn"}),
]
def scan_region(wps):
    names=[norm(w["name"]) for w in wps if "Pickup" not in w["name"]]
    best=None;bestc=0
    for rg,sig in REGION_SIG:
        c=sum(1 for term in sig if any(term in nm for nm in names))
        if c>bestc: best=rg;bestc=c
    return best or "Activity"
def hours_of(txt):
    if not txt: return None
    m=re.search(r'(\d+)\s*hour', txt); h=int(m.group(1)) if m else None
    if h and re.search(r'30\s*min', txt): h+=0.5
    return h

tours=[]

# ---------- troll.is (12) : real waypoints + ISK price ----------
TROLL=load(os.path.join(ROOT,"data","tours.json"),[])
TB={t["slug"]:t for t in load(S("troll_bokun.json"),[]) if t.get("price_isk") is not None}
FALLBACK={
 "snorkeling-in-silfra-with-transfer-from-reykjavik":[REYK,{"name":"Silfra","lat":64.2558,"lng":-21.1188}],
 "riding-and-hiking-in-the-valley-reykjadalur":[REYK,{"name":"Reykjadalur","lat":64.024,"lng":-21.212}],
 "landmannalaugar-super-jeep-day-tour-from-reykjavik":[REYK,{"name":"Hjalparfoss","lat":64.113,"lng":-19.826},{"name":"Haifoss","lat":64.211,"lng":-19.686},{"name":"Landmannalaugar","lat":63.9903,"lng":-19.0578}],
}
SHORT={
 "golden-circle-bruarfoss-kerid":("Golden Circle + Brúarfoss & Kerið","Golden Circle"),
 "snaefellsnes-peninsula":("Snæfellsnes Peninsula","Snæfellsnes"),
 "south-coast-glacier-hike":("South Coast + Glacier Hike","South Coast"),
 "snaefellsnes-peninsula-chinese-day-tour":("Snæfellsnes 斯奈山 (中文团)","Snæfellsnes"),
 "snorkeling-in-silfra-with-transfer-from-reykjavik":("Silfra Snorkeling","Activity"),
 "riding-and-hiking-in-the-valley-reykjadalur":("Reykjadalur Riding + Hiking","Activity"),
 "golden-circle-blue-lagoon":("Golden Circle + Blue Lagoon","Golden Circle"),
 "golden-circle-snorkeling-in-silfra":("Golden Circle + Silfra Snorkel","Golden Circle"),
 "south-coast-katla":("South Coast + Katla Ice Cave","South Coast"),
 "landmannalaugar-super-jeep-day-tour-from-reykjavik":("Landmannalaugar Super Jeep","Highland"),
 "vip-private-golden-circle-day-tour":("VIP Golden Circle (Private)","Golden Circle"),
 "south-coast-optional-glacier-hike-katla-private-tour":("VIP South Coast (Private)","South Coast"),
}
no=0
for t in TROLL:
    slug=t["slug"]; b=TB.get(slug)
    wps=t["waypoints"] if t["waypoints"] else FALLBACK.get(slug,[])
    if not wps: continue
    short,region=SHORT.get(slug,(t["name"][:48],"Activity"))
    vip=t["no"] in (11,12)
    no+=1
    tours.append({"no":no,"operator":"trollis","short":short,"name":t["name"],"name_zh":"",
        "price":round(b["price_isk"]) if b else None,"currency":"ISK","unit":"每团" if vip else "每人",
        "hours":hours_of(b["duration"]) if b else t.get("hours"),"rating":(b.get("rating") or 0) if b else t.get("rating"),
        "region":region,"vip":vip,"url":t["url"],
        "waypoints":[{"name":w["name"],"lat":w["lat"],"lng":w["lng"]} for w in wps]})

# ---------- extracted routes (bus + adventures) ----------
EXT={r["url"].rstrip("/"):r for r in load(S("route_extracted.json"),[])}
BUS={b["url"].rstrip("/"):b for b in load(S("bus_full.json"),[]) if b.get("price") is not None}
ADV={a["url"].rstrip("/"):a for a in load(S("adv_api.json"),[]) if a.get("price") is not None}

JUNK=re.compile(r'reykjav|pickup|drop|meeting|hotel|start of|end of|safety|suit up|we expect|arrive|^\d+\.',re.I)
def clean_name(n):
    n=re.sub(r'^\d+\.\s*Stop at\s*','',n or ''); n=re.sub(r'\s+\d+\s*minutes?$','',n)
    return n.strip()

def build_route(url, op, price_rec):
    """return waypoints list (>=2 real stops) or None"""
    ex=EXT.get(url)
    stops=[]
    if ex and ex.get("is_multi_stop"):
        for s in ex.get("stops",[]):
            g=geo(s)
            if g and not any(abs(g["lat"]-x["lat"])<0.01 and abs(g["lng"]-x["lng"])<0.01 for x in stops):
                stops.append(g)
    # fallback: bus agenda coords
    if len(stops)<2 and op=="bustravel":
        seen=[]
        for w in (price_rec.get("waypoints") or []):
            nm=clean_name(w["name"])
            if JUNK.search(w["name"]) or not nm: continue
            if any(abs(w["lat"]-x["lat"])<0.01 and abs(w["lng"]-x["lng"])<0.01 for x in seen): continue
            seen.append({"name":nm,"lat":round(w["lat"],4),"lng":round(w["lng"],4)})
        if len(seen)>=2: stops=seen
    if len(stops)<2: return None
    return [REYK]+stops

def region_of(url, default="Activity"):
    ex=EXT.get(url); return reg(ex.get("region")) if ex else default

# bus
for url,b in BUS.items():
    wps=build_route(url,"bustravel",b)
    if not wps: continue
    no+=1
    tours.append({"no":no,"operator":"bustravel","short":(b.get("title") or url.split("/")[-1])[:52],
        "name":b.get("title") or "","name_zh":"","price":round(b["price"]),"currency":"ISK","unit":"每人",
        "hours":hours_of(b.get("duration")),"rating":round(b.get("rating") or 0,2),
        "region":region_of(url),"vip":False,"url":url,"waypoints":wps})
# adventures
for url,a in ADV.items():
    wps=build_route(url,"adventures",a)
    if not wps: continue
    no+=1
    tours.append({"no":no,"operator":"adventures","short":(a.get("title") or url.split("/")[-1])[:52],
        "name":a.get("title") or "","name_zh":"","price":round(a["price"]),"currency":"ISK","unit":"每人",
        "hours":None,"rating":0,"region":region_of(url),"vip":False,"url":url,"waypoints":wps})

# ---------- magic : Bokun row data (base64) + agenda coords, unified ISK ----------
GAZ_ITEMS=sorted(GAZ.items(), key=lambda kv:-len(kv[0]))  # longest names first
def scan_desc(text):
    """find canonical gazetteer places mentioned in text, ordered by first appearance"""
    low=(text or "").lower(); hits=[]
    for name,coord in GAZ_ITEMS:
        if name in ("Reykjavik","Reykjavík"): continue
        pos=low.find(name.lower())
        if pos>=0 and not any(name==h[0] for h in hits):
            hits.append((name,coord,pos))
    hits.sort(key=lambda x:x[2])
    out=[]
    for name,coord,_ in hits:
        if not any(abs(coord[0]-x["lat"])<0.01 and abs(coord[1]-x["lng"])<0.01 for x in out):
            out.append({"name":name,"lat":coord[0],"lng":coord[1]})
    return out
MDROP=re.compile(r'winter-dream|glacier-hiking-dream|iceclimbing-dream|northen-light-dream|'
                 r'transfer|shuttle|eclipse|festival|flyover|-ticket|admission|lava-show|'
                 r'perlan|whales?-of-iceland|hvammsvik|food-and-history|northern-lights|'
                 r'ice-cave-tour$|snowmobile', re.I)
MAG=[m for m in load(S("magic_full.json"),[]) if m.get("price_isk") is not None]
for m in MAG:
    slug=m.get("slug","").rstrip("/")
    if MDROP.search(slug): continue
    ag=[w for w in (m.get("agenda") or []) if "Pickup" not in w["name"] and w["name"].strip()]
    if len(ag)>=2:
        wps=[REYK]+[{"name":w["name"],"lat":round(w["lat"],4),"lng":round(w["lng"],4)} for w in ag]
    else:
        stops=scan_desc(m.get("desc",""))
        if len(stops)<2: continue
        wps=[REYK]+stops
    rating=m.get("rating")
    try: rating=round(float(rating),2)
    except: rating=0
    no+=1
    tours.append({"no":no,"operator":"magicicelandtravel","short":(m.get("title") or slug)[:52],
        "name":m.get("title") or "","name_zh":"","price":m["price_isk"],"currency":"ISK","unit":"每人",
        "hours":hours_of(m.get("duration")),"rating":rating,
        "region":scan_region(wps),"vip":False,"url":m["url"],"waypoints":wps})

# ---------- write + inject ----------
json.dump(tours, open(S("all_tours.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print("tours:", len(tours), dict(Counter(t["operator"] for t in tours)))
print("priced:", sum(1 for t in tours if t["price"] is not None), "/", len(tours))

tmpl=open(os.path.join(HERE,"maplibre_template.html"),encoding="utf-8").read()
out=tmpl.replace("/*__TOURS__*/null", json.dumps(tours, ensure_ascii=False))
open(os.path.join(ROOT,"index.html"),"w",encoding="utf-8").write(out)
print("wrote index.html", os.path.getsize(os.path.join(ROOT,"index.html")), "bytes")
