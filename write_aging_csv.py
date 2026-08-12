import json, csv, random, unicodedata, re

def norm(s):
    s = unicodedata.normalize('NFD', s)
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()

# strong non-French structural markers -> drop (conservative)
FOREIGN_TOKENS = [
    'ristorante', 'trattoria', 'albergo', 'osteria', 'gasthof', 'gasthaus',
    'wirtshaus', 'staustube', 'weinstube', 'kranenturm', 'hostel', 'guesthouse',
    'bed and breakfast', 'bed & breakfast', 'b&b', 'posada', 'hostal', 'bodega',
    'de lokeend', 'wirtsstube', 'brauhaus', 'brewery', 'pub restaurant',
    'heritage hotel', 'roistrer', 'sobre mesa', 'haos', 'ukermark', 'perahu',
    'unter freunden', 'eten drinken', 'ankerstube', 'mövenpick', 'movenpick',
    'zur', 'zum', 'kegelstuben', 'scholzehof', 'romkerhall', 'koenigreich',
    'in den hof', 'lisas welt', 'ochsen', 'agriturismo', 'molino',
    'restaurante', 'wirtshaus', 'biergarten', 'wirtsstub', 'gasthaus',
]
# foreign-location markers that can appear in the domain OR the name
LOCATION_MARKERS = [
    'koeln', 'koln', 'naumburg', 'naumburg', 'stubbington', 'wolgen',
    'moevenpick', 'movenpick', 'schwaben', 'wurzburg', 'hamburg',
    'merklingen', 'erbacher', 'ldn', 'loveshackldn', 'london', 'mainz',
    'bernau', 'gempenturm',
]

def is_foreign(name, domain):
    nm = norm(name)
    d = norm(domain)
    # compact = only alphanumeric, to catch variants like "anker-stube"/"ankerstube"
    compact = re.sub(r'[^a-z0-9]', '', nm + d)
    spaced = (nm + ' ' + d)
    for t in FOREIGN_TOKENS:
        ct = re.sub(r'[^a-z0-9]', '', t)
        if ct and ct in compact:
            return True
    for m in LOCATION_MARKERS:
        if m in spaced or re.sub(r'[^a-z0-9]', '', m) in compact:
            return True
    return False

data = json.load(open('aging_scored.json'))
info = {}
for l in open('candidates.tsv'):
    p = l.rstrip('\n').split('\t')
    info[p[0]] = [x.strip() for x in p[1:]]

aged = [r for r in data if r['score'] >= 5 and r['domain'] in info]
aged = [r for r in aged if not is_foreign(info[r['domain']][0], r['domain'])]
print('candidats score>=5 apres filtre etranger:', len(aged))

FRENCH_TLDS = {'fr', 'bzh', 'paris', 're', 'yt', 'tf', 'wf', 'pm', 'gp',
               'mq', 'gf', 'nc', 'pf', 'restaurant', 'menu', 'catering'}

def french_tld(r):
    return r['domain'].rsplit('.', 1)[-1] in FRENCH_TLDS

n_fr = sum(1 for r in aged if french_tld(r))
n_gen = len(aged) - n_fr
print(f'candidats: {n_fr} TLD francais + {n_gen} TLD generiques')

random.seed(21)
w = 10  # each french candidate is weighted above generics (french priority)
aged.sort(key=lambda r: (-r['score'] - w if french_tld(r) else -r['score'], random.random()))
picks = aged[:200]
picks.sort(key=lambda r: -r['score'])
print('selection finale:', len(picks), '| avec TLD franc:', sum(1 for r in picks if french_tld(r)))
print('score min:', picks[-1]['score'])

def yr(r):
    y = r['copyright_year']
    return y if y is not None and 1990 <= y <= 2030 else None

def pad(lst, n):
    return (list(lst) + [''] * n)[:n]

w = csv.writer(open('restaurants_vieux_200.csv', 'w', newline='', encoding='utf-8'), delimiter=';')
w.writerow(['site_web', 'nom_restaurant', 'ville', 'code_postal', 'score_anciennete',
            'non_responsive', 'sans_https', 'techno', 'copyright', 'indices_anciennete'])
for r in picks:
    i = pad(info[r['domain']], 7)
    cy = yr(r)
    w.writerow([r['url'], i[0], i[3], '', r['score'],
                'oui' if not r['responsive'] else 'non',
                'oui' if not r['https'] else 'non',
                r['generator'] or '—', cy if cy else '—',
                ' | '.join(r['reasons']) or '—'])
print('CSV ecrit avec', len(picks), 'lignes -> restaurants_vieux_200.csv')