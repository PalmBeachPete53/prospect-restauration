"""Remplace dans les lots deja livres les prospects trop loin de leur ville.

Les lots 1 et 2 ont ete constitues avec un rayon de 25 km : un artisan de
Montigny-le-Bretonneux y figure sous l'etiquette "Paris", a 26 km du centre.
On les remplace par des prospects dont l'adresse a ete lue sur leur propre
site et dont la distance au centre-ville a ete calculee.

Un candidat dont la page n'affiche aucune adresse n'est pas retenu : c'est
exactement l'incertitude qui a produit le probleme qu'on repare ici.

Usage : python remplace_eloignes.py [--dry-run]
"""
import csv, json, math, re, sys, unicodedata
import urllib.request, urllib.parse
import concurrent.futures as cf

from config_prospect import (GRANDES_VILLES, NICHES, BROWSER_UA,
                             MAX_ETABLISSEMENTS, not_qualified, is_chain,
                             is_directory)

DRY = '--dry-run' in sys.argv
# Les lots deja remis a l'utilisateur ne se retouchent pas : on ne traite que
# les fichiers nommes en argument.
FICHIERS = [a for a in sys.argv[1:] if a.endswith('.csv')] or ['lot_01.csv', 'lot_02.csv']
SOURCE_CANDIDATS = 'candidates_v2.tsv' 
# Distance acceptable entre le prospect et le centre-ville annonce. 7 km etait
# trop severe : une banlieue a 20 km reste un prospect valable, seuls les cas
# aberrants genent (Thaon-les-Vosges rattache a Metz, a 97 km).
RAYON_MAX = 22.0         # km
CANDIDATS_PAR_TROU = 14  # profondeur d'exploration avant d'abandonner

CENTRES = {n: (la, lo) for n, _d, la, lo, _r in GRANDES_VILLES}
ADRESSE = re.compile(
    r'\b((?:0[1-9]|[1-8]\d|9[0-5])\d{3})\s+'
    r'([A-ZÀ-Ý][\wÀ-ÿ\'\-]+(?:[ \-][A-ZÀ-Ýa-zà-ÿ\'\-]+){0,3})')
CHAINE = re.compile(
    r'\bnos\s+(?:salons|agences|magasins|boutiques|pressings|instituts'
    r'|garages|restaurants|centres|adresses)\b|\bnotre\s+r[ée]seau\b'
    r'|\bfranchis[ée]s?\b', re.I)


def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return re.sub(r'[^a-z0-9]', '', s)


def km(a, b, c, d):
    R, p = 6371.0, math.radians
    return 2 * R * math.asin(math.sqrt(
        math.sin(p(c - a) / 2) ** 2
        + math.cos(p(a)) * math.cos(p(c)) * math.sin(p(d - b) / 2) ** 2))


_cp_cache = {}


def coord_cp(cp):
    """Centre officiel d'un code postal, via l'API geo de l'Etat."""
    if cp in _cp_cache:
        return _cp_cache[cp]
    try:
        url = f'https://geo.api.gouv.fr/communes?codePostal={cp}&fields=nom,centre'
        with urllib.request.urlopen(url, timeout=15) as r:
            j = json.load(r)
        c = j[0]['centre']['coordinates']
        _cp_cache[cp] = (c[1], c[0], j[0]['nom'])
    except Exception:
        _cp_cache[cp] = None
    return _cp_cache[cp]


def page(dom):
    try:
        req = urllib.request.Request(f'http://{dom}',
                                     headers={'User-Agent': BROWSER_UA})
        with urllib.request.urlopen(req, timeout=12) as r:
            h = r.read(300000).decode('utf-8', 'ignore')
    except Exception:
        return ''
    h = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', h, flags=re.S | re.I)
    h = re.sub(r'&[a-z]+;|&#\d+;', ' ', h)
    return ' '.join(re.sub(r'<[^>]+>', ' ', h).split())


def evalue(arg):
    """Le candidat est-il un independant, situe a moins de 7 km du centre ?"""
    dom, ville = arg
    t = page(dom)
    if not t:
        return dom, None, 'injoignable'
    if CHAINE.search(t):
        return dom, None, 'parle de ses etablissements'
    trouves = ADRESSE.findall(t)
    if not trouves:
        return dom, None, 'aucune adresse affichee'
    if ville not in CENTRES:
        return dom, None, 'ville hors liste'
    cla, clo = CENTRES[ville]
    # on garde l'adresse la plus proche : un site peut citer un fournisseur
    best = None
    for cp, _com in trouves:
        c = coord_cp(cp)
        if not c:
            continue
        d = km(cla, clo, c[0], c[1])
        if best is None or d < best[0]:
            best = (d, cp, c[2])
    if best is None:
        return dom, None, 'code postal inconnu'
    if best[0] > RAYON_MAX:
        return dom, None, f'{best[0]:.0f} km ({best[2]})'
    return dom, {'commune': f'{best[2]} ({best[1]})', 'km': best[0]}, 'ok'


def main():
    info = {}
    for l in open(SOURCE_CANDIDATS, encoding='utf-8').read().splitlines()[1:]:
        p = l.split('\t')
        if len(p) >= 6:
            info[p[0]] = {'nom': p[1], 'niche': p[2], 'ville': p[3],
                          'dept': p[4],
                          'nb': int(p[5]) if p[5].isdigit() else 1}
    sites = {r['domain']: r for r in json.load(open('sites_v2.json', encoding='utf-8'))}
    etat = json.load(open('delivered.json', encoding='utf-8'))
    livres = set(etat['domaines'])

    lots = {f: list(csv.DictReader(open(f, encoding='utf-8'), delimiter=';'))
            for f in FICHIERS}
    occupes = {r['domaine'] for v in lots.values() for r in v}
    noms_pris = {(norm(r['nom']), norm(r['ville'])) for v in lots.values() for r in v}

    # --- reperer les trop lointains -----------------------------------------
    trous = []
    for f, rows in lots.items():
        for r in rows:
            com = (r.get('commune') or '').strip()
            if '(' not in com or r['ville'] not in CENTRES:
                continue
            c = coord_cp(com.split('(')[-1].strip(') '))
            if not c:
                continue
            cla, clo = CENTRES[r['ville']]
            d = km(cla, clo, c[0], c[1])
            if d > RAYON_MAX:
                trous.append({'fichier': f, 'ligne': r, 'km': d, 'ou': c[2]})
    print(f'{len(trous)} prospects au-dela de {RAYON_MAX:.0f} km\n')

    # --- chercher un remplacant pour chacun ---------------------------------
    for t in trous:
        r = t['ligne']
        vieux = r['domaine']
        niche = info.get(vieux, {}).get('niche')
        if not niche:
            niche = next((k for k, (lab, _s) in NICHES.items() if lab == r['niche']), None)
        pool = []
        for d, m in info.items():
            if m['niche'] != niche or d in livres or d in occupes:
                continue
            s = sites.get(d)
            if not s or s.get('vide') or s['design'] < 15:
                continue
            if not_qualified(d) or is_chain(d) or is_directory(d):
                continue
            if m['nb'] >= MAX_ETABLISSEMENTS:
                continue
            if (norm(m['nom']), norm(m['ville'])) in noms_pris:
                continue
            if not m['nom'].strip():
                continue
            pool.append((s['design'], d, m))
        pool.sort(reverse=True, key=lambda x: x[0])
        pool = pool[:CANDIDATS_PAR_TROU]

        print(f"{t['fichier']} | {r['nom'][:26]:<26} | {t['km']:.0f} km ({t['ou']}) "
              f"-> examen de {len(pool)} candidats")
        gagnant = None
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            verdicts = dict((dom, (ok, why)) for dom, ok, why in
                            ex.map(evalue, [(d, m['ville']) for _sc, d, m in pool]))
        for sc, d, m in pool:
            ok, why = verdicts[d]
            if ok:
                gagnant = (sc, d, m, ok)
                print(f'    retenu  {sc:>3} | {m["nom"][:24]:<24} | '
                      f'{ok["commune"]} a {ok["km"]:.1f} km')
                break
            print(f'    ecarte  {sc:>3} | {m["nom"][:24]:<24} | {why}')
        if not gagnant:
            print('    !! aucun remplacant verifiable\n')
            continue
        sc, d, m, ok = gagnant
        s = sites[d]
        r['domaine'] = d
        r['nom'] = m['nom']
        r['ville'] = m['ville']
        r['commune'] = ok['commune']
        r['dept'] = m['dept']
        r['design'] = s['design']
        r['anciennete'] = s['anciennete']
        r['non_responsif'] = 'non' if s.get('responsive', True) else 'oui'
        r['sans_https'] = 'non' if s.get('https', True) else 'oui'
        r['techno'] = s.get('generator') or '—'
        r['signaux_design'] = ' | '.join(s.get('signaux', [])) or '—'
        occupes.add(d)
        noms_pris.add((norm(m['nom']), norm(m['ville'])))
        # Le prospect ecarte reste marque comme sorti : le rendre au vivier le
        # ferait ressortir au lot suivant avec le defaut qui l'avait fait
        # retirer. C'est arrive a 'Poilane', retire du lot 3 et revenu au lot 4.
        livres.add(d)
        print(f'    (a inscrire dans NOT_QUALIFIED_DOMAINS : {vieux})')
        print()

    if DRY:
        print('[dry-run] rien ecrit.')
        return
    for f, rows in lots.items():
        champs = list(rows[0].keys())
        w = csv.DictWriter(open(f, 'w', newline='', encoding='utf-8'),
                           fieldnames=champs, delimiter=';')
        w.writeheader()
        w.writerows(rows)
        print(f'{f} reecrit')
    etat['domaines'] = sorted(livres)
    json.dump(etat, open('delivered.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'delivered.json : {len(etat["domaines"])} domaines')


if __name__ == '__main__':
    main()
