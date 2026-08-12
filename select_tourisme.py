import json, csv, unicodedata, re, urllib.request, concurrent.futures as cf

# locations/markets in titles that reveal a site is NOT in the French target regions
TITLE_FOREIGN = [
    r'weil am rhein', r'\bkoeln\b', r'\bkoln\b', r'\bköln\b', r'\bberlin\b',
    r'\bschweiz\b|switzerland', r'\bmunchen\b|münchen', r'\bhamburg\b', r'\blondon\b',
    r'castelldefels', r'\bginesta\b', r'\bbarcelona\b', r'\bspain\b|spanien', r'\balt hall\b|gaststube',
    r'rustikales restaurant', r'weg am rhein', r'london\b',
    r'diari digital', r'molins de rei', r'nieuws|actualit\w+\b', r'\bgaststube\b',
    r'clerkenwell',
]

# hand-verified non-restaurants / foreign sites that the name+domain filter missed
EXCLUDE_DOMAINS = {'viumolinsderei.com', 'agrology.fr'}

# region-specific design floor (Normandie slightly relaxed to reach its quota)
MIN_DESIGN = {'Normandie': 8}

def title_flag(title):
    t = (title or '').lower()
    return any(re.search(p, t) for p in TITLE_FOREIGN)

def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()

FOREIGN_TOKENS = [
    'ristorante', 'trattoria', 'albergo', 'osteria', 'gasthof', 'gasthaus',
    'wirtshaus', 'staustube', 'weinstube', 'kranenturm', 'hostel', 'guesthouse',
    'bed and breakfast', 'bed & breakfast', 'b&b', 'posada', 'hostal', 'bodega',
    'de lokeend', 'brauhaus', 'brewery', 'unter freunden', 'eten drinken',
    'ankerstube', 'movenpick', 'zur', 'zum', 'kegelstuben', 'romkerhall',
    'koenigreich', 'in den hof', 'lisas welt', 'ochsen', 'agriturismo', 'molino',
    'restaurante', 'ruehrberger', 'freihof', 'gufel', 'knonau',
]
LOCATION_MARKERS = [
    'koeln', 'koln', 'naumburg', 'stubbington', 'wolgen', 'moevenpick',
    'schwaben', 'wurzburg', 'hamburg', 'merklingen', 'erbacher', 'ldn',
    'london', 'mainz', 'bernau', 'gempenturm', 'viverone', 'adrian', 'tarantani',
    'ruehrbergerhoe', 'knonaurestaurant',
]
def is_foreign(name, domain):
    nm = norm(name); d = norm(domain)
    compact = re.sub(r'[^a-z0-9]', '', nm + d)
    for t in FOREIGN_TOKENS:
        if re.sub(r'[^a-z0-9]', '', t) in compact:
            return True
    for m in LOCATION_MARKERS:
        if m in (nm + ' ' + d) or re.sub(r'[^a-z0-9]', '', m) in compact:
            return True
    return False

design = json.load(open('design_target.json'))
aging = {r['domain']: r for r in json.load(open('aging_scored.json'))}
info = {}
for l in open('candidates.tsv'):
    p = l.rstrip('\n').split('\t'); info[p[0]] = [x.strip() for x in p[1:]]

def enrich(d):
    a = design[d]
    g = aging.get(d, {})
    return {
        'site_web': d,
        'nom': info.get(d, [''])[0],
        'region': a['region'],
        'dept': a['dept'],
        'cp': a['cp'],
        'design': a['design_score'],
        'tourisme': a['tourist'],
        'anciennete': g.get('score', ''),
        'non_responsif': 'oui' if not g.get('responsive', True) else 'non',
        'sans_https': 'oui' if not g.get('https', True) else 'non',
        'techno': a.get('generator') or g.get('generator') or '—',
        'sign': ' | '.join(a.get('signals', []) + a.get('notables', [])) or '—',
    }

allrows = [
    enrich(d) for d in design
    if design[d]['tourist'] >= 4 and design[d]['design_score'] >= MIN_DESIGN.get(design[d]['region'], 10)
    and not is_foreign(info.get(d, [''])[0], d)
]

# best-effort title check: drop sites whose homepage reveals a foreign market
# or a location outside the French target regions (bandhbuildings, Medusa Desnuda…)
def fetch_title(d):
    try:
        h = urllib.request.urlopen(
            urllib.request.Request('http://' + d, headers={'User-Agent': 'Mozilla/5.0'}),
            timeout=10).read().decode('utf-8', 'ignore')
        m = re.search(r'<title>(.*?)</title>', h, re.I | re.S)
        return ' '.join((m.group(1) if m else '').split())
    except Exception:
        return ''

CACHE = {}
def clean(row):
    d = row['site_web']
    if d in EXCLUDE_DOMAINS:
        return None
    if d not in CACHE:
        CACHE[d] = fetch_title(d)
    return None if title_flag(CACHE[d]) else row

allrows = [c for c in (clean(r) for r in allrows) if c]

byregion = {}
for r in allrows:
    byregion.setdefault(r['region'], []).append(r)
for r in byregion:
    byregion[r].sort(key=lambda x: (-x['design'], -x['tourisme']))

# balanced quotas so all three tourist regions are well represented
QUOTAS = {'Normandie': 13, "Cote d'Azur": 13, 'Ile-de-France': 14}
picks = []
for r in byregion:
    picks.extend(byregion[r][:QUOTAS.get(r, 0)])
picks = picks[:40]
picks.sort(key=lambda x: (-x['design'], -x['tourisme'], x['region']))

print('selection:', len(picks), '| regions:',
      {r: sum(1 for p in picks if p['region'] == r) for r in byregion})
print('score design min/max:', min(p['design'] for p in picks), '/', max(p['design'] for p in picks))

cols = ['site_web', 'nom', 'region', 'dept', 'cp', 'design', 'tourisme',
        'anciennete', 'non_responsif', 'sans_https', 'techno', 'signaux_design']

def wcsv(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(cols)
        for r in rows:
            w.writerow([r['site_web'], r['nom'], r['region'], r['dept'], r['cp'],
                        r['design'], r['tourisme'], r['anciennete'], r['non_responsif'],
                        r['sans_https'], r['techno'], r['sign']])
    print('ecrit', path, len(rows))

allrows.sort(key=lambda x: (-x['design'], -x['tourisme']))
wcsv('restaurants_tourisme_pool.csv', allrows)
wcsv('restaurants_tourisme_top40.csv', picks)
for i, r in enumerate(picks, 1):
    print("{:>2} | {:<3} | {:<20} | {}".format(i, r['design'], r['nom'][:18], r['site_web']))