"""Etape 4 : sort le lot suivant, 7 prospects par niche.

Methode : a chaque passage on livre BATCH_SIZE (7) prospects par niche, classes
par score de design decroissant. Les prospects deja livres sont memorises dans
delivered.json et ne ressortent jamais - y compris les 60 restaurants de la
campagne v1, injectes au premier passage.

Deux garde-fous issus de la campagne v1 :
  - les sites tiers (annuaires, plateformes) ne sont pas des prospects ;
  - une meme enseigne presente sur plusieurs domaines ne compte qu'une fois.

Usage :
    python select_batch.py            # livre le lot et le marque comme livre
    python select_batch.py --dry-run  # montre le lot sans rien marquer
"""
import csv, json, os, re, sys, unicodedata

from config_prospect import NICHES, BATCH_SIZE, MAX_ETABLISSEMENTS, not_qualified

DELIVERED = 'delivered.json'
MIN_DESIGN = 10          # en dessous, le site n'est pas assez date pour l'argumentaire
V1_DELIVERABLES = ('restaurants_tourisme_top40.csv', 'restaurants_tourisme_next20.csv')

dry_run = '--dry-run' in sys.argv


def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return re.sub(r'[^a-z0-9]', '', s)


def domain_root(d):
    """sushi-first.com et sushifirst.fr partagent la meme racine."""
    return norm(d.rsplit('.', 1)[0])


def load_delivered():
    if os.path.exists(DELIVERED):
        return json.load(open(DELIVERED, encoding='utf-8'))
    # premier passage : on part des prospects deja demarches en v1
    seed = []
    for path in V1_DELIVERABLES:
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as f:
            r = csv.reader(f, delimiter=';')
            next(r, None)
            seed += [row[0] for row in r if row]
    print(f'init : {len(seed)} prospects v1 marques comme deja livres')
    return {'lot': 0, 'domaines': sorted(set(seed))}


state = load_delivered()
already = set(state['domaines'])

info = {}
with open('candidates_v2.tsv', encoding='utf-8') as f:
    next(f)
    for line in f:
        p = line.rstrip('\n').split('\t')
        if len(p) >= 6:
            info[p[0]] = {'nom': p[1], 'niche': p[2], 'ville': p[3], 'dept': p[4],
                          'nb_etab': int(p[5]) if p[5].isdigit() else 1}

sites = {r['domain']: r for r in json.load(open('sites_v2.json', encoding='utf-8'))}

# --- candidats retenus ------------------------------------------------------
pool = []
for d, meta in info.items():
    s = sites.get(d)
    if not s or s.get('vide') or d in already or not_qualified(d):
        continue
    if meta['nb_etab'] >= MAX_ETABLISSEMENTS:   # chaine / franchise
        continue
    if s['design'] < MIN_DESIGN:
        continue
    pool.append({**meta, 'domaine': d, 'design': s['design'],
                 'anciennete': s['anciennete'],
                 'responsive': s.get('responsive', True),
                 'https': s.get('https', True),
                 'techno': s.get('generator') or '',
                 'signaux': ' | '.join(s.get('signaux', []))})

pool.sort(key=lambda r: (-r['design'], -r['anciennete']))

# --- une seule entree par enseigne ------------------------------------------
# Les enseignes deja livrees comptent aussi : sans ca, le second domaine d'une
# meme enseigne redeviendrait "unique" une fois le premier sorti du pool et
# serait livre au lot suivant.
vus_nom, vus_racine, uniques = set(), set(), []
for d in already:
    vus_racine.add(domain_root(d))
    meta = info.get(d)
    if meta and meta['nom']:
        vus_nom.add((norm(meta['nom']), meta['ville']))
for r in pool:
    cle_nom = (norm(r['nom']), r['ville']) if r['nom'] else None
    cle_racine = domain_root(r['domaine'])
    if (cle_nom and cle_nom in vus_nom) or cle_racine in vus_racine:
        continue
    if cle_nom:
        vus_nom.add(cle_nom)
    vus_racine.add(cle_racine)
    uniques.append(r)

# --- 7 par niche ------------------------------------------------------------
lot = []
for niche in NICHES:
    lot += [r for r in uniques if r['niche'] == niche][:BATCH_SIZE]

if not lot:
    print('Aucun prospect disponible : relancer les etapes 1 a 3.')
    sys.exit(0)

numero = state['lot'] + 1
sortie = f'lot_{numero:02d}.csv'
COLS = ['domaine', 'nom', 'niche', 'ville', 'dept', 'design', 'anciennete',
        'non_responsif', 'sans_https', 'techno', 'signaux_design']

with open(sortie, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(COLS)
    for r in lot:
        w.writerow([r['domaine'], r['nom'], NICHES[r['niche']][0], r['ville'],
                    r['dept'], r['design'], r['anciennete'],
                    'non' if r['responsive'] else 'oui',
                    'non' if r['https'] else 'oui',
                    r['techno'] or '—', r['signaux'] or '—'])

for niche, (label, _) in NICHES.items():
    lignes = [r for r in lot if r['niche'] == niche]
    dispo = sum(1 for r in uniques if r['niche'] == niche)
    manque = '' if len(lignes) == BATCH_SIZE else f'  (seulement {len(lignes)}/{BATCH_SIZE})'
    print(f'\n{label} - {len(lignes)} livres, {dispo} disponibles{manque}')
    for r in lignes:
        print(f"  {r['design']:>3} | {r['nom'][:28]:<28} | {r['ville']:<16} | {r['domaine']}")

if dry_run:
    print(f'\n[dry-run] {sortie} ecrit, delivered.json inchange.')
else:
    state['lot'] = numero
    state['domaines'] = sorted(already | {r['domaine'] for r in lot})
    json.dump(state, open(DELIVERED, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'\nLot {numero} : {len(lot)} prospects -> {sortie} '
          f'({len(state["domaines"])} domaines livres au total)')
