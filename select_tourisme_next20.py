import csv

def read_csv(path):
    with open(path, encoding='utf-8') as f:
        r = csv.reader(f, delimiter=';')
        header = next(r)
        return header, [row for row in r]

header, pool = read_csv('restaurants_tourisme_pool.csv')
_, top40 = read_csv('restaurants_tourisme_top40.csv')

excluded = {row[0] for row in top40}

remaining = [row for row in pool if row[0] not in excluded]
remaining.sort(key=lambda r: (-int(r[5]), -int(r[6])))  # design desc, tourisme desc

next20 = remaining[:20]

with open('restaurants_tourisme_next20.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(header)
    w.writerows(next20)

print('ecrit restaurants_tourisme_next20.csv', len(next20))
print('regions:', {r for r in (row[2] for row in next20)})
for i, r in enumerate(next20, 1):
    print("{:>2} | {:<3} | {:<25} | {}".format(i, r[5], r[1][:24], r[0]))
