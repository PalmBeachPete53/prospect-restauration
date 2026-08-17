"""Etape 2 : garde les domaines qui repondent (HTTPS d'abord, puis HTTP).

Entree : candidates_v2.tsv     Sortie : live_v2.json  [[domaine, url, statut], ...]
Reprise : les domaines deja testes sont relus depuis live_v2.json et sautes.
"""
import concurrent.futures as cf, urllib.request, urllib.error, socket, json, os, time

from config_prospect import BROWSER_UA

socket.setdefaulttimeout(8)
DONE_FILE = 'live_v2.json'


def check(d):
    for url in (f'https://{d}', f'http://{d}'):
        req = urllib.request.Request(url, method='GET',
                                     headers={'User-Agent': BROWSER_UA})
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                return (d, r.geturl(), r.status)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return (d, url, e.code)
        except Exception:
            pass
    return None


results = []
if os.path.exists(DONE_FILE):
    results = json.load(open(DONE_FILE, encoding='utf-8'))
done = {r[0] for r in results}

domains = []
with open('candidates_v2.tsv', encoding='utf-8') as f:
    next(f)
    for line in f:
        domains.append(line.split('\t')[0])

todo = [d for d in domains if d not in done]
print(f'deja teste : {len(done)}, a tester : {len(todo)}', flush=True)

start = time.time()
processed = 0
with cf.ThreadPoolExecutor(max_workers=32) as ex:
    for res in ex.map(check, todo):
        processed += 1
        if res:
            results.append(res)
        if processed % 400 == 0:
            json.dump(results, open(DONE_FILE, 'w', encoding='utf-8'))
            print(f'{processed}/{len(todo)} en ligne={len(results)} '
                  f'({int(time.time() - start)}s)', flush=True)

json.dump(results, open(DONE_FILE, 'w', encoding='utf-8'))
print(f'TERMINE : {len(results)} sites en ligne', flush=True)
