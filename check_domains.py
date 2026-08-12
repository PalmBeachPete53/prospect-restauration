import concurrent.futures as cf, urllib.request, socket, json, os, time

socket.setdefaulttimeout(8)
DONE_FILE = "live.json"
TODO_FILE = "domains_todo.txt"

def check(d):
    for url in (f"https://{d}", f"http://{d}"):
        req = urllib.request.Request(url, method='GET', headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                ct = r.headers.get('Content-Type', '')
                body = r.read(2000).decode('utf-8', 'ignore').lower()
                kind = 'html' if 'html' in ct or '<' in body else 'txt'
                return (d, url, r.status, kind)
        except urllib.error.HTTPError as e:
            if e.code in (403, 401, 200, 301, 302, 307, 308):
                return (d, url, e.code, 'err-http')
            return None
        except Exception:
            pass
    return None

results = []
if os.path.exists(DONE_FILE):
    results = json.load(open(DONE_FILE))
done_domains = {r[0] for r in results}

domains = [l.split('\t')[0] for l in open('candidates.tsv')]
todo = [d for d in domains if d not in done_domains]
print(f"already done: {len(done_domains)}, todo: {len(todo)}", flush=True)

start = time.time()
processed = 0
with cf.ThreadPoolExecutor(max_workers=32) as ex:
    for res in ex.map(check, todo):
        processed += 1
        if res:
            results.append(res)
        if processed % 400 == 0:
            json.dump(results, open(DONE_FILE, 'w'))
            print(f"progress: {processed}/{len(todo)} live={len(results)} elapsed={int(time.time()-start)}s", flush=True)
json.dump(results, open(DONE_FILE, 'w'))
print(f"done. total live so far: {len(results)}", flush=True)