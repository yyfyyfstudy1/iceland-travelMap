#!/usr/bin/env python3
"""Regenerate Firebase-shaped exports from data/sources/all_tours.json:
  data/firebase/tours.json       array, each record has a stable `id` (operator_slug)
  data/firebase/tours_rtdb.json  {"tours": { id: record }} for `firebase database:set`
"""
import os, json, re
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
tours=json.load(open(os.path.join(ROOT,"data","sources","all_tours.json"),encoding="utf-8"))
def slug(u): return re.sub(r'[^a-z0-9\-]','',u.rstrip("/").split("/")[-1].lower())[:60]
seen={}; docs={}; arr=[]
for t in tours:
    base=f"{t['operator']}_{slug(t['url'])}"; i=seen.get(base,0); seen[base]=i+1
    did=base if i==0 else f"{base}-{i}"
    rec={k:t[k] for k in t if k!="no"}; rec["id"]=did
    docs[did]=rec; arr.append(rec)
os.makedirs(os.path.join(ROOT,"data","firebase"),exist_ok=True)
json.dump({"tours":docs}, open(os.path.join(ROOT,"data","firebase","tours_rtdb.json"),"w"), ensure_ascii=False, indent=1)
json.dump(arr, open(os.path.join(ROOT,"data","firebase","tours.json"),"w"), ensure_ascii=False, indent=1)
print(f"wrote data/firebase/tours.json ({len(arr)}) + tours_rtdb.json")
