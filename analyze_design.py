import concurrent.futures as cf, urllib.request, urllib.parse, socket, json, re, random, time, os
import unicodedata

socket.setdefaulttimeout(12)
UA = {'User-Agent': 'Mozilla/5.0'}

def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()

FOREIGN_TOKENS = [
    'ristorante', 'trattoria', 'albergo', 'osteria', 'gasthof', 'gasthaus',
    'wirtshaus', 'staustube', 'weinstube', 'kranenturm', 'hostel', 'guesthouse',
    'bed and breakfast', 'bed & breakfast', 'b&b', 'posada', 'hostal', 'bodega',
    'de lokeend', 'brauhaus', 'brewery', 'pub restaurant',
    'unter freunden', 'eten drinken', 'ankerstube', 'movenpick',
    'zur', 'zum', 'kegelstuben', 'scholzehof', 'romkerhall', 'koenigreich',
    'in den hof', 'lisas welt', 'ochsen', 'agriturismo', 'molino',
    'restaurante', 'gasthaus',
]
LOCATION_MARKERS = [
    'koeln', 'koln', 'naumburg', 'stubbington', 'wolgen', 'moevenpick',
    'schwaben', 'wurzburg', 'hamburg', 'merklingen', 'erbacher', 'ldn',
    'london', 'mainz', 'bernau', 'gempenturm',
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

FRENCH_TAGS = {'fr', 'bzh', 'paris', 're', 'yt', 'tf', 'wf', 'pm', 'gp',
               'mq', 'gf', 'nc', 'pf', 'restaurant', 'menu', 'catering'}

# Rebuild the exact same 200-selection as write_aging_csv.py
info = {}
for l in open('candidates.tsv'):
    p = l.rstrip('\n').split('\t'); info[p[0]] = [x.strip() for x in p[1:]]

aged = [r for r in json.load(open('aging_scored.json'))
        if r['score'] >= 5 and r['domain'] in info
        and not is_foreign(info[r['domain']][0], r['domain'])]

random.seed(21)
W = 10
aged.sort(key=lambda r: (-r['score'] - W if r['domain'].rsplit('.', 1)[-1] in FRENCH_TAGS else -r['score'],
                         random.random()))
PICKS = aged[:200]
print("picks={}".format(len(PICKS)), flush=True)

CSS_HREF = re.compile(r'<link[^>]*href=["\']([^"\']+\.css[^"\']*)["\'][^>]*rel=["\']stylesheet["\']', re.I)
CSS_HREF2 = re.compile(r'<link[^>]*rel=["\']stylesheet["\'][^>]*href=["\']([^"\']+)["\']', re.I)

def get(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.geturl(), r.read(600000).decode('utf-8', 'ignore')
    except Exception:
        return url, ''

def get_css(base, html):
    css = []
    hrefs = CSS_HREF.findall(html) + CSS_HREF2.findall(html)
    seen = set()
    for h in hrefs[:4]:
        h = h.split('?')[0]
        if not h or h in seen:
            continue
        seen.add(h)
        if h.startswith('//'):
            h = 'http:' + h
        if h.startswith('data:') or not h.lower().endswith('.css'):
            continue
        full = urllib.parse.urljoin(base, h)
        try:
            css.append(get(full)[1])
        except Exception:
            pass
    return '\n'.join(css)

def analyze_design(d, url, html, css):
    low = html.lower()
    signals = []
    s = 0
    n_table = low.count('<table')
    if n_table >= 3:
        s += 14; signals.append('layout en tableaux (%d)' % n_table)
    n_font = low.count('<font')
    if n_font:
        s += 10; signals.append('balises <font> (%d)' % n_font)
    if '<center>' in low:
        s += 5; signals.append('<center>')
    if '<marquee' in low:
        s += 7; signals.append('<marquee>')
    if '<blink' in low:
        s += 7; signals.append('<blink>')
    if 'bgcolor=' in low:
        s += 5; signals.append('bgcolor=')
    if '<frameset' in low:
        s += 10; signals.append('frameset')
    if 'doctype' not in low[:500]:
        s += 5; signals.append('sans doctype')
    elif 'html 4' in low[:2000] or 'xhtml 1.0 transitional' in low[:2000]:
        s += 4; signals.append('doctype ancien')
    if '<meta name="viewport"' not in low:
        s += 15; signals.append('non responsive')
    if low.count('<br') > 40:
        s += 3; signals.append('<br> en masse')
    if 'spacer.gif' in low or 'clear.gif' in low:
        s += 5; signals.append('gif de mise en page')
    if len(re.findall(r'src="[^"]+\.gif', low)) > 3:
        s += 3; signals.append('images .gif')
    if 'document.write' in low:
        s += 4; signals.append('document.write')
    if 'action="mailto:' in low:
        s += 5; signals.append('formulaire mailto')
    if 'webcounter' in low or 'hit counter' in low:
        s += 5; signals.append('compteur de visites')

    csig = []
    cs = 0
    cl = css.lower()
    if css:
        if '@media' not in cl:
            cs += 14; csig.append('pas de @media')
        has_px = re.search(r'(?<![-\w])[0-9]+px', cl)
        has_rel = re.search(r'\brem\b|\bem\b|%', cl)
        if has_px and not has_rel:
            cs += 6; csig.append('px uniquement')
        if 'flex' not in cl and 'grid' not in cl:
            cs += 5; csig.append('pas de flex/grid')
        if '--' not in cl:
            cs += 3; csig.append('pas de variables CSS')
        if len(css) < 600:
            cs += 6; csig.append('CSS tres court (%dB)' % len(css))
        if ('times new roman' in cl or 'trebuchet' in cl or 'georgia' in cl) and 'verdana' in cl:
            cs += 4; csig.append('police vintage')
        if 'border-radius' not in cl and 'box-shadow' not in cl:
            cs += 3; csig.append('aucun radius/ombre')

    tech = 0
    g = ''
    gm = re.search(r'<meta name="generator" content="([^"]*)"', low)
    if gm:
        g = gm.group(1).strip()[:60]
    gl = g.lower()
    if any(x in gl for x in ('frontpage', 'dreamweaver', 'golive')):
        tech += 22; signals.append('generateur obsolete')
    elif 'joomla' in gl:
        tech += 12; signals.append('Joomla')
    elif 'wordpress' in gl:
        m = re.search(r'wordpress (\d+)', gl)
        v = int(m.group(1)) if m else 0
        if v and v <= 4:
            tech += 8; signals.append('WordPress %d' % v)
        elif v == 5:
            tech += 4; signals.append('WordPress 5')

    return {'html_s': s, 'css_s': cs, 'tech_s': tech, 'design_score': s + cs + tech,
            'css_size': len(css), 'generator': g, 'signals': signals,
            'notables': csig}

DONE = 'design.json'
out = []
if os.path.exists(DONE):
    out = json.load(open(DONE))
done = {r['domain'] for r in out}
todo = [p for p in PICKS if p['domain'] not in done]
print("already {} / todo {}".format(len(done), len(todo)), flush=True)

def work(p):
    d = p['domain']
    url = p.get('url') or 'http://' + d
    final_url, html = get(url)
    css = get_css(final_url, html)
    a = analyze_design(d, final_url, html, css)
    a['domain'] = d
    a['nom'] = info.get(d, [''])[0]
    a['anciennete'] = p.get('score')
    a['url'] = d
    return a

start = time.time()
with cf.ThreadPoolExecutor(max_workers=20) as ex:
    for i, a in enumerate(ex.map(work, todo), 1):
        out.append(a)
        if i % 100 == 0:
            json.dump(out, open(DONE, 'w'), ensure_ascii=False)
            print("progress {}/{}".format(i, len(todo)), flush=True)
json.dump(out, open(DONE, 'w'), ensure_ascii=False)
print("DONE design sites: {}".format(len(out)), flush=True)