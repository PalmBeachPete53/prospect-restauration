"""Resout les communes des zones attractives en coordonnees officielles.

Zone attractive : une commune qui vit du tourisme ou d'une clientele aisee, et
dont les commerces ont donc de quoi payer un site. Trois familles ici - le
littoral, la montagne (stations de ski, lacs alpins), et les villes d'eaux et
hauts lieux touristiques. Les communes peu denses de l'interieur n'y figurent
pas : leur tissu commercial ne justifie pas la depense.

Rayon de 4 km, contre 20 km pour les grandes villes : une station balneaire ou
un village de montagne n'a pas de banlieue, et au-dela on ramasse la commune
voisine sous une etiquette qui n'est pas la sienne.

Les coordonnees ne s'inventent pas : chaque nom est resolu aupres de
geo.api.gouv.fr. Une commune introuvable ou ambigue est signalee, jamais
devinee - c'est ainsi qu'on evite de rattacher un commerce a une ville ou il
n'est pas.

Sortie : attractives_generated.py
Usage  : python fetch_attractives.py
"""
import urllib.request, urllib.parse, json, time
import concurrent.futures as cf

RAYON = 4000

# (nom, code departement) - le departement leve l'ambiguite entre homonymes
COMMUNES = [
    # ================= LITTORAL =================
    # -- Cote d'Azur --
    ('Antibes', '06'), ('Cannes', '06'), ('Menton', '06'),
    ('Villefranche-sur-Mer', '06'), ('Beaulieu-sur-Mer', '06'),
    ('Saint-Jean-Cap-Ferrat', '06'), ('Cagnes-sur-Mer', '06'),
    ('Mandelieu-la-Napoule', '06'), ('Roquebrune-Cap-Martin', '06'),
    ('Le Cannet', '06'), ('Vallauris', '06'), ('Saint-Laurent-du-Var', '06'),
    ('Théoule-sur-Mer', '06'), ('Èze', '06'), ('Cap-d\'Ail', '06'),
    ('Villeneuve-Loubet', '06'), 
    # -- Var --
    ('Saint-Tropez', '83'), ('Ramatuelle', '83'), ('Sainte-Maxime', '83'),
    ('Saint-Raphaël', '83'), ('Fréjus', '83'), ('Le Lavandou', '83'),
    ('Bandol', '83'), ('Sanary-sur-Mer', '83'), ('Cavalaire-sur-Mer', '83'),
    ('Bormes-les-Mimosas', '83'), ('Hyères', '83'), ('Six-Fours-les-Plages', '83'),
    ('La Seyne-sur-Mer', '83'), ('Cogolin', '83'), ('Grimaud', '83'),
    ('Saint-Cyr-sur-Mer', '83'), ('Le Pradet', '83'), ('Carqueiranne', '83'),
    ('Saint-Mandrier-sur-Mer', '83'), ('La Croix-Valmer', '83'),
    ('Gassin', '83'), ('Roquebrune-sur-Argens', '83'),
    # -- Bouches-du-Rhone --
    ('Cassis', '13'), ('La Ciotat', '13'), ('Sausset-les-Pins', '13'),
    ('Martigues', '13'), ('Saintes-Maries-de-la-Mer', '13'),
    ('Carry-le-Rouet', '13'), ('Istres', '13'),
    # -- Occitanie --
    ('Sète', '34'), ('Agde', '34'), ('La Grande-Motte', '34'),
    ('Palavas-les-Flots', '34'), ('Frontignan', '34'), ('Marseillan', '34'),
    ('Valras-Plage', '34'), ('Vias', '34'), ('Portiragnes', '34'),
    ('Le Grau-du-Roi', '30'), ('Gruissan', '11'), ('Narbonne', '11'),
    ('Leucate', '11'), ('Port-la-Nouvelle', '11'),
    ('Collioure', '66'), ('Argelès-sur-Mer', '66'), ('Canet-en-Roussillon', '66'),
    ('Banyuls-sur-Mer', '66'), ('Saint-Cyprien', '66'), ('Le Barcarès', '66'),
    ('Torreilles', '66'), ('Sainte-Marie-la-Mer', '66'), ('Port-Vendres', '66'),
    # -- Pays basque et Landes --
    ('Biarritz', '64'), ('Saint-Jean-de-Luz', '64'), ('Anglet', '64'),
    ('Hendaye', '64'), ('Bidart', '64'), ('Ciboure', '64'), ('Guéthary', '64'),
    ('Soorts-Hossegor', '40'), ('Capbreton', '40'), ('Mimizan', '40'),
    ('Biscarrosse', '40'), ('Vieux-Boucau-les-Bains', '40'), ('Seignosse', '40'),
    ('Moliets-et-Maa', '40'), ('Ondres', '40'), ('Tarnos', '40'),
    ('Saint-Vincent-de-Tyrosse', '40'), ('Messanges', '40'),
    # -- Gironde --
    ('Arcachon', '33'), ('La Teste-de-Buch', '33'), ('Lège-Cap-Ferret', '33'),
    ('Andernos-les-Bains', '33'), ('Lacanau', '33'), ('Gujan-Mestras', '33'),
    ('Soulac-sur-Mer', '33'), ('Carcans', '33'), ('Hourtin', '33'),
    ('Le Porge', '33'), ('Arès', '33'), ('Biganos', '33'),
    # -- Charente-Maritime --
    ('Royan', '17'), ('Saint-Palais-sur-Mer', '17'), ('Châtelaillon-Plage', '17'),
    ('Saint-Martin-de-Ré', '17'), ('La Flotte', '17'), ('Fouras', '17'),
    ('Rivedoux-Plage', '17'), ('Sainte-Marie-de-Ré', '17'),
    ('Le Bois-Plage-en-Ré', '17'), ('Ars-en-Ré', '17'), ('La Couarde-sur-Mer', '17'),
    ('Saint-Pierre-d\'Oléron', '17'), ('Le Château-d\'Oléron', '17'),
    ('Dolus-d\'Oléron', '17'), ('Saint-Trojan-les-Bains', '17'),
    ('Vaux-sur-Mer', '17'), ('Saint-Georges-de-Didonne', '17'),
    ('La Tremblade', '17'), ('Angoulins', '17'),
    # -- Vendee --
    ('Les Sables-d\'Olonne', '85'), ('Saint-Gilles-Croix-de-Vie', '85'),
    ('Saint-Jean-de-Monts', '85'), ('Noirmoutier-en-l\'Île', '85'),
    ('La Tranche-sur-Mer', '85'), ('Bretignolles-sur-Mer', '85'),
    ('Saint-Hilaire-de-Riez', '85'), ('Jard-sur-Mer', '85'),
    ('Longeville-sur-Mer', '85'), ('Notre-Dame-de-Monts', '85'),
    ('L\'Île-d\'Yeu', '85'), ('Talmont-Saint-Hilaire', '85'),
    ('Barbâtre', '85'), ('La Guérinière', '85'),
    # -- Loire-Atlantique --
    ('La Baule-Escoublac', '44'), ('Pornichet', '44'), ('Le Croisic', '44'),
    ('Pornic', '44'), ('Guérande', '44'), ('Saint-Brevin-les-Pins', '44'),
    ('Batz-sur-Mer', '44'), ('Le Pouliguen', '44'), ('La Turballe', '44'),
    ('Piriac-sur-Mer', '44'), ('Préfailles', '44'), ('La Plaine-sur-Mer', '44'),
    ('Saint-Michel-Chef-Chef', '44'), ('La Bernerie-en-Retz', '44'),
    # -- Morbihan --
    ('Carnac', '56'), ('Quiberon', '56'), ('La Trinité-sur-Mer', '56'),
    ('Vannes', '56'), ('Arzon', '56'), ('Larmor-Plage', '56'), ('Sarzeau', '56'),
    ('Damgan', '56'), ('Pénestin', '56'), ('Saint-Pierre-Quiberon', '56'),
    ('Erdeven', '56'), ('Plouharnel', '56'), ('Locmariaquer', '56'),
    ('Le Palais', '56'), ('Sauzon', '56'), ('Guidel', '56'), ('Ploemeur', '56'),
    ('Baden', '56'), ('Île-aux-Moines', '56'),
    # -- Finistere --
    ('Bénodet', '29'), ('Concarneau', '29'), ('Roscoff', '29'),
    ('Douarnenez', '29'), ('Fouesnant', '29'), ('La Forêt-Fouesnant', '29'),
    ('Crozon', '29'), ('Camaret-sur-Mer', '29'), ('Carantec', '29'),
    ('Combrit', '29'), ('Loctudy', '29'), ('Île-Tudy', '29'), ('Névez', '29'),
    ('Trégunc', '29'), ('Clohars-Carnoët', '29'), ('Plougasnou', '29'),
    ('Saint-Pol-de-Léon', '29'), ('Plouescat', '29'), ('Le Conquet', '29'),
    # -- Cotes-d'Armor --
    ('Perros-Guirec', '22'), ('Saint-Cast-le-Guildo', '22'), ('Erquy', '22'),
    ('Pléneuf-Val-André', '22'), ('Paimpol', '22'), ('Trégastel', '22'),
    ('Trébeurden', '22'), ('Pleumeur-Bodou', '22'), ('Lannion', '22'),
    ('Tréguier', '22'), ('Saint-Quay-Portrieux', '22'),
    ('Binic-Étables-sur-Mer', '22'), ('Lancieux', '22'),
    ('Saint-Jacut-de-la-Mer', '22'), ('Fréhel', '22'),
    # -- Ille-et-Vilaine --
    ('Saint-Malo', '35'), ('Dinard', '35'), ('Cancale', '35'),
    ('Saint-Lunaire', '35'), ('Saint-Briac-sur-Mer', '35'),
    ('Le Vivier-sur-Mer', '35'),
    # -- Manche --
    ('Granville', '50'), ('Barneville-Carteret', '50'),
    ('Jullouville', '50'), ('Carolles', '50'), ('Saint-Pair-sur-Mer', '50'),
    ('Agon-Coutainville', '50'), ('Saint-Vaast-la-Hougue', '50'),
    ('Barfleur', '50'), ('Port-Bail-sur-Mer', '50'),
    # -- Calvados --
    ('Deauville', '14'), ('Trouville-sur-Mer', '14'), ('Cabourg', '14'),
    ('Houlgate', '14'), ('Villers-sur-Mer', '14'), ('Ouistreham', '14'),
    ('Courseulles-sur-Mer', '14'), ('Honfleur', '14'), ('Blonville-sur-Mer', '14'),
    ('Arromanches-les-Bains', '14'), ('Port-en-Bessin-Huppain', '14'),
    ('Luc-sur-Mer', '14'), ('Lion-sur-Mer', '14'), ('Langrune-sur-Mer', '14'),
    ('Bernières-sur-Mer', '14'), ('Merville-Franceville-Plage', '14'),
    ('Dives-sur-Mer', '14'), ('Benerville-sur-Mer', '14'), ('Asnelles', '14'),
    # -- Seine-Maritime --
    ('Étretat', '76'), ('Dieppe', '76'), ('Le Tréport', '76'),
    ('Fécamp', '76'), ('Veules-les-Roses', '76'), ('Saint-Valery-en-Caux', '76'),
    ('Yport', '76'), ('Criel-sur-Mer', '76'),
    # -- Somme et Pas-de-Calais --
    ('Le Touquet-Paris-Plage', '62'), ('Wimereux', '62'), ('Berck', '62'),
    ('Neufchâtel-Hardelot', '62'), ('Wissant', '62'), ('Merlimont', '62'),
    ('Ambleteuse', '62'), ('Audresselles', '62'), ('Cucq', '62'),
    ('Le Crotoy', '80'), ('Saint-Valery-sur-Somme', '80'), ('Cayeux-sur-Mer', '80'),
    ('Fort-Mahon-Plage', '80'), ('Quend', '80'), ('Mers-les-Bains', '80'),
    ('Bray-Dunes', '59'), ('Zuydcoote', '59'),
    # -- Corse --
    ('Porto-Vecchio', '2A'), ('Bonifacio', '2A'), ('Ajaccio', '2A'),
    ('Propriano', '2A'), ('Calvi', '2B'), ('L\'Île-Rousse', '2B'),
    ('Saint-Florent', '2B'), ('Bastia', '2B'), ('Sartène', '2A'),
    ('Grosseto-Prugna', '2A'), ('Cargèse', '2A'), ('Figari', '2A'),
    ('Olmeto', '2A'), ('Lumio', '2B'), ('Algajola', '2B'),
    ('Sari-Solenzara', '2A'), ('Ghisonaccia', '2B'), ('San-Nicolao', '2B'),

    # ================= MONTAGNE =================
    # -- Haute-Savoie --
    ('Chamonix-Mont-Blanc', '74'), ('Megève', '74'), ('Morzine', '74'),
    ('Les Gets', '74'), ('La Clusaz', '74'), ('Le Grand-Bornand', '74'),
    ('Combloux', '74'), ('Saint-Gervais-les-Bains', '74'), ('Samoëns', '74'),
    ('Arâches-la-Frasse', '74'), ('Praz-sur-Arly', '74'), ('Sallanches', '74'),
    ('Cluses', '74'), ('Thonon-les-Bains', '74'), ('Évian-les-Bains', '74'),
    ('Veyrier-du-Lac', '74'), ('Sevrier', '74'), ('Talloires-Montmin', '74'),
    ('Passy', '74'), ('Abondance', '74'),
    # -- Savoie --
    ('Val-d\'Isère', '73'), ('Tignes', '73'), ('Les Allues', '73'),
    ('Courchevel', '73'), ('Les Belleville', '73'), ('Bourg-Saint-Maurice', '73'),
    ('Aime-la-Plagne', '73'), ('La Plagne Tarentaise', '73'), ('Valloire', '73'),
    ('Valmeinier', '73'), ('Saint François Longchamp', '73'),
    ('Aix-les-Bains', '73'), ('Peisey-Nancroix', '73'),
    ('Villarembert', '73'), ('Fontcouverte-la-Toussuire', '73'),
    # -- Isere / Hautes-Alpes / Alpes-de-Haute-Provence --
    ('Chamrousse', '38'), ('Huez', '38'), ('Les Deux Alpes', '38'),
    ('Villard-de-Lans', '38'), ('Autrans-Méaudre en Vercors', '38'),
    ('Briançon', '05'), ('Saint-Chaffrey', '05'), ('Montgenèvre', '05'),
    ('Vars', '05'), ('Risoul', '05'), ('Embrun', '05'), ('Gap', '05'),
    ('Barcelonnette', '04'), ('Gréoux-les-Bains', '04'), ('Digne-les-Bains', '04'),
    ('Manosque', '04'),
    # -- Pyrenees --
    ('Bagnères-de-Luchon', '31'), ('Saint-Lary-Soulan', '65'), ('Cauterets', '65'),
    ('Argelès-Gazost', '65'), ('Bagnères-de-Bigorre', '65'), ('Lourdes', '65'),
    ('Font-Romeu-Odeillo-Via', '66'), ('Ax-les-Thermes', '09'),
    ('Amélie-les-Bains-Palalda', '66'), ('Vernet-les-Bains', '66'),
    # -- Jura, Vosges, Massif central --
    ('Gérardmer', '88'), ('La Bresse', '88'), ('Les Rousses', '39'),
    ('Métabief', '25'), ('Mont-Dore', '63'), ('La Bourboule', '63'),
    ('Besse-et-Saint-Anastaise', '63'), ('Chamalières', '63'),
    ('Vittel', '88'), ('Contrexéville', '88'), ('Morteau', '25'),

    # ================= VILLES D'EAUX ET HAUTS LIEUX =================
    ('Vichy', '03'), ('Dax', '40'), ('Salies-de-Béarn', '64'),
    ('La Roche-Posay', '86'), ('Divonne-les-Bains', '01'),
    ('Beaune', '21'), ('Saint-Émilion', '33'), ('Sarlat-la-Canéda', '24'),
    ('Uzès', '30'), ('Gordes', '84'), ('Saint-Rémy-de-Provence', '13'),
    ('L\'Isle-sur-la-Sorgue', '84'), ('Lourmarin', '84'), ('Bonnieux', '84'),
    ('Ménerbes', '84'), ('Cassis', '13'), ('Menthon-Saint-Bernard', '74'),
    ('Honfleur', '14'), ('Riquewihr', '68'), ('Ribeauvillé', '68'),
    ('Kaysersberg Vignoble', '68'), ('Eguisheim', '68'), ('Obernai', '67'),
    ('Chinon', '37'), ('Amboise', '37'), ('Montrichard Val de Cher', '41'),
    ('Fontainebleau', '77'), ('Barbizon', '77'), ('Chantilly', '60'),
    ('Senlis', '60'), ('Giverny', '27'), ('Les Andelys', '27'),
    ('Saint-Paul-de-Vence', '06'), ('Mougins', '06'), ('Valbonne', '06'),
    ('Grasse', '06'), ('Biot', '06'),
]

API = 'https://geo.api.gouv.fr/communes'


def resous(item):
    nom, dept = item
    params = urllib.parse.urlencode({
        'nom': nom, 'codeDepartement': dept,
        'fields': 'nom,centre,codeDepartement,population', 'limit': 5})
    try:
        with urllib.request.urlopen(f'{API}?{params}', timeout=25) as r:
            res = json.load(r)
    except Exception as exc:
        return None, (nom, dept, f'erreur reseau : {exc}')
    if not res:
        return None, (nom, dept, 'introuvable')
    exact = [c for c in res if c['nom'].lower() == nom.lower()]
    if not exact:
        return None, (nom, dept, f"pas de correspondance (propose : {res[0]['nom']})")
    c = exact[0]
    coords = (c.get('centre') or {}).get('coordinates')
    if not coords:
        return None, (nom, dept, 'sans coordonnees')
    lon, lat = coords
    return (c['nom'], c['codeDepartement'], lat, lon,
            c.get('population') or 0), None


def main():
    vus, uniques = set(), []
    for item in COMMUNES:
        if item not in vus:
            vus.add(item)
            uniques.append(item)
    print(f'{len(uniques)} communes a resoudre ({len(COMMUNES) - len(uniques)} '
          f'doublons ecartes)', flush=True)

    ok, rates = [], []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for res, err in ex.map(resous, uniques):
            if err:
                rates.append(err)
            else:
                ok.append(res)

    # une commune peut figurer deux fois sous des orthographes differentes
    par_cle = {}
    for nom, dept, lat, lon, pop in ok:
        par_cle[(nom, dept)] = (lat, lon, pop)

    print(f'{len(par_cle)} communes resolues, {len(rates)} echecs')
    with open('attractives_generated.py', 'w', encoding='utf-8') as f:
        f.write('# genere par fetch_attractives.py - coordonnees officielles\n')
        f.write(f'# rayon {RAYON} m : ces communes n\'ont pas de banlieue\n')
        f.write('# (nom, departement, lat, lon, rayon)\n')
        f.write('ATTRACTIVES = [\n')
        for (nom, dept), (lat, lon, pop) in sorted(par_cle.items()):
            propre = nom.replace("'", "\\'")
            d = f"'{dept}'" if dept in ('2A', '2B') else int(dept)
            f.write(f"    ('{propre}', {d}, {lat:.4f}, {lon:.4f}, {RAYON}),"
                    f"  # {pop} hab.\n")
        f.write(']\n')
    print('-> attractives_generated.py')
    if rates:
        print('\nNon retenues :')
        for nom, dept, err in sorted(rates):
            print(f'  {nom} ({dept}) : {err}')


if __name__ == '__main__':
    main()
