"""Repere les chaines que le comptage OpenStreetMap laisse passer.

Le garde-fou MAX_ETABLISSEMENTS compte les etablissements portant le meme
domaine dans OSM. Il rate les groupes dont les points de vente ne sont pas tous
cartographies, ou sont disperses hors des villes scannees : un reseau de neuf
salons n'apparait qu'une fois et passe pour un artisan isole.

Ici on lit ce que le site dit de lui-meme : "nos salons", "nos agences",
"19 pressings", "notre reseau", "franchise". Un site qui parle de ses
etablissements au pluriel est gere au niveau du groupe, pas par le gerant local.

Sortie : _chaines.json  (liste des suspects, a trancher a la main)
"""
import csv, glob, json, re
import concurrent.futures as cf
import urllib.request

from config_prospect import BROWSER_UA

MOTIFS = [
    (re.compile(r'\bnos\s+(?:salons|agences|magasins|boutiques|ateliers|garages'
                r'|pressings|instituts|restaurants|centres|points\s+de\s+vente'
                r'|adresses|etablissements|établissements)\b', re.I), 'parle de SES etablissements'),
    (re.compile(r'\b(\d{1,3})\s+(?:salons|agences|magasins|boutiques|pressings'
                r'|instituts|garages|restaurants|centres)\b', re.I), 'annonce un nombre d\'etablissements'),
    (re.compile(r'\bnotre\s+r[ée]seau\b', re.I), 'parle de son reseau'),
    (re.compile(r'\b(?:franchis[ée]|franchise|succursales?)\b', re.I), 'franchise/succursale'),
    (re.compile(r'\btrouv(?:er|ez)\s+(?:un|votre|le)\s+\w+\s+(?:à\s+)?proximit[ée]', re.I),
     'localisateur de points de vente'),
    (re.compile(r'\bnos\s+\d{1,3}\s+\w+', re.I), 'compte ses implantations'),
]


def texte(dom):
    try:
        req = urllib.request.Request(f'http://{dom}', headers={'User-Agent': BROWSER_UA})
        with urllib.request.urlopen(req, timeout=12) as r:
            h = r.read(300000).decode('utf-8', 'ignore')
    except Exception:
        return ''
    h = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', h, flags=re.S | re.I)
    h = re.sub(r'&[a-z]+;|&#\d+;', ' ', h)
    return ' '.join(re.sub(r'<[^>]+>', ' ', h).split())


def controle(item):
    fichier, dom, nom, niche = item
    t = texte(dom)
    if not t:
        return None
    touches = []
    for motif, libelle in MOTIFS:
        m = motif.search(t)
        if m:
            a = max(0, m.start() - 60)
            touches.append({'motif': libelle,
                            'extrait': t[a:m.end() + 60].strip()})
    if not touches:
        return None
    return {'fichier': fichier, 'domaine': dom, 'nom': nom, 'niche': niche,
            'indices': touches}


items = []
for f in sorted(glob.glob('lot_*.csv')):
    for r in csv.DictReader(open(f, encoding='utf-8'), delimiter=';'):
        items.append((f, r['domaine'], r['nom'], r['niche']))

print(f'{len(items)} prospects a controler', flush=True)
suspects = []
with cf.ThreadPoolExecutor(max_workers=24) as ex:
    for res in ex.map(controle, items):
        if res:
            suspects.append(res)

suspects.sort(key=lambda s: (-len(s['indices']), s['fichier']))
json.dump(suspects, open('_chaines.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# la console Windows est en cp1252 : les pages ramenent des caracteres
# qu'elle ne sait pas afficher, et un rapport ne doit pas planter la-dessus.
def sur(s):
    return s.encode('cp1252', 'replace').decode('cp1252')

print(f'\n=== {len(suspects)} SUSPECTS ===\n')
for s in suspects:
    print(sur(f"{s['fichier']} | {s['nom'][:30]} | {s['domaine']}"
              f"  ({len(s['indices'])} indices)"))
    for i in s['indices'][:3]:
        print(sur(f"    {i['motif']} : ...{i['extrait'][:130]}..."))
    print()
print('-> _chaines.json')
