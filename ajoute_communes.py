"""Ajoute aux lots la commune reelle, lue sur le site du prospect.

Pourquoi : la colonne "ville" porte le centre de la recherche, pas l'adresse du
pro. Un menuisier de Vaucresson ressort etiquete "Paris" parce qu'il tombe dans
le rayon de 25 km. Pour demarcher, c'est la commune qui compte.

Principe : on n'ecrase rien. La zone de recherche reste telle quelle, et la
commune n'est renseignee que si le site l'affiche avec son code postal. Quand
la page ne donne pas d'adresse lisible, la case reste vide - une case vide se
verifie d'un coup d'oeil, une commune devinee se propage.

Entree : _depts.json (produit par check_depts.py)   Sortie : lot_*.csv completes
"""
import csv, glob, json, re

# mots qui trainent apres le nom de commune dans le texte des pages
BRUIT = re.compile(
    r'^(?:t[ée]l|tel|fax|france|ouvert|horaires?|contact|email|mail|le|la|les'
    r'|l\'|de|du|des|siret|rcs|siege|adresse)$', re.I)


def commune_propre(brut):
    """Garde le nom de commune, coupe ce qui suit."""
    mots = re.split(r'[\s\-]+', (brut or '').strip())
    garde = []
    for i, m in enumerate(mots):
        if not m:
            continue
        if BRUIT.match(m) and i > 0:
            break
        # un mot en minuscules apres le premier n'appartient plus au toponyme
        if i > 0 and m[:1].islower() and m.lower() not in ('sur', 'sous', 'les',
                                                           'le', 'la', 'en',
                                                           'lez', 'aux', 'au'):
            break
        garde.append(m)
        if len(garde) >= 4:
            break
    return ' '.join(garde).strip(" -'")


data = json.load(open('_depts.json', encoding='utf-8'))
# domaine -> "Commune (CP)", uniquement pour les adresses effectivement lues
trouve = {}
for c in data['corrections']:
    nom = commune_propre(c['commune'])
    if nom:
        trouve[c['domaine']] = f"{nom} ({c['cp']})"

print(f"{len(trouve)} communes relevees sur les sites :")
for d, v in sorted(trouve.items()):
    print(f'  {d:<38} {v}')

for f in sorted(glob.glob('lot_*.csv')):
    rows = list(csv.reader(open(f, encoding='utf-8'), delimiter=';'))
    head, body = rows[0], rows[1:]
    if 'commune' in head:
        i = head.index('commune')
    else:
        i = head.index('ville') + 1
        head.insert(i, 'commune')
        for r in body:
            r.insert(i, '')
    n = 0
    for r in body:
        v = trouve.get(r[0])
        if v and r[i] != v:
            r[i] = v
            n += 1
    w = csv.writer(open(f, 'w', newline='', encoding='utf-8'), delimiter=';')
    w.writerow(head)
    w.writerows(body)
    print(f'{f} : {n} communes renseignees sur {len(body)} lignes')
