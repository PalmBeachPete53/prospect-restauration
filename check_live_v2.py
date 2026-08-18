"""Etape 2 : garde les domaines qui repondent (HTTPS d'abord, puis HTTP).

Entree : candidates_v2.tsv     Sortie : live_v2.json  [[domaine, url, statut], ...]

Prudence sur le parallelisme : a 32 fils sur 16 000 domaines, la resolution DNS
locale sature et rend des echecs immediats. Un controle qui traite 16 000
domaines en deux minutes n'a pas teste grand-chose - un sondage avait montre
que 87 % des domaines declares morts repondaient en realite. Douze fils et un
delai franc coutent du temps mais ne jettent pas cinq mille prospects valables.

Deux passes : les echecs de la premiere sont rejoues plus lentement, car un
echec isole tient plus souvent a une saturation passagere qu'a un domaine mort.

Reprise : les domaines deja trouves vivants sont relus depuis live_v2.json et
sautes ; les autres sont retentes.
"""
import concurrent.futures as cf, urllib.request, urllib.error, socket, json, os, time

from config_prospect import BROWSER_UA

DELAI = 15
FILS = 12
socket.setdefaulttimeout(DELAI)
DONE_FILE = 'live_v2.json'


def check(d):
    for url in (f'https://{d}', f'http://{d}'):
        req = urllib.request.Request(url, method='GET',
                                     headers={'User-Agent': BROWSER_UA})
        try:
            with urllib.request.urlopen(req, timeout=DELAI) as r:
                return (d, r.geturl(), r.status)
        except urllib.error.HTTPError as e:
            # le domaine repond, il refuse juste l'acces anonyme
            if e.code in (401, 403):
                return (d, url, e.code)
        except Exception:
            pass
    return None


def passe(domaines, fils, libelle):
    trouves, echecs = [], []
    debut = time.time()
    with cf.ThreadPoolExecutor(max_workers=fils) as ex:
        for i, (d, res) in enumerate(zip(domaines, ex.map(check, domaines)), 1):
            (trouves if res else echecs).append(res if res else d)
            if i % 500 == 0:
                print(f'  {libelle} {i}/{len(domaines)} '
                      f'vivants={len(trouves)} ({int(time.time() - debut)}s)',
                      flush=True)
    return trouves, echecs


results = []
if os.path.exists(DONE_FILE):
    results = json.load(open(DONE_FILE, encoding='utf-8'))
deja = {r[0] for r in results}

domaines = []
with open('candidates_v2.tsv', encoding='utf-8') as f:
    next(f)
    for line in f:
        d = line.split('\t')[0]
        if d not in deja:
            domaines.append(d)

print(f'deja vivants : {len(deja)}, a tester : {len(domaines)} '
      f'({FILS} fils, {DELAI}s de delai)', flush=True)

trouves, echecs = passe(domaines, FILS, 'passe 1')
results += trouves
json.dump(results, open(DONE_FILE, 'w', encoding='utf-8'))
print(f'passe 1 : {len(trouves)} vivants, {len(echecs)} echecs a rejouer',
      flush=True)

if echecs:
    # moitie moins de fils : si la premiere passe a sature, insister au meme
    # rythme ne ferait que confirmer la saturation.
    trouves2, morts = passe(echecs, max(4, FILS // 2), 'passe 2')
    results += trouves2
    print(f'passe 2 : {len(trouves2)} vivants de plus, {len(morts)} morts confirmes',
          flush=True)

json.dump(results, open(DONE_FILE, 'w', encoding='utf-8'))
total = len(results)
print(f'TERMINE : {total} sites en ligne sur {total + len(domaines) - len(trouves)}',
      flush=True)
