import concurrent.futures as cf, urllib.request, urllib.parse, socket, json, re, os, time

socket.setdefaulttimeout(12)
UA = {'User-Agent': 'Mozilla/5.0'}

# French region & tourism mapping by department
NORMANDIE = {14, 15, 27, 50, 61, 76}
ILE_DE_FRANCE = {75, 77, 78, 91, 92, 93, 94, 95}
COTE_AZUR = {4, 5, 6, 13, 83, 84}

# tourist attractiveness 3-5 per dept
DEPT_TOURISM = {
    75: 5, 78: 5, 77: 4, 91: 4, 92: 4, 93: 3, 94: 4, 95: 4,   # Ile-de-France
    6: 5, 83: 5, 13: 4, 84: 4, 4: 3, 5: 3,                      # Cote d'Azur / PACA
    14: 5, 76: 4, 50: 5, 27: 4, 61: 3,                          # Normandie
}

def region_of(dept):
    if dept in NORMANDIE: return 'Normandie'
    if dept in ILE_DE_FRANCE: return 'Ile-de-France'
    if dept in COTE_AZUR: return 'Cote d\'Azur'
    return None

def get(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.geturl(), r.read(600000).decode('utf-8', 'ignore')
    except Exception:
        return url, ''

CTX_KW = ['adresse', 'address', 'code postal', 'code postale', 'france', 'rue ',
          'boulevard', 'place', 'ville', 'commune', 'cp :', 'cp ', 'cedex', 'street',
          'rue,', 'place', 'avant', 'tel', 'tél ', 'postal code', 'zip', 'city', 'à ', 'a ']

def extract_postal(html):
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'[^A-Za-zÀ-ÿ0-9@\n .\-]', ' ', text)
    candidates = re.findall(r'\b([1-9][0-9]{4})\b', text)
    best = None; best_score = 0
    for cp in candidates:
        dept = int(cp[:2])
        if dept < 1 or dept > 95 or dept == 20:
            continue
        # find position
        idxs = [m.start() for m in re.finditer(r'(?<!\d)' + re.escape(cp) + r'(?!\d)', text)]
        sidx = idxs[0] if idxs else -1
        score = 1
        lo = max(0, sidx - 140); hi = min(len(text), sidx + 140)
        ctx = text[lo:hi].lower()
        for kw in CTX_KW:
            if kw in ctx:
                score += 1
        if score > best_score:
            best_score = score; best = (cp, dept)
    return best  # (cp, dept) or None
    return best  # (cp, dept) or None

def work(d):
    url = 'http://' + d
    final, html = get(url)
    res = extract_postal(html)
    if not res:
        return None
    cp, dept = res
    reg = region_of(dept)
    if not reg:
        return None
    return {'domain': d, 'cp': cp, 'dept': dept, 'region': reg,
            'tourist': DEPT_TOURISM.get(dept, 0)}

DONE = 'region_geo.json'
results = []
if os.path.exists(DONE):
    results = json.load(open(DONE))
todo = {}
for d, url, status, kind in json.load(open('live.json')):
    if d not in {r['domain'] for r in results}:
        todo[d] = url
print("already {} / todo {}".format(len(results), len(todo)), flush=True)

start = time.time()
with cf.ThreadPoolExecutor(max_workers=24) as ex:
    it = ex.map(work, list(todo), chunksize=8)
    for i, r in enumerate(it, 1):
        if r:
            results.append(r)
        if i % 600 == 0:
            json.dump(results, open(DONE, 'w'), ensure_ascii=False)
            print("progress {}/{} (geolocalises={})".format(i, len(todo), len(results)), flush=True)
json.dump(results, open(DONE, 'w'), ensure_ascii=False)
print("DONE geolocalise={}".format(len(results)), flush=True)