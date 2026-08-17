"""Genere la liste des villes depuis OpenStreetMap.

Les coordonnees ne s'inventent pas : on demande a Overpass toutes les communes
francaises au-dessus d'un seuil de population, avec leur centre et leur code
postal (dont on tire le departement). Sortie : cities_generated.py, a coller
dans config_prospect.py.

Le rayon est deduit de la population : une grande ville a une couronne plus
large qu'une sous-prefecture.

Usage : python fetch_cities.py [population_min]
"""
import urllib.request, urllib.parse, json, sys, re

SEUIL = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
UA = 'prospect-locaux/1.0 (prospection commerciale France)'

# area 3602202162 = France metropolitaine (relation OSM 2202162)
QUERY = f"""[out:json][timeout:180];
area(3602202162)->.fr;
(
  node["place"~"^(city|town)$"]["population"](area.fr);
  way["place"~"^(city|town)$"]["population"](area.fr);
  relation["place"~"^(city|town)$"]["population"](area.fr);
);
out center tags;"""


def rayon(pop):
    """Rayon couvrant la commune et sa premiere couronne."""
    if pop >= 1000000:
        return 25000
    if pop >= 300000:
        return 18000
    if pop >= 150000:
        return 15000
    if pop >= 80000:
        return 13000
    if pop >= 40000:
        return 12000
    return 10000


def main():
    data = urllib.parse.urlencode({'data': QUERY}).encode()
    req = urllib.request.Request('https://overpass-api.de/api/interpreter',
                                 data=data,
                                 headers={'User-Agent': UA,
                                          'Accept': 'application/json'})
    print('interrogation d\'Overpass...', flush=True)
    with urllib.request.urlopen(req, timeout=200) as r:
        payload = json.load(r)
    if payload.get('remark'):
        print('ECHEC :', payload['remark'])
        return

    villes = {}
    for e in payload.get('elements', []):
        t = e.get('tags', {})
        nom = (t.get('name') or '').strip()
        if not nom:
            continue
        pop = re.sub(r'[^0-9]', '', t.get('population', '') or '')
        if not pop or int(pop) < SEUIL:
            continue
        pop = int(pop)

        # departement : les 2 premiers chiffres du code postal, 3 en outre-mer
        cp = (t.get('addr:postcode') or t.get('postal_code') or '').strip()
        m = re.match(r'^(\d{2})\d{3}$', cp)
        if not m:
            continue
        dept = int(m.group(1))
        if dept in (97, 98):      # outre-mer : hors champ
            continue

        lat = e.get('lat') or (e.get('center') or {}).get('lat')
        lon = e.get('lon') or (e.get('center') or {}).get('lon')
        if lat is None or lon is None:
            continue

        # doublon (node + relation pour la meme commune) : on garde la plus peuplee
        cle = (nom, dept)
        if cle not in villes or villes[cle][0] < pop:
            villes[cle] = (pop, lat, lon)

    lignes = sorted(villes.items(), key=lambda kv: -kv[1][0])
    print(f'{len(lignes)} communes >= {SEUIL} habitants', flush=True)

    with open('cities_generated.py', 'w', encoding='utf-8') as f:
        f.write(f'# genere par fetch_cities.py, seuil {SEUIL} hab.\n')
        f.write('# (nom, departement, lat, lon, rayon)\n')
        f.write('CITIES = [\n')
        for (nom, dept), (pop, lat, lon) in lignes:
            propre = nom.replace("'", "\\'")
            f.write(f"    ('{propre}', {dept}, {lat:.4f}, {lon:.4f}, "
                    f"{rayon(pop)}),  # {pop}\n")
        f.write(']\n')
    print('-> cities_generated.py', flush=True)
    for (nom, dept), (pop, _la, _lo) in lignes[:10]:
        print(f'  {nom} ({dept}) {pop}')


if __name__ == '__main__':
    main()
