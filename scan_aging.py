import concurrent.futures as cf, urllib.request, socket, json, os, re, time

socket.setdefaulttimeout(10)
DONE_FILE = "aging.json"
RESUME = {}
if os.path.exists(DONE_FILE):
    RESUME = {r["domain"]: r for r in json.load(open(DONE_FILE))}

live = json.load(open("live.json"))
target = [(d, url) for d, url, status, kind in live if d not in RESUME]
print(f"resume ok={len(RESUME)} todo={len(target)}", flush=True)

def fetch_home(d, url):
    req = urllib.request.Request(url, method='GET', headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            ct = r.headers.get('Content-Type', '')
            raw = r.read(400000)
            final_url = r.geturl()
            return d, final_url, r.status, raw, ct
    except urllib.error.HTTPError as e:
        return d, url, e.code, b'', ''
    except Exception:
        return d, url, 0, b'', ''

def analyze(d, url, status, raw, ct):
    txt = raw.decode('utf-8', 'ignore')
    low = txt.lower()
    all_years = set(int(y) for y in re.findall(r'(?:19|20)\d{2}', txt)) if txt else set()
    footyears = set()
    for m in re.finditer(r'(?:©|&copy;|copyright)\s*[()\- ]{0,4}((?:19|20)\d{2})\s*(?:[-–]\s*((?:19|20)\d{2}))?', low):
        footyears.add(int(m.group(1)))
        if m.group(2):
            footyears.add(int(m.group(2)))
    if not footyears:
        footyears = all_years
    copyright_year = max(footyears) if footyears else None
    max_year_seen = max(all_years) if all_years else None

    responsive = '<meta name="viewport"' in low
    https = url.startswith("https://")
    gm = re.search(r'<meta name="generator" content="([^"]*)"', low)
    generator = gm.group(1).strip()[:60] if gm else ""

    old_markers = []
    marks = [
        ('frontpage', 'FrontPage'), ('dreamweaver', 'Dreamweaver'),
        ('adobe go live', 'GoLive'), ('<font', '<font>'),
        ('<center>', '<center>'), ('bgcolor=', 'bgcolor'),
        ('<frameset', 'frameset'), ('microsoft office 4.0', 'MSO4'),
        ('//--></style>', 'legacy-css'),
    ]
    for sub, lab in marks:
        if sub in low:
            old_markers.append(lab)

    return {
        "domain": d, "url": url, "http_status": status,
        "content_type": ct, "copyright_year": copyright_year,
        "max_year_seen": max_year_seen, "responsive": responsive,
        "https": https, "generator": generator, "old_markers": old_markers,
        "size_bytes": len(raw),
    }

results = list(RESUME.values())
start = time.time()
n = 0
with cf.ThreadPoolExecutor(max_workers=32) as ex:
    futs = {ex.submit(fetch_home, d, url): (d, url) for d, url in target}
    for fut in cf.as_completed(futs):
        d, url, status, raw, ct = fut.result()
        results.append(analyze(d, url, status, raw, ct))
        n += 1
        if n % 400 == 0:
            json.dump(results, open(DONE_FILE, 'w'), ensure_ascii=False)
            print(f"progress {n}/{len(target)} elapsed={int(time.time()-start)}s", flush=True)
json.dump(results, open(DONE_FILE, 'w'), ensure_ascii=False)
print(f"DONE total={len(results)}", flush=True)