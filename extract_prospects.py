"""Etape 1 : interroge Overpass ville par ville et niche par niche.

Une requete par couple (ville, niche), avec un rayon autour du centre-ville qui
englobe la commune et sa premiere couronne. Sortie : candidates_v2.tsv
(domaine, nom, niche, ville, dept, url brute), dedoublonne par domaine.

Reprise possible : le fichier _raw_v2.json est relu au demarrage, les couples
deja traites sont sautes.
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


SERVER_TIMEOUT = 90     # au dela, mieux vaut decouper que d'attendre


def build_query(selectors, lat, lon, radius):
    """Une clause par selecteur.

    Les deux facons de taguer un site (website et contact:website) tiennent en
    une regex de cle plutot qu'en deux clauses : a nombre de selecteurs egal,
    la requete est deux fois plus legere, ce qui compte sur les zones denses.
    """
    parts = [f'nwr["{k}"="{v}"][~"^(website|contact:website)$"~"."]'
             f'(around:{radius},{lat},{lon});' for k, v in selectors]
    return (f'[out:json][timeout:{SERVER_TIMEOUT}];('
            + ''.join(parts) + ');out tags;')


HEADERS = {'User-Agent': OVERPASS_UA, 'Accept': 'application/json'}
_ep_index = itertools.count()


def fetch(query, tours=4):
    """Interroge Overpass en alternant les serveurs.

    429 = quota : il faut vraiment attendre, pas reessayer tout de suite.
    504 = requete trop lourde pour le serveur : l'appelant la decoupera.

    Piege : quand SA propre limite de temps expire, Overpass repond HTTP 200
    avec un JSON vide portant un champ "remark". Pris pour un succes, ca fait
    disparaitre silencieusement tous les resultats de la requete.
    """
    data = urllib.parse.urlencode({'data': query}).encode()
    for tour in range(tours):
        ep = ENDPOINTS[next(_ep_index) % len(ENDPOINTS)]
        court = ep.split('//')[1].split('/')[0]
        try:
            req = urllib.request.Request(ep, data=data, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=SERVER_TIMEOUT + 20) as r:
                payload = json.load(r)
            remarque = payload.get('remark', '')
            if remarque:
                print(f'    ! {court}: remark "{remarque[:60]}"', flush=True)
                if tour >= 1:
                    return None      # a decouper, ce n'est pas un vrai vide
                time.sleep(3)
                continue
            return payload
        except urllib.error.HTTPError as e:
            print(f'    ! {court}: HTTP {e.code}', flush=True)
            if e.code == 429:
                time.sleep(35)   # quota : la seule reponse utile est d'attendre
            elif e.code in (504, 502, 503):
                # Sur les instances publiques, un 504 traduit plus souvent une
                # surcharge passagere qu'une requete trop lourde : la meme
                # requete repart parfois en 30 s sur un autre serveur. On
                # insiste donc avant de conclure au poids et de decouper.
                time.sleep(6)
            else:
                time.sleep(5)
        except Exception as exc:
            print(f'    ! {court}: {exc}', flush=True)
            time.sleep(8)
    return None


# On part optimiste : dans une station balneaire, les 28 selecteurs de
# l'artisanat passent en une requete. Sur Paris ou Lyon, le serveur refuse des
# le deuxieme selecteur. Plutot que de fixer une taille qui serait absurde d'un
# cote ou de l'autre, on tente large et on divise a chaque refus.
TAILLE_PAQUET = 8


def _fetch_paquet(selectors, lat, lon, radius):
    """Un paquet de selecteurs, avec division en deux si le serveur cale."""
    payload = fetch(build_query(selectors, lat, lon, radius))
    if payload is not None:
        return payload.get('elements', []), True
    if len(selectors) == 1:
        print(f'    -- abandon sur {selectors[0][0]}={selectors[0][1]}', flush=True)
        return [], False
    milieu = len(selectors) // 2
    print(f'    .. decoupage en {milieu} + {len(selectors) - milieu} selecteurs', flush=True)
    gauche, ok_g = _fetch_paquet(selectors[:milieu], lat, lon, radius)
    droite, ok_d = _fetch_paquet(selectors[milieu:], lat, lon, radius)
    # ET, pas OU : une moitie perdue rend le resultat incomplet. Avec un OU,
    # une niche a moitie ramenee passait pour traitee et le cache gravait le
    # trou - c'est ce qui donnait des "+0" sur Paris sans le moindre ECHEC.
    return gauche + droite, (ok_g and ok_d)


def fetch_selectors(selectors, lat, lon, radius):
    """Recupere les elements d'une niche, par paquets de selecteurs.

    Le couple n'est considere comme traite que si TOUS les paquets ont abouti :
    sinon un paquet perdu ferait passer la niche pour depouillee, et le cache
    de reprise graverait ce vide dans le marbre.
    """
    elements, complet = [], True
    for i in range(0, len(selectors), TAILLE_PAQUET):
        lot, ok = _fetch_paquet(selectors[i:i + TAILLE_PAQUET], lat, lon, radius)
        elements += lot
        complet = complet and ok
    return elements, complet


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
    # {domaine: [nom, niche, ville, dept, url_brute]}
    results = {}
    # {domaine: nb d'etablissements portant ce domaine} -> detecte les chaines
    counts = {}
    seen_pairs = set()
    if os.path.exists(RAW):
        saved = json.load(open(RAW, encoding='utf-8'))
        results = saved.get('results', {})
        counts = saved.get('counts', {})
        seen_pairs = {tuple(p) for p in saved.get('pairs', [])}
        print(f'reprise : {len(results)} domaines, {len(seen_pairs)} couples deja faits',
              flush=True)

    def save():
        json.dump({'results': results, 'counts': counts, 'pairs': sorted(seen_pairs)},
                  open(RAW, 'w', encoding='utf-8'), ensure_ascii=False)

    # --niches a,b : ne traiter que ces niches (utile quand une seule manque
    # de candidats et qu'il faut elargir aux villes restantes sans tout refaire)
    voulues = set(NICHES)
    if '--niches' in sys.argv:
        voulues = set(sys.argv[sys.argv.index('--niches') + 1].split(','))
        print(f'niches limitees a : {", ".join(sorted(voulues))}', flush=True)

    taches = [(city, dept, lat, lon, radius, niche, selectors)
              for city, dept, lat, lon, radius in CITIES
              for niche, (_label, selectors) in NICHES.items()
              if niche in voulues and (city, niche) not in seen_pairs]
    total = len(taches)
    print(f'{total} couples a traiter sur {len(CITIES) * len(NICHES)}', flush=True)

    verrou = threading.Lock()
    avance = [0]

    def traiter(t):
        city, dept, lat, lon, radius, niche, selectors = t
        elements, ok = fetch_selectors(selectors, lat, lon, radius)
        with verrou:
            avance[0] += 1
            n = avance[0]
            if not ok:
                print(f'[{n}/{total}] {city} / {niche}: ECHEC', flush=True)
                return
            added = 0
            for e in elements:
                tags = e.get('tags', {})
                raw = tags.get('website') or tags.get('contact:website') or ''
                dom = normalize(raw)
                if not dom:
                    continue
                counts[dom] = counts.get(dom, 0) + 1
                if dom in results:
                    continue
                results[dom] = [(tags.get('name') or '').strip(), niche, city,
                                str(dept), raw.strip()]
                added += 1
            seen_pairs.add((city, niche))
            print(f'[{n}/{total}] {city} / {niche}: +{added} (total={len(results)})',
                  flush=True)
            if n % 5 == 0:
                save()

    # Un fil par serveur Overpass : chacun ne voit qu'une connexion a la fois,
    # ce qui reste dans les usages de l'API publique tout en allant 3x plus vite.
    with cf.ThreadPoolExecutor(max_workers=len(ENDPOINTS)) as ex:
        list(ex.map(traiter, taches))

    save()

    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        f.write('domaine\tnom\tniche\tville\tdept\tnb_etablissements\turl_brute\n')
        for dom, row in sorted(results.items()):
            nom, niche, city, dept, raw = row
            f.write('\t'.join([dom, nom, niche, city, dept,
                               str(counts.get(dom, 1)), raw]) + '\n')

    par_niche = {}
    for row in results.values():
        par_niche[row[1]] = par_niche.get(row[1], 0) + 1
    chaines = sum(1 for d in results if counts.get(d, 1) >= 3)
    print(f'\nTOTAL {len(results)} domaines uniques -> {OUT}')
    print(f'  dont {chaines} portes par 3+ etablissements (chaines, ecartees a l\'etape 4)')
    for niche, n in sorted(par_niche.items(), key=lambda x: -x[1]):
        print(f'  {niche:<20} {n}')


if __name__ == '__main__':
    main()
