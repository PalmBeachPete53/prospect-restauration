import urllib.request, urllib.parse, json, time, re, concurrent.futures as cf

ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
MIN_CELL = 0.5

FAILED = [
    (41.0, 2.5, 42.0, 4.5),(41.0, 4.5, 42.0, 6.5),(41.0, 6.5, 42.0, 8.5),
    (42.0, 0.5, 43.0, 2.5),(42.0, 6.5, 43.0, 8.5),(42.0, 8.5, 43.0, 10.5),
    (43.0, -1.5, 44.0, 0.5),(43.0, 0.5, 44.0, 2.5),(43.0, 4.5, 44.0, 6.5),(43.0, 6.5, 44.0, 8.5),
    (44.0, 2.5, 45.0, 4.5),(44.0, 4.5, 45.0, 6.5),(44.0, 6.5, 45.0, 8.5),(44.0, 8.5, 45.0, 10.5),
    (45.0, 0.5, 46.0, 2.5),(45.0, 2.5, 46.0, 4.5),(45.0, 6.5, 46.0, 8.5),(45.0, 8.5, 46.0, 10.5),
    (46.0, -1.5, 47.0, 0.5),(46.0, 8.5, 47.0, 10.5),
    (47.0, 0.5, 48.0, 2.5),(47.0, 4.5, 48.0, 6.5),
    (48.0, 6.5, 49.0, 8.5),(48.0, 8.5, 49.0, 10.5),
    (49.0, -1.5, 50.0, 0.5),(49.0, 2.5, 50.0, 4.5),(49.0, 4.5, 50.0, 6.5),(49.0, 6.5, 50.0, 8.5),
    (50.0, 2.5, 51.0, 4.5),(50.0, 8.5, 51.0, 10.5),
    (51.0, -1.5, 52.0, 0.5),(51.0, 0.5, 52.0, 2.5),(51.0, 2.5, 52.0, 4.5),
    (51.0, 4.5, 52.0, 6.5),(51.0, 6.5, 52.0, 8.5),
]

def query(endpoint, bb):
    s, w, n, e = bb
    q = (f'[out:json][timeout:120];(node["amenity"="restaurant"]["website"]({s},{w},{n},{e});'
         f'node["amenity"="restaurant"]["contact:website"]({s},{w},{n},{e});'
         f'way["amenity"="restaurant"]["website"]({s},{w},{n},{e});'
         f'way["amenity"="restaurant"]["contact:website"]({s},{w},{n},{e}););out tags;')
    data_b = urllib.parse.urlencode({'data': q}).encode()
    req = urllib.request.Request(endpoint, data=data_b, headers={'User-Agent': 'Mozilla/5.0 prospect-restaurateurs'})
    with urllib.request.urlopen(req, timeout=110) as r:
        return json.load(r)

def fetch(bb):
    for ep in ENDPOINTS:
        try:
            return query(ep, bb)
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
           'snapchat.com','tiktok.com','youtube.com')
    if any(b in low for b in bad): return None
    m = re.match(r'^https?://([^/:?#]+)', url)
    if not m: return None
    d = m.group(1).lower().rstrip('.')
    if not re.match(r'^[a-z0-9-]+(\.[a-z0-9-]+)+$', d): return None
    if d.split('.')[0] == 'www': d = d.partition('www.')[2]
    return d

def merge_into(results, payload):
    if not payload or 'elements' not in payload: return 0
    n = 0
    for e in payload['elements']:
        t = e.get('tags', {})
        raw = t.get('website') or t.get('contact:website') or ''
        name = (t.get('name') or '').strip()
        dom = normalize(raw)
        if dom:
            results.setdefault(dom, (name, raw.strip()))
            n += 1
    return n

def process_cell(bb, results, lock):
    stack = [bb]
    while stack:
        s, w, n, e = stack.pop()
        payload = fetch((s, w, n, e))
        nf = merge_into(results, payload)
        if not nf and (n - s) > MIN_CELL and (e - w) > MIN_CELL:
            ms, me = (s + n) / 2, (w + e) / 2
            stack.extend([(s, w, ms, me), (s, me, ms, e), (ms, w, n, me), (ms, me, n, e)])
    return len(results)

if __name__ == '__main__':
    results = json.load(open('_raw_domains.json', 'r'))
    print(f"start pool: {len(results)}", flush=True)
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(process_cell, cp, results, None): cp for cp in FAILED}
        for fut in cf.as_completed(futs):
            fut.result()
    print(f"TOTAL raw after recovery: {len(results)}", flush=True)
    json.dump(results, open('_raw_domains.json', 'w'), ensure_ascii=False)
    with open('candidates.tsv', 'w', encoding='utf-8') as f:
        for dom in sorted(results):
            name, url = results[dom]
            f.write(f"{dom}\t{name}\t{url}\t\n")
    print("candidates.tsv ecrit", flush=True)