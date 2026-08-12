import urllib.request, urllib.parse, json, time, re, os, concurrent.futures as cf

# Coverage of mainland France (2x1 deg grid) + DOM bboxes, recursive split of failing cells
GRID = []
for lon in [-5.5, -3.5, -1.5, 0.5, 2.5, 4.5, 6.5, 8.5]:
    for lat_ in [41.0, 42.0, 43.0, 44.0, 45.0, 46.0, 47.0, 48.0, 49.0, 50.0, 51.0]:
        GRID.append((lat_, lon, lat_ + 1.0, lon + 2.0))
DOMS_BBOX = [
    (15.8, -61.9, 16.6, -61.0),    # Guadeloupe
    (14.3, -61.3, 14.9, -60.7),    # Martinique
    (2.1, -54.6, 5.9, -51.5),      # Guyane
    (-21.5, 55.1, -20.8, 55.9),    # La Réunion
    (-13.1, 44.9, -12.5, 45.4),    # Mayotte
]
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
MIN_CELL = 0.5  # stop splitting below this size

def query_bbox(endpoint, bb):
    s, w, n, e = bb
    q = (f'[out:json][timeout:120];(node["amenity"="restaurant"]["website"]({s},{w},{n},{e});'
         f'node["amenity"="restaurant"]["contact:website"]({s},{w},{n},{e});'
         f'way["amenity"="restaurant"]["website"]({s},{w},{n},{e});'
         f'way["amenity"="restaurant"]["contact:website"]({s},{w},{n},{e}););out tags;')
    data_b = urllib.parse.urlencode({'data': q}).encode()
    req = urllib.request.Request(endpoint, data=data_b, headers={'User-Agent': 'Mozilla/5.0 prospect-restaurateurs'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)

def query_region(endpoint, region):
    q = (f'[out:json][timeout:120];area["name"="{region}"]->.a;'
         f'(node["amenity"="restaurant"]["website"](area.a);'
         f'node["amenity"]["restaurant"]["contact:website"](area.a);'
         f'way["amenity"="restaurant"]["website"](area.a);'
         f'way["amenity"="restaurant"]["contact:website"](area.a););out tags;')
    data_b = urllib.parse.urlencode({'data': q}).encode()
    req = urllib.request.Request(endpoint, data=data_b, headers={'User-Agent': 'Mozilla/5.0 prospect-restaurateurs'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)

def fetch(task):
    kind, key = task
    for ep in ENDPOINTS:
        try:
            if kind == 'bbox':
                return query_bbox(ep, key)
            return query_region(ep, key)
        except Exception:
            time.sleep(1)
    return None

def normalize(url):
    url = (url or '').strip()
    if not url: return None
    if '://' not in url: url = 'http://' + url
    low = url.lower()
    bad = ('facebook.com','fb.com','instagram.com','google.com','yelp.com','tripadvisor.com',
           'thefork.com','linkedin.com','twitter.com','maps.google','pinterest.com','foursquare.com',
           'snapchat.com','tiktok.com','youtube.com','google.fr')
    if any(b in low for b in bad): return None
    m = re.match(r'^https?://([^/:?#]+)', url)
    if not m: return None
    domain = m.group(1).lower().rstrip('.')
    if not re.match(r'^[a-z0-9-]+(\.[a-z0-9-]+)+$', domain): return None
    if domain.split('.')[0] == 'www': domain = domain.partition('www.')[2]
    return domain

results = {}
stats = {'ok': 0, 'fail': 0, 'splits': 0}

def add_payload(payload, label):
    if not payload or 'elements' not in payload:
        return 0
    n = 0
    for e in payload['elements']:
        tags = e.get('tags', {})
        rname = (tags.get('name') or '').strip()
        raw = tags.get('website') or tags.get('contact:website') or ''
        dom = normalize(raw)
        if dom:
            results.setdefault(dom, (rname, raw.strip()))
            n += 1
    return n

def process(bb):
    stack = [(bb[0], bb[1], bb[2], bb[3], 0)]
    while stack:
        s, w, n, e, dep = stack.pop()
        payload = fetch(('bbox', (s, w, n, e)))
        nf = add_payload(payload, (s, w, n, e))
        if nf:
            stats['ok'] += 1
        else:
            if (n - s) <= MIN_CELL or (e - w) <= MIN_CELL:
                stats['fail'] += 1
            else:
                stats['splits'] += 1
                mid_s, mid_e = (s + n) / 2, (w + e) / 2
                stack.append((s, w, mid_s, mid_e, dep + 1))
                stack.append((s, mid_e, mid_s, e, dep + 1))
                stack.append((mid_s, w, n, mid_e, dep + 1))
                stack.append((mid_s, mid_e, n, e, dep + 1))
        print(f"bb {s:.2f},{w:.2f}->{n:.2f},{e:.2f}: {nf} (total={len(results)}) ok={stats['ok']} fail={stats['fail']} splits={stats['splits']}", flush=True)
        if len(results) % 2000 < 5:
            json.dump(results, open('_raw_domains.json', 'w'), ensure_ascii=False)

print("scan mainland...", flush=True)
for bb in GRID:
    process(bb)

print("scan DOM...", flush=True)
for bb in DOMS_BBOX:
    process(bb)

json.dump(results, open('_raw_domains.json', 'w'), ensure_ascii=False)
print(f"TOTAL domaines uniques: {len(results)}", flush=True)