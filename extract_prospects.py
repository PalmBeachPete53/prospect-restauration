"""Etape 1 : collecte les commerces ayant un site web, ville par ville.

Methode : une requete par (ville, cle OSM), pas par (ville, niche). Les cinq
niches se partagent quatre cles seulement - craft, shop, amenity, leisure - et
demander "tous les commerces de cette cle qui ont un site" est une lecture
d'index, la ou une union de vingt valeurs faisait tomber le serveur en 504.
Le tri par niche se fait ensuite en local, gratuitement.

L'ecart n'est pas mince : tous les commerces de Paris dans 20 km reviennent en
11 secondes, quand l'ancienne methode n'arrivait pas au bout d'une seule niche.

Sortie : candidates_v2.tsv, dedoublonne par domaine.
Reprise : _raw_v2.json memorise les couples (ville, cle) deja traites.
"""
import urllib.request, urllib.parse, urllib.error, json, time, re, os, sys, threading, itertools
import concurrent.futures as cf

from config_prospect import CITIES, NICHES, OVERPASS_UA, is_directory

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]
RAW = '_raw_v2.json'
OUT = 'candidates_v2.tsv'
SERVER_TIMEOUT = 90

# (cle, valeur) -> niche. Construit une fois : c'est lui qui remplace les
# milliers de requetes par selecteur.
NICHE_DE = {}
for _niche, (_label, _sels) in NICHES.items():
    for _k, _v in _sels:
        NICHE_DE[(_k, _v)] = _niche
CLES = sorted({k for k, _v in NICHE_DE})


def build_query(cle, lat, lon, radius):
    """Tous les objets portant cette cle et un site web, dans le rayon."""
    return (f'[out:json][timeout:{SERVER_TIMEOUT}];'
            f'(nwr["{cle}"][~"^(website|contact:website)$"~"."]'
            f'(around:{radius},{lat},{lon}););out tags;')


HEADERS = {'User-Agent': OVERPASS_UA, 'Accept': 'application/json'}
_ep_index = itertools.count()


def fetch(query, tours=5):
    """Interroge Overpass en alternant les serveurs.

    429 = quota : il faut attendre, pas reessayer tout de suite.
    504 = surcharge passagere le plus souvent : un autre serveur repond.

    Piege connu : quand sa limite de temps expire, Overpass repond HTTP 200
    avec un JSON vide portant un champ "remark". Pris pour un succes, il fait
    disparaitre silencieusement tous les resultats.
    """
    data = urllib.parse.urlencode({'data': query}).encode()
    for tour in range(tours):
        ep = ENDPOINTS[next(_ep_index) % len(ENDPOINTS)]
        court = ep.split('//')[1].split('/')[0]
        try:
            req = urllib.request.Request(ep, data=data, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=SERVER_TIMEOUT + 30) as r:
                payload = json.load(r)
            remarque = payload.get('remark', '')
            if remarque:
                print(f'    ! {court}: remark "{remarque[:60]}"', flush=True)
                time.sleep(4)
                continue
            return payload
        except urllib.error.HTTPError as e:
            print(f'    ! {court}: HTTP {e.code}', flush=True)
            time.sleep(35 if e.code == 429 else 6)
        except Exception as exc:
            print(f'    ! {court}: {exc}', flush=True)
            time.sleep(8)
    return None


def normalize(url):
    url = (url or '').strip()
    if not url:
        return None
    if '://' not in url:
        url = 'http://' + url
    m = re.match(r'^https?://([^/:?#]+)', url)
    if not m:
        return None
    domain = m.group(1).lower().rstrip('.')
    if not re.match(r'^[a-z0-9-]+(\.[a-z0-9-]+)+$', domain):
        return None
    if domain.startswith('www.'):
        domain = domain[4:]
    if is_directory(domain):
        return None
    return domain


def main():
    results, counts = {}, {}
    seen = set()
    if os.path.exists(RAW):
        saved = json.load(open(RAW, encoding='utf-8'))
        results = saved.get('results', {})
        counts = saved.get('counts', {})
        seen = {tuple(p) for p in saved.get('pairs', [])}
        print(f'reprise : {len(results)} domaines, {len(seen)} couples faits',
              flush=True)

    def save():
        json.dump({'results': results, 'counts': counts, 'pairs': sorted(seen)},
                  open(RAW, 'w', encoding='utf-8'), ensure_ascii=False)

    voulues = set(NICHES)
    if '--niches' in sys.argv:
        voulues = set(sys.argv[sys.argv.index('--niches') + 1].split(','))
        print(f'niches limitees a : {", ".join(sorted(voulues))}', flush=True)

    taches = [(ville, dept, lat, lon, rayon, cle)
              for ville, dept, lat, lon, rayon in CITIES
              for cle in CLES
              if (ville, cle) not in seen]
    # Zones legeres d'abord : les stations balneaires repondent en quelques
    # secondes et fournissent de quoi constituer un lot sans attendre Paris.
    taches.sort(key=lambda t: t[4])
    total = len(taches)
    print(f'{total} couples (ville, cle) a traiter sur '
          f'{len(CITIES) * len(CLES)}', flush=True)

    verrou = threading.Lock()
    avance = [0]
    depart = time.time()

    def traiter(t):
        ville, dept, lat, lon, rayon, cle = t
        payload = fetch(build_query(cle, lat, lon, rayon))
        with verrou:
            avance[0] += 1
            n = avance[0]
            if payload is None:
                print(f'[{n}/{total}] {ville} / {cle}: ECHEC', flush=True)
                return
            elements = payload.get('elements', [])
            ajouts = 0
            for e in elements:
                tags = e.get('tags', {})
                niche = NICHE_DE.get((cle, tags.get(cle)))
                if niche is None or niche not in voulues:
                    continue          # cette valeur ne fait partie d'aucune niche
                brut = tags.get('website') or tags.get('contact:website') or ''
                dom = normalize(brut)
                if not dom:
                    continue
                counts[dom] = counts.get(dom, 0) + 1
                if dom in results:
                    continue
                results[dom] = [(tags.get('name') or '').strip(), niche, ville,
                                str(dept), brut.strip()]
                ajouts += 1
            seen.add((ville, cle))
            reste = (time.time() - depart) / n * (total - n) / 60
            print(f'[{n}/{total}] {ville} / {cle}: +{ajouts} '
                  f'({len(elements)} objets, total={len(results)}) '
                  f'~{reste:.0f} min restantes', flush=True)
            if n % 4 == 0:
                save()

    with cf.ThreadPoolExecutor(max_workers=2 * len(ENDPOINTS)) as ex:
        list(ex.map(traiter, taches))

    save()

    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        f.write('domaine\tnom\tniche\tville\tdept\tnb_etablissements\turl_brute\n')
        for dom, row in sorted(results.items()):
            nom, niche, ville, dept, brut = row
            f.write('\t'.join([dom, nom, niche, ville, dept,
                               str(counts.get(dom, 1)), brut]) + '\n')

    par_niche = {}
    for row in results.values():
        par_niche[row[1]] = par_niche.get(row[1], 0) + 1
    chaines = sum(1 for d in results if counts.get(d, 1) >= 3)
    print(f'\nTOTAL {len(results)} domaines uniques -> {OUT}')
    print(f'  dont {chaines} portes par 3+ etablissements (chaines)')
    for niche, n in sorted(par_niche.items(), key=lambda x: -x[1]):
        print(f'  {niche:<20} {n}')


if __name__ == '__main__':
    main()
