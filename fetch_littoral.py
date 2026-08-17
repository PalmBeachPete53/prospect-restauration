"""Resout les communes du littoral en coordonnees officielles.

Le champ de recherche s'elargit aux villes moyennes de bord de mer a fort
pouvoir d'achat : stations balneaires, ports de plaisance, cotes touristiques.
Les communes de l'interieur peu denses n'ont pas le tissu commercial qu'on
cherche et sont exclues d'office.

Les coordonnees ne s'inventent pas : chaque nom est resolu aupres de
geo.api.gouv.fr, qui renvoie le centre officiel, le code postal et la
population. Une commune introuvable ou ambigue est signalee, jamais devinee.

Sortie : littoral_generated.py
Usage  : python fetch_littoral.py
"""
import urllib.request, urllib.parse, json, time, sys

# Rayon serre : on veut la commune et son immediate peripherie, pas le
# departement. 7 km suffit pour une station balneaire et sa zone d'activite.
RAYON = 7000

# (nom, code departement) - le departement leve l'ambiguite entre homonymes
COMMUNES = [
    # --- Cote d'Azur / Var ---
    ('Antibes', '06'), ('Cannes', '06'), ('Menton', '06'),
    ('Villefranche-sur-Mer', '06'), ('Beaulieu-sur-Mer', '06'),
    ('Saint-Jean-Cap-Ferrat', '06'), ('Cagnes-sur-Mer', '06'),
    ('Mandelieu-la-Napoule', '06'), ('Roquebrune-Cap-Martin', '06'),
    ('Le Cannet', '06'), ('Vallauris', '06'), ('Saint-Laurent-du-Var', '06'),
    ('Saint-Tropez', '83'), ('Ramatuelle', '83'), ('Sainte-Maxime', '83'),
    ('Saint-Raphaël', '83'), ('Fréjus', '83'), ('Le Lavandou', '83'),
    ('Bandol', '83'), ('Sanary-sur-Mer', '83'), ('Cavalaire-sur-Mer', '83'),
    ('Bormes-les-Mimosas', '83'), ('Hyères', '83'), ('Six-Fours-les-Plages', '83'),
    ('La Seyne-sur-Mer', '83'), ('Cogolin', '83'), ('Grimaud', '83'),
    ('Cassis', '13'), ('La Ciotat', '13'), ('Sausset-les-Pins', '13'),
    ('Martigues', '13'), ('Saintes-Maries-de-la-Mer', '13'),
    # --- Occitanie ---
    ('Sète', '34'), ('Agde', '34'), ('La Grande-Motte', '34'),
    ('Palavas-les-Flots', '34'), ('Frontignan', '34'), ('Marseillan', '34'),
    ('Le Grau-du-Roi', '30'), ('Gruissan', '11'), ('Narbonne', '11'),
    ('Collioure', '66'), ('Argelès-sur-Mer', '66'), ('Canet-en-Roussillon', '66'),
    ('Banyuls-sur-Mer', '66'), ('Saint-Cyprien', '66'),
    # --- Nouvelle-Aquitaine ---
    ('Biarritz', '64'), ('Saint-Jean-de-Luz', '64'), ('Anglet', '64'),
    ('Hendaye', '64'), ('Bidart', '64'), ('Ciboure', '64'),
    ('Soorts-Hossegor', '40'), ('Capbreton', '40'), ('Mimizan', '40'),
    ('Biscarrosse', '40'), ('Vieux-Boucau-les-Bains', '40'),
    ('Arcachon', '33'), ('La Teste-de-Buch', '33'), ('Lège-Cap-Ferret', '33'),
    ('Andernos-les-Bains', '33'), ('Lacanau', '33'), ('Gujan-Mestras', '33'),
    ('Royan', '17'), ('Saint-Palais-sur-Mer', '17'), ('Châtelaillon-Plage', '17'),
    ('Saint-Martin-de-Ré', '17'), ('La Flotte', '17'), ('Fouras', '17'),
    # --- Pays de la Loire / Vendee ---
    ('Les Sables-d\'Olonne', '85'), ('Saint-Gilles-Croix-de-Vie', '85'),
    ('Saint-Jean-de-Monts', '85'), ('Noirmoutier-en-l\'Île', '85'),
    ('La Tranche-sur-Mer', '85'), ('Bretignolles-sur-Mer', '85'),
    ('La Baule-Escoublac', '44'), ('Pornichet', '44'), ('Le Croisic', '44'),
    ('Pornic', '44'), ('Guérande', '44'), ('Saint-Brevin-les-Pins', '44'),
    # --- Bretagne ---
    ('Saint-Malo', '35'), ('Dinard', '35'), ('Cancale', '35'),
    ('Perros-Guirec', '22'), ('Saint-Cast-le-Guildo', '22'), ('Erquy', '22'),
    ('Pléneuf-Val-André', '22'), ('Paimpol', '22'), ('Trégastel', '22'),
    ('Carnac', '56'), ('Quiberon', '56'), ('La Trinité-sur-Mer', '56'),
    ('Vannes', '56'), ('Arzon', '56'), ('Larmor-Plage', '56'), ('Sarzeau', '56'),
    ('Bénodet', '29'), ('Concarneau', '29'), ('Roscoff', '29'),
    ('Douarnenez', '29'), ('Fouesnant', '29'), ('La Forêt-Fouesnant', '29'),
    # --- Normandie ---
    ('Deauville', '14'), ('Trouville-sur-Mer', '14'), ('Cabourg', '14'),
    ('Houlgate', '14'), ('Villers-sur-Mer', '14'), ('Ouistreham', '14'),
    ('Courseulles-sur-Mer', '14'), ('Honfleur', '14'), ('Blonville-sur-Mer', '14'),
    ('Étretat', '76'), ('Dieppe', '76'), ('Le Tréport', '76'),
    ('Granville', '50'), ('Barneville-Carteret', '50'),
    # --- Hauts-de-France ---
    ('Le Touquet-Paris-Plage', '62'), ('Wimereux', '62'), ('Berck', '62'),
    ('Neufchâtel-Hardelot', '62'), ('Wissant', '62'),
    # --- Corse ---
    ('Porto-Vecchio', '2A'), ('Bonifacio', '2A'), ('Ajaccio', '2A'),
    ('Propriano', '2A'), ('Calvi', '2B'), ('L\'Île-Rousse', '2B'),
    ('Saint-Florent', '2B'), ('Bastia', '2B'),
]

API = 'https://geo.api.gouv.fr/communes'


def resous(nom, dept):
    params = urllib.parse.urlencode({
        'nom': nom, 'codeDepartement': dept,
        'fields': 'nom,centre,codesPostaux,codeDepartement,population',
        'limit': 5})
    try:
        with urllib.request.urlopen(f'{API}?{params}', timeout=20) as r:
            res = json.load(r)
    except Exception as exc:
        return None, f'erreur reseau : {exc}'
    if not res:
        return None, 'introuvable'
    # geo.api.gouv.fr classe par pertinence ; on exige une correspondance exacte
    exact = [c for c in res if c['nom'].lower() == nom.lower()]
    c = exact[0] if exact else res[0]
    if not exact:
        return None, f"pas de correspondance exacte (propose : {res[0]['nom']})"
    coords = (c.get('centre') or {}).get('coordinates')
    if not coords:
        return None, 'sans coordonnees'
    lon, lat = coords
    return (c['nom'], c['codeDepartement'], lat, lon,
            c.get('population') or 0), None


def main():
    ok, rates = [], []
    for nom, dept in COMMUNES:
        res, err = resous(nom, dept)
        if err:
            rates.append((nom, dept, err))
            print(f'  !! {nom} ({dept}) : {err}', flush=True)
        else:
            ok.append(res)
        time.sleep(0.05)

    print(f'\n{len(ok)} communes resolues, {len(rates)} echecs')
    with open('littoral_generated.py', 'w', encoding='utf-8') as f:
        f.write('# genere par fetch_littoral.py - coordonnees officielles\n')
        f.write('# (nom, departement, lat, lon, rayon)\n')
        f.write('LITTORAL = [\n')
        for nom, dept, lat, lon, pop in ok:
            propre = nom.replace("'", "\\'")
            d = dept if dept in ('2A', '2B') else int(dept)
            d = f"'{d}'" if isinstance(d, str) else d
            f.write(f"    ('{propre}', {d}, {lat:.4f}, {lon:.4f}, {RAYON}),"
                    f"  # {pop} hab.\n")
        f.write(']\n')
    print('-> littoral_generated.py')
    if rates:
        print('\nA corriger a la main :')
        for nom, dept, err in rates:
            print(f'  {nom} ({dept}) : {err}')


if __name__ == '__main__':
    main()
