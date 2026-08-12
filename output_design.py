import json, csv

design = json.load(open('design.json'))
aging = {r['domain']: r for r in json.load(open('aging_scored.json'))}
info = {}
for l in open('candidates.tsv'):
    p = l.rstrip('\n').split('\t'); info[p[0]] = [x.strip() for x in p[1:]]

rows = []
for r in design:
    d = r['domain']
    a = aging.get(d, {})
    rows.append({
        'site_web': d,
        'nom_restaurant': info.get(d, [''])[0],
        'score_design': r['design_score'],
        'score_anciennete': r.get('anciennete', a.get('score')),
        'non_responsive': 'oui' if not a.get('responsive', True) else 'non',
        'sans_https': 'oui' if not a.get('https', True) else 'non',
        'techno': r.get('generator') or a.get('generator') or '—',
        'copyright': a.get('copyright_year') or '—',
        'html_s': r['html_s'], 'css_s': r['css_s'], 'tech_s': r['tech_s'],
        'signaux_html': ' | '.join(r.get('signals', [])) or '—',
        'signaux_css': ' | '.join(r.get('notables', [])) or '—',
    })
rows.sort(key=lambda r: -r['score_design'])

cols = ['site_web', 'nom_restaurant', 'score_design', 'score_anciennete',
        'non_responsive', 'sans_https', 'techno', 'copyright',
        'html_s', 'css_s', 'tech_s', 'signaux_html', 'signaux_css']

def write(path, subset):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(cols)
        for r in subset:
            w.writerow([r['site_web'], r['nom_restaurant'],
                        r['score_design'], r['score_anciennete'], r['non_responsive'],
                        r['sans_https'], r['techno'], r['copyright'],
                        r['html_s'], r['css_s'], r['tech_s'],
                        r['signaux_html'], r['signaux_css']])
    print('ecrit', path, len(subset))

write('restaurants_design_200.csv', rows)
write('restaurants_design_top40.csv', rows[:40])
print('--- TOP 10 design ---')
for r in rows[:10]:
    print("{:>3} | {} | {}".format(r['score_design'], r['nom_restaurant'][:34], r['site_web']))