"""Etape 1 : interroge Overpass ville par ville et niche par niche.

Une requete par couple (ville, niche), avec un rayon autour du centre-ville qui
englobe la commune et sa premiere couronne. Sortie : candidates_v2.tsv
(domaine, nom, niche, ville, dept, url brute), dedoublonne par domaine.

Reprise possible : le fichier _raw_v2.json est relu au demarrage, les couples
deja traites sont sautes.
"""
import urllib.request, urllib.parse, json, time, re, os, sys

from config_prospect import CITIES, NICHES, OVERPASS_UA, is_directory

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]
RAW = '_raw_v2.json'
OUT = 'candidates_v2.tsv'


def build_query(selectors, lat, lon, radius):
    parts = []
    for k, v in selectors:
        for w in ('website', 'contact:website'):
            parts.append(f'nwr["{k}"="{v}"]["{w}"](around:{radius},{lat},{lon});')
    return '[out:json][timeout:180];(' + ''.join(parts) + ');out tags;'


def fetch(query):
    data = urllib.parse.urlencode({'data': query}).encode()
    headers = {'User-Agent': OVERPASS_UA, 'Accept': 'application/json'}
    for ep in ENDPOINTS:
        for attempt in range(3):
            try:
                req = urllib.request.Request(ep, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=180) as r:
                    return json.load(r)
            except Exception as exc:
                print(f'    ! {ep.split("//")[1].split("/")[0]}: {exc}', flush=True)
                time.sleep(5 + attempt * 10)
    return None


def normalize(url):
    url = (url or '').strip()
    if not url:
        return None
    if '://' not in url:
        url = 'http://' + url
    m = re.match(r'^https?://([^/:?#]+)', url)
    if not m:
        return None
    domain = m.group(1).lower().rstrip('.')
    if not re.match(r'^[a-z0-9-]+(\.[a-z0-9-]+)+$', domain):
        return None
    if domain.startswith('www.'):
        domain = domain[4:]
    if is_directory(domain):
        return None
    return domain


def main():
    # {domaine: [nom, niche, ville, dept, url_brute]}
    results = {}
    # {domaine: nb d'etablissements portant ce domaine} -> detecte les chaines
    counts = {}
    seen_pairs = set()
    if os.path.exists(RAW):
        saved = json.load(open(RAW, encoding='utf-8'))
        results = saved.get('results', {})
        counts = saved.get('counts', {})
        seen_pairs = {tuple(p) for p in saved.get('pairs', [])}
        print(f'reprise : {len(results)} domaines, {len(seen_pairs)} couples deja faits',
              flush=True)

    def save():
        json.dump({'results': results, 'counts': counts, 'pairs': sorted(seen_pairs)},
                  open(RAW, 'w', encoding='utf-8'), ensure_ascii=False)

    total_pairs = len(CITIES) * len(NICHES)
    done = 0
    for city, dept, lat, lon, radius in CITIES:
        for niche, (label, selectors) in NICHES.items():
            done += 1
            if (city, niche) in seen_pairs:
                continue
            payload = fetch(build_query(selectors, lat, lon, radius))
            if payload is None:
                print(f'[{done}/{total_pairs}] {city} / {niche}: ECHEC', flush=True)
                continue
            added = 0
            for e in payload.get('elements', []):
                tags = e.get('tags', {})
                raw = tags.get('website') or tags.get('contact:website') or ''
                dom = normalize(raw)
                if not dom:
                    continue
                counts[dom] = counts.get(dom, 0) + 1
                if dom in results:
                    continue
                name = (tags.get('name') or '').strip()
                results[dom] = [name, niche, city, str(dept), raw.strip()]
                added += 1
            seen_pairs.add((city, niche))
            print(f'[{done}/{total_pairs}] {city} / {niche}: +{added} '
                  f'(total={len(results)})', flush=True)
            save()

    save()

    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        f.write('domaine\tnom\tniche\tville\tdept\tnb_etablissements\turl_brute\n')
        for dom, row in sorted(results.items()):
            nom, niche, city, dept, raw = row
            f.write('\t'.join([dom, nom, niche, city, dept,
                               str(counts.get(dom, 1)), raw]) + '\n')

    par_niche = {}
    for row in results.values():
        par_niche[row[1]] = par_niche.get(row[1], 0) + 1
    chaines = sum(1 for d in results if counts.get(d, 1) >= 3)
    print(f'\nTOTAL {len(results)} domaines uniques -> {OUT}')
    print(f'  dont {chaines} portes par 3+ etablissements (chaines, ecartees a l\'etape 4)')
    for niche, n in sorted(par_niche.items(), key=lambda x: -x[1]):
        print(f'  {niche:<20} {n}')


if __name__ == '__main__':
    main()
