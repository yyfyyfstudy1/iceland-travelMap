#!/usr/bin/env python3
"""Fetch each selected tour page, extract visible text + title + any Google Maps
directions URL, and write data/sources/prefetch.json for the extraction workflow."""
import os, re, json, subprocess, html, time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUTDIR = os.path.join(ROOT, "data", "sources"); os.makedirs(OUTDIR, exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
LISTS = {
    "magicicelandtravel": "/tmp/recon/urls_magic12.txt",
    "bustravel":          "/tmp/recon/urls_bus12.txt",
    "adventures":         "/tmp/recon/urls_adv12.txt",
}

def fetch(url):
    r = subprocess.run(["curl","-sL","--max-time","40","-A",UA,url], capture_output=True, text=True)
    return r.stdout or ""

def visible(h):
    h = re.sub(r"<script[\s\S]*?</script>", " ", h, flags=re.I)
    h = re.sub(r"<style[\s\S]*?</style>", " ", h, flags=re.I)
    h = re.sub(r"<!--[\s\S]*?-->", " ", h)
    m = re.search(r"<title[^>]*>([\s\S]*?)</title>", h, re.I)
    title = html.unescape(m.group(1)).strip() if m else ""
    text = html.unescape(re.sub(r"<[^>]+>", " ", h))
    text = re.sub(r"\s+", " ", text).strip()
    return title, text

def gmaps(h):
    m = re.search(r"https?://www\.google\.[a-z.]+/maps/dir/[^\"'\s\\]+", h)
    return m.group(0) if m else ""

out = []
for op, lst in LISTS.items():
    for u in [l.strip() for l in open(lst) if l.strip()]:
        h = fetch(u)
        title, text = visible(h)
        out.append({"operator": op, "url": u, "title": title[:200], "gmaps_dir": gmaps(h), "text": text[:7000]})
        time.sleep(0.25)

json.dump(out, open(os.path.join(OUTDIR, "prefetch.json"), "w"), ensure_ascii=False, indent=1)
print(f"prefetched {len(out)} tours -> data/sources/prefetch.json\n")
for o in out:
    print(f"  {o['operator'][:12]:12} {'GMAP' if o['gmaps_dir'] else '    '} len={len(o['text']):5}  {o['title'][:64]}")
