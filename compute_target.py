import concurrent.futures as cf, urllib.request, urllib.parse, socket, json, re, os, time

socket.setdefaulttimeout(12)
UA = {'User-Agent': 'Mozilla/5.0'}
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
    for h in (CSS_HREF.findall(html) + CSS_HREF2.findall(html))[:4]:
        h = h.split('?')[0]
        if not h or h.startswith('data:') or not h.lower().endswith('.css'):
            continue
        if h.startswith('//'):
            h = 'http:' + h
        try:
            css.append(get(urllib.parse.urljoin(base, h))[1])
        except Exception:
            pass
    return '\n'.join(css)

def analyze_design(html, css):
    low = html.lower()
    signals = []
    s = 0
    n = low.count('<table')
    if n >= 3: s += 14; signals.append('layout en tableaux (%d)' % n)
    n = low.count('<font')
    if n: s += 10; signals.append('balises <font> (%d)' % n)
    if '<center>' in low: s += 5; signals.append('<center>')
    if '<marquee' in low: s += 7; signals.append('<marquee>')
    if '<blink' in low: s += 7; signals.append('<blink>')
    if 'bgcolor=' in low: s += 5; signals.append('bgcolor=')
    if '<frameset' in low: s += 10; signals.append('frameset')
    if 'doctype' not in low[:500]: s += 5; signals.append('sans doctype')
    elif 'html 4' in low[:2000] or 'xhtml 1.0 transitional' in low[:2000]: s += 4; signals.append('doctype ancien')
    if '<meta name="viewport"' not in low: s += 15; signals.append('non responsive')
    if low.count('<br') > 40: s += 3; signals.append('<br> en masse')
    if 'spacer.gif' in low or 'clear.gif' in low: s += 5; signals.append('gif de mise en page')
    if len(re.findall(r'src="[^"]+\.gif', low)) > 3: s += 3; signals.append('images .gif')
    if 'document.write' in low: s += 4; signals.append('document.write')
    if 'action="mailto:' in low: s += 5; signals.append('formulaire mailto')
    if 'webcounter' in low or 'hit counter' in low: s += 5; signals.append('compteur de visites')

    cs = 0; csig = []
    cl = css.lower()
    if css:
        if '@media' not in cl: cs += 14; csig.append('pas de @media')
        has_px = re.search(r'(?<![-\w])[0-9]+px', cl)
        has_rel = re.search(r'\brem\b|\bem\b|%', cl)
        if has_px and not has_rel: cs += 6; csig.append('px uniquement')
        if 'flex' not in cl and 'grid' not in cl: cs += 5; csig.append('pas de flex/grid')
        if '--' not in cl: cs += 3; csig.append('pas de variables CSS')
        if len(css) < 600: cs += 6; csig.append('CSS tres court (%dB)' % len(css))
        if ('times new roman' in cl or 'trebuchet' in cl or 'georgia' in cl) and 'verdana' in cl: cs += 4; csig.append('police vintage')
        if 'border-radius' not in cl and 'box-shadow' not in cl: cs += 3; csig.append('aucun radius/ombre')

    tech = 0
    g = ''
    gm = re.search(r'<meta name="generator" content="([^"]*)"', low)
    if gm: g = gm.group(1).strip()[:60]
    gl = g.lower()
    if any(x in gl for x in ('frontpage', 'dreamweaver', 'golive')):
        tech += 22; signals.append('generateur obsolete')
    elif 'joomla' in gl: tech += 12; signals.append('Joomla')
    elif 'wordpress' in gl:
        m = re.search(r'wordpress (\d+)', gl); v = int(m.group(1)) if m else 0
        if v and v <= 4: tech += 8; signals.append('WordPress %d' % v)
        elif v == 5: tech += 4; signals.append('WordPress 5')

    return {'html_s': s, 'css_s': cs, 'tech_s': tech, 'design_score': s + cs + tech,
            'generator': g, 'signals': signals, 'notables': csig}

geo = json.load(open('region_geo.json'))
DONE = 'design_target.json'
out = {}
if os.path.exists(DONE):
    out = json.load(open(DONE))
todo = [g for g in geo if g['domain'] not in out]
print("already {} / todo {}".format(len(out), len(todo)), flush=True)

save_lock = None
def work(g):
    d = g['domain']
    final, html = get('http://' + d)
    css = get_css(final, html)
    a = analyze_design(html, css)
    a['domain'] = d
    a['cp'] = g['cp']; a['dept'] = g['dept']; a['region'] = g['region']; a['tourist'] = g['tourist']
    return a

with cf.ThreadPoolExecutor(max_workers=20) as ex:
    for i, a in enumerate(ex.map(work, todo), 1):
        out[a['domain']] = a
        if i % 150 == 0:
            json.dump(out, open(DONE, 'w'), ensure_ascii=False)
            print("progress {}/{}".format(i, len(todo)), flush=True)
json.dump(out, open(DONE, 'w'), ensure_ascii=False)
print("DONE design_target={}".format(len(out)), flush=True)