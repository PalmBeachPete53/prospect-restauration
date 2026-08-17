"""Etape 3 : profile chaque site en ligne (anciennete + design) en une seule passe.

La v1 telechargeait la page d'accueil deux fois (scan_aging puis analyze_design).
Ici un seul fetch alimente les deux scores, plus le CSS lie.

Entree : live_v2.json   Sortie : sites_v2.json
Reprise : les domaines deja profiles sont sautes.
"""
import concurrent.futures as cf, urllib.request, urllib.parse, socket, json, re, os, time

from config_prospect import BROWSER_UA

socket.setdefaulttimeout(12)
UA = {'User-Agent': BROWSER_UA}
DONE = 'sites_v2.json'

CSS_HREF = re.compile(
    r'<link[^>]*href=["\']([^"\']+\.css[^"\']*)["\'][^>]*rel=["\']stylesheet["\']', re.I)
CSS_HREF2 = re.compile(
    r'<link[^>]*rel=["\']stylesheet["\'][^>]*href=["\']([^"\']+)["\']', re.I)


def get(url, limit=600000):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                    timeout=12) as r:
            return r.geturl(), r.read(limit).decode('utf-8', 'ignore')
    except Exception:
        return url, ''


def get_css(base, html):
    css, seen = [], set()
    for h in (CSS_HREF.findall(html) + CSS_HREF2.findall(html))[:4]:
        h = h.split('?')[0]
        if not h or h in seen:
            continue
        seen.add(h)
        if h.startswith('//'):
            h = 'http:' + h
        if h.startswith('data:') or not h.lower().endswith('.css'):
            continue
        css.append(get(urllib.parse.urljoin(base, h), 200000)[1])
    return '\n'.join(css)


def score_anciennete(low, url, generator):
    """Score d'anciennete : ce qui trahit un site qui n'a plus bouge depuis des annees."""
    score, reasons = 0, []
    g = generator.lower()
    wm = re.search(r'wordpress\s+(\d+)\.(\d+)', g)
    if wm:
        major, minor = int(wm.group(1)), int(wm.group(2))
        if major < 6:
            score += 3; reasons.append(f'WordPress {major}')
        elif major == 6 and minor <= 1:
            score += 2; reasons.append(f'WordPress {major}.{minor} (ancien)')
    if 'joomla' in g:
        score += 3; reasons.append('Joomla')
    if any(x in g for x in ('frontpage', 'dreamweaver', 'golive')):
        score += 3; reasons.append('constructeur obsolete')

    marks = [lab for sub, lab in (('<font', '<font>'), ('<center>', '<center>'),
                                  ('bgcolor=', 'bgcolor'), ('<frameset', 'frameset'))
             if sub in low]
    if marks:
        score += 3; reasons.append('balises desuetes: ' + ','.join(marks))
    if '<meta name="viewport"' not in low:
        score += 3; reasons.append('non responsive')
    if not url.startswith('https://'):
        score += 2; reasons.append('pas de HTTPS')

    years = set()
    for m in re.finditer(
            r'(?:©|&copy;|copyright)\s*[()\- ]{0,4}((?:19|20)\d{2})'
            r'\s*(?:[-–]\s*((?:19|20)\d{2}))?', low):
        years.add(int(m.group(1)))
        if m.group(2):
            years.add(int(m.group(2)))
    year = max(years) if years else None
    if year and 1990 <= year <= 2030 and year < 2022:
        score += 2; reasons.append(f'copyright {year}')
    return score, reasons, year


def score_design(low, css):
    """Score de design : a quel point le site fait visuellement date."""
    s, signals = 0, []
    n_table = low.count('<table')
    if n_table >= 3:
        s += 14; signals.append(f'layout en tableaux ({n_table})')
    n_font = low.count('<font')
    if n_font:
        s += 10; signals.append(f'balises <font> ({n_font})')
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

    cl = css.lower()
    if css:
        if '@media' not in cl:
            s += 14; signals.append('pas de @media')
        if re.search(r'(?<![-\w])[0-9]+px', cl) and not re.search(r'\brem\b|\bem\b|%', cl):
            s += 6; signals.append('px uniquement')
        if 'flex' not in cl and 'grid' not in cl:
            s += 5; signals.append('pas de flex/grid')
        if '--' not in cl:
            s += 3; signals.append('pas de variables CSS')
        if len(css) < 600:
            s += 6; signals.append(f'CSS tres court ({len(css)}B)')
        if ('times new roman' in cl or 'trebuchet' in cl or 'georgia' in cl) and 'verdana' in cl:
            s += 4; signals.append('police vintage')
        if 'border-radius' not in cl and 'box-shadow' not in cl:
            s += 3; signals.append('aucun radius/ombre')
    return s, signals


def work(item):
    d, url = item
    final_url, html = get(url)
    if not html:
        return {'domain': d, 'url': url, 'vide': True,
                'design': 0, 'anciennete': 0, 'signaux': [], 'raisons': []}
    css = get_css(final_url, html)
    low = html.lower()
    gm = re.search(r'<meta name="generator" content="([^"]*)"', low)
    generator = gm.group(1).strip()[:60] if gm else ''
    tm = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.S)
    title = ' '.join((tm.group(1) if tm else '').split())[:120]

    anc, raisons, year = score_anciennete(low, final_url, generator)
    des, signaux = score_design(low, css)
    return {
        'domain': d, 'url': final_url, 'vide': False,
        'design': des, 'anciennete': anc,
        'responsive': '<meta name="viewport"' in low,
        'https': final_url.startswith('https://'),
        'generator': generator, 'title': title, 'copyright': year,
        'signaux': signaux, 'raisons': raisons,
    }


out = []
if os.path.exists(DONE):
    out = json.load(open(DONE, encoding='utf-8'))
done = {r['domain'] for r in out}

live = json.load(open('live_v2.json', encoding='utf-8'))
todo = [(d, url) for d, url, _status in live if d not in done]
print(f'deja profile : {len(done)}, a profiler : {len(todo)}', flush=True)

start = time.time()
with cf.ThreadPoolExecutor(max_workers=20) as ex:
    for i, r in enumerate(ex.map(work, todo), 1):
        out.append(r)
        if i % 200 == 0:
            json.dump(out, open(DONE, 'w', encoding='utf-8'), ensure_ascii=False)
            print(f'{i}/{len(todo)} ({int(time.time() - start)}s)', flush=True)

json.dump(out, open(DONE, 'w', encoding='utf-8'), ensure_ascii=False)
print(f'TERMINE : {len(out)} sites profiles', flush=True)
