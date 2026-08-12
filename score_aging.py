import json, re

data = json.load(open('aging.json'))
info = {}
for l in open('candidates.tsv'):
    p = l.rstrip('\n').split('\t')
    info[p[0]] = [x.strip() for x in p[1:]]

def clean_year(r):
    y = r['copyright_year']
    return y if y is not None and 1990 <= y <= 2030 else None

for r in data:
    g = r['generator'].lower()
    score = 0
    reasons = []
    wm = re.search(r'wordpress\s+(\d+)\.(\d+)', g)
    if wm:
        major, minor = int(wm.group(1)), int(wm.group(2))
        if major < 6:
            score += 3; reasons.append("WordPress {}".format(wm.group(1)))
        elif major == 6 and minor <= 1:
            score += 2; reasons.append("WordPress {}.{} (ancien)".format(major, minor))
    if 'joomla' in g:
        score += 3; reasons.append("Joomla")
    if any(x in g for x in ('frontpage', 'dreamweaver', 'golive')):
        score += 3; reasons.append("constructeur obsolète")
    marks = [m for m in r['old_markers'] if m in ('<font>', '<center>', 'bgcolor', 'frameset')]
    if marks:
        score += 3; reasons.append("balises désuètes: " + ",".join(marks))
    if not r['responsive']:
        score += 3; reasons.append("non responsive")
    if not r['https']:
        score += 2; reasons.append("pas de HTTPS")
    y = clean_year(r)
    if y is not None and y < 2022:
        score += 2; reasons.append("copyright {}".format(y))
    r['score'] = score
    r['reasons'] = reasons

from collections import Counter
data.sort(key=lambda r: -r['score'])
print('score distribution:', Counter(r['score'] for r in data))
high = [r for r in data if r['score'] >= 5]
print('sites avec score>=5:', len(high))
json.dump(data, open('aging_scored.json', 'w'), ensure_ascii=False)