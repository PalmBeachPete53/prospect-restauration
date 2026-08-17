"""Verifie que la commune annoncee correspond a celle affichee sur le site.

La colonne "ville" porte le centre de la recherche, pas la commune du pro : un
artisan de la premiere couronne ressort etiquete au nom de la grande ville
voisine. On relit l'adresse sur la page pour retablir la vraie commune.

Un nombre a cinq chiffres ne suffit pas a designer un code postal (un prix, une
reference produit ou un numero de telephone tronque y ressemblent) : on exige
qu'il soit suivi d'un nom de commune, et on privilegie les adresses precedees
d'un mot de voirie.

Sortie : _depts.json  {corrections, muets}
"""
import csv, glob, re, json
import concurrent.futures as cf
import urllib.request

from config_prospect import BROWSER_UA

VOIRIE = r'(?:rue|avenue|av\.|bd|boulevard|place|chemin|impasse|route|all[ée]e|quai|cours|faubourg|zone|za|zi|c\.?c\.?)'
# code postal metropolitain suivi d'un nom de commune
ADRESSE = re.compile(
    r'\b((?:0[1-9]|[1-8]\d|9[0-5])\d{3})\s+'
    r'([A-ZÀ-Ý][\wÀ-ÿ\'\-]+(?:[ \-][A-ZÀ-Ýa-zà-ÿ\'\-]+){0,3})')
PRES_VOIRIE = re.compile(VOIRIE + r'[^.]{0,80}?\b((?:0[1-9]|[1-8]\d|9[0-5])\d{3})\b', re.I)


def texte(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': BROWSER_UA})
        with urllib.request.urlopen(req, timeout=12) as r:
            h = r.read(300000).decode('utf-8', 'ignore')
    except Exception:
        return ''
    h = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', h, flags=re.S | re.I)
    return ' '.join(re.sub(r'<[^>]+>', ' ', h).split())


def controle(item):
    fichier, dom, nom, dept, ville = item
    t = texte(f'http://{dom}')
    if not t:
        return (fichier, dom, nom, dept, ville, None, None, 'injoignable')

    # priorite aux codes postaux annonces juste apres un mot de voirie
    prioritaires = set(PRES_VOIRIE.findall(t))
    trouves = ADRESSE.findall(t)
    if not trouves:
        return (fichier, dom, nom, dept, ville, None, None, 'pas d\'adresse')

    retenus = [(cp, com) for cp, com in trouves if cp in prioritaires] or trouves
    freq = {}
    for cp, com in retenus:
        freq.setdefault(cp, []).append(com.strip())
    cp = max(freq, key=lambda k: len(freq[k]))
    commune = freq[cp][0]
    return (fichier, dom, nom, dept, ville, cp, commune,
            'ok' if cp[:2] == dept else 'ecart')


items = []
for f in sorted(glob.glob('lot_*.csv')):
    for r in csv.DictReader(open(f, encoding='utf-8'), delimiter=';'):
        items.append((f, r['domaine'], r['nom'], r['dept'].zfill(2), r['ville']))

print(f'{len(items)} prospects a controler', flush=True)
corrections, muets = [], []
with cf.ThreadPoolExecutor(max_workers=24) as ex:
    for res in ex.map(controle, items):
        fichier, dom, nom, dept, ville, cp, commune, verdict = res
        if verdict == 'ecart':
            corrections.append({'fichier': fichier, 'domaine': dom, 'nom': nom,
                                'dept_annonce': dept, 'ville_annoncee': ville,
                                'cp': cp, 'commune': commune})
        elif verdict != 'ok':
            muets.append({'fichier': fichier, 'domaine': dom, 'nom': nom,
                          'dept': dept, 'ville': ville, 'motif': verdict})

print(f'\n=== ECARTS CONFIRMES : {len(corrections)} ===')
for c in sorted(corrections, key=lambda x: (x['fichier'], x['nom'])):
    print(f"  {c['fichier']} | {c['nom'][:24]:<24} | "
          f"{c['ville_annoncee']} ({c['dept_annonce']}) -> "
          f"{c['commune']} ({c['cp']}) | {c['domaine']}")

print(f'\n=== ADRESSE ILLISIBLE : {len(muets)} ===')
for m in sorted(muets, key=lambda x: (x['fichier'], x['nom'])):
    print(f"  {m['fichier']} | {m['nom'][:24]:<24} | {m['ville']} ({m['dept']}) "
          f"| {m['motif']} | {m['domaine']}")

json.dump({'corrections': corrections, 'muets': muets},
          open('_depts.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n-> _depts.json')
