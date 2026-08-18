"""Configuration partagee de la prospection v2 : villes ciblees, niches, filtres.

Champ de recherche, en deux blocs :

  - les grandes villes, dans un rayon de 20 km autour du centre. A 25 km on
    ramassait des communes sans rapport avec la ville annoncee ; a 7 km le
    rendement s'effondrait. 20 km couvre la ville et sa banlieue, ce qui
    reste demarchable.

  - les zones attractives, dans un rayon de 4 km : littoral, stations de
    montagne, villes d'eaux et hauts lieux touristiques. Ramatuelle, Megeve,
    Deauville, Saint-Emilion. Un commerce y vit du tourisme ou d'une clientele
    aisee, et a donc de quoi payer un site. Ces communes n'ont pas de banlieue :
    au-dela de 4 km on ramasse la commune voisine sous une etiquette qui n'est
    pas la sienne. Les communes peu denses de l'interieur n'y figurent pas.

Les coordonnees viennent de geo.api.gouv.fr via fetch_attractives.py.
"""
from attractives_generated import ATTRACTIVES

# (nom, departement, lat, lon, rayon en metres)
GRANDES_VILLES = [
    ('Paris',              75, 48.8566,  2.3522, 20000),
    ('Lyon',               69, 45.7640,  4.8357, 20000),
    ('Marseille',          13, 43.2965,  5.3698, 20000),
    ('Lille',              59, 50.6292,  3.0573, 20000),
    ('Toulouse',           31, 43.6047,  1.4442, 20000),
    ('Bordeaux',           33, 44.8378, -0.5792, 20000),
    ('Nantes',             44, 47.2184, -1.5536, 20000),
    ('Nice',               6,  43.7102,  7.2620, 20000),
    ('Strasbourg',         67, 48.5734,  7.7521, 20000),
    ('Montpellier',        34, 43.6108,  3.8767, 20000),
    ('Rennes',             35, 48.1173, -1.6778, 20000),
    ('Grenoble',           38, 45.1885,  5.7245, 20000),
    ('Rouen',              76, 49.4432,  1.0999, 20000),
    ('Toulon',             83, 43.1242,  5.9280, 20000),
    ('Saint-Etienne',      42, 45.4397,  4.3872, 20000),
    ('Nancy',              54, 48.6921,  6.1844, 20000),
    ('Tours',              37, 47.3941,  0.6848, 20000),
    ('Clermont-Ferrand',   63, 45.7772,  3.0870, 20000),
    ('Reims',              51, 49.2583,  4.0317, 20000),
    ('Le Havre',           76, 49.4944,  0.1079, 20000),
    ('Dijon',              21, 47.3220,  5.0415, 20000),
    ('Angers',             49, 47.4784, -0.5632, 20000),
    ('Nimes',              30, 43.8367,  4.3601, 20000),
    ('Aix-en-Provence',    13, 43.5297,  5.4474, 20000),
    ('Le Mans',            72, 48.0061,  0.1996, 20000),
    ('Brest',              29, 48.3904, -4.4861, 20000),
    ('Amiens',             80, 49.8941,  2.2958, 20000),
    ('Limoges',            87, 45.8336,  1.2611, 20000),
    ('Metz',               57, 49.1193,  6.1757, 20000),
    ('Besancon',           25, 47.2378,  6.0241, 20000),
    ('Orleans',            45, 47.9029,  1.9093, 20000),
    ('Mulhouse',           68, 47.7508,  7.3359, 20000),
    ('Caen',               14, 49.1829, -0.3707, 20000),
    ('Perpignan',          66, 42.6887,  2.8948, 20000),
    ('Avignon',            84, 43.9493,  4.8055, 20000),
    ('Poitiers',           86, 46.5802,  0.3404, 20000),
    ('Annecy',             74, 45.8992,  6.1294, 20000),
    ('Pau',                64, 43.2951, -0.3708, 20000),
    ('La Rochelle',        17, 46.1591, -1.1520, 20000),
    ('Bayonne',            64, 43.4929, -1.4748, 20000),
    ('Valence',            26, 44.9334,  4.8924, 20000),
    ('Troyes',             10, 48.2973,  4.0744, 20000),
    ('Lorient',            56, 47.7477, -3.3660, 20000),
    ('Chambery',           73, 45.5646,  5.9178, 20000),
    ('Colmar',             68, 48.0794,  7.3585, 20000),
    ('Beziers',            34, 43.3440,  3.2159, 20000),
    ('Quimper',            29, 47.9960, -4.1024, 20000),
    ('Saint-Nazaire',      44, 47.2735, -2.2134, 20000),
    ('Dunkerque',          59, 51.0344,  2.3768, 20000),
    ('Bourges',            18, 47.0810,  2.3988, 20000),
]

# Une commune attractive peut deja figurer parmi les grandes villes (Cannes,
# Vannes, Dieppe...) : la grande ville l'emporte, avec son rayon de 20 km.
_deja = {nom for nom, *_ in GRANDES_VILLES}
CITIES = GRANDES_VILLES + [v for v in ATTRACTIVES if v[0] not in _deja]

# niche -> (libelle, selecteurs OpenStreetMap)
#
# Les selecteurs font le rendement : a 7 km de rayon, une niche etroite ne
# ramene presque rien. La restauration se limitait a restaurant + fast_food,
# ce qui laissait de cote les cafes, bars et brasseries - l'essentiel du
# commerce d'une station balneaire.
NICHES = {
    'artisanat_btp': (
        'Artisanat & BTP',
        [('craft', 'plumber'), ('craft', 'electrician'), ('craft', 'roofer'),
         ('craft', 'gardener'), ('craft', 'carpenter'), ('craft', 'builder'),
         ('craft', 'hvac'), ('craft', 'painter'), ('craft', 'tiler'),
         ('craft', 'stonemason'), ('craft', 'window_construction'),
         ('craft', 'scaffolder'), ('craft', 'insulation'), ('craft', 'plasterer'),
         ('craft', 'metal_construction'), ('craft', 'joiner'),
         ('craft', 'glaziery'), ('craft', 'floorer'), ('craft', 'chimney_sweeper'),
         ('craft', 'parquet_layer'), ('craft', 'sun_protection'),
         ('craft', 'handicraft'), ('craft', 'blacksmith'), ('craft', 'sawmiller'),
         ('craft', 'pest_control'), ('craft', 'well_drilling'),
         ('shop', 'doityourself'), ('shop', 'trade')],
    ),
    'beaute_bienetre': (
        'Beaute & Bien-etre',
        [('shop', 'hairdresser'), ('shop', 'beauty'), ('shop', 'massage'),
         ('leisure', 'spa'), ('shop', 'nail_salon'), ('shop', 'herbalist'),
         ('shop', 'cosmetics'), ('shop', 'perfumery'), ('shop', 'tattoo'),
         ('shop', 'hairdresser_supply'), ('amenity', 'public_bath'),
         ('leisure', 'sauna'), ('shop', 'optician')],
    ),
    'restauration': (
        'Restauration',
        [('amenity', 'restaurant'), ('amenity', 'fast_food'),
         ('amenity', 'cafe'), ('amenity', 'bar'), ('amenity', 'pub'),
         ('amenity', 'ice_cream'), ('amenity', 'biergarten'),
         ('amenity', 'food_court'), ('shop', 'bakery'), ('shop', 'pastry'),
         ('shop', 'butcher'), ('shop', 'seafood'), ('shop', 'deli'),
         ('shop', 'confectionery'), ('shop', 'caterer'), ('craft', 'caterer'),
         ('shop', 'wine'), ('shop', 'cheese')],
    ),
    'automobile': (
        'Automobile',
        [('shop', 'car_repair'), ('shop', 'tyres'), ('shop', 'car_parts'),
         ('amenity', 'car_wash'), ('shop', 'car_wash'),
         ('shop', 'motorcycle_repair'), ('shop', 'car'), ('shop', 'motorcycle'),
         ('shop', 'caravan'), ('shop', 'truck'), ('shop', 'boat'),
         ('shop', 'motorcycle_parts'), ('amenity', 'vehicle_inspection'),
         ('shop', 'agrarian')],
    ),
    'services_proximite': (
        'Services de proximite',
        [('shop', 'laundry'), ('shop', 'dry_cleaning'), ('craft', 'cleaning'),
         ('shop', 'bicycle'), ('craft', 'shoemaker'),
         ('craft', 'electronics_repair'), ('shop', 'repair'),
         ('craft', 'tailor'), ('shop', 'tailor'), ('craft', 'locksmith'),
         ('craft', 'key_cutter'), ('shop', 'copyshop'), ('craft', 'photographer'),
         ('shop', 'photo'), ('craft', 'upholsterer'), ('shop', 'pet_grooming'),
         ('shop', 'sewing'), ('craft', 'watchmaker'), ('shop', 'watches'),
         ('shop', 'funeral_directors'), ('shop', 'travel_agency'),
         ('shop', 'mobile_phone'), ('shop', 'computer')],
    ),
}

# nombre de prospects livres par niche a chaque passage
BATCH_SIZE = 7

# Overpass refuse les User-Agent qui imitent un navigateur (HTTP 406) :
# il faut un UA descriptif. A l'inverse, pour visiter les sites des prospects
# c'est bien un UA navigateur qu'il faut.
OVERPASS_UA = 'prospect-locaux/1.0 (prospection commerciale France)'
BROWSER_UA = 'Mozilla/5.0'

# Un domaine porte par plusieurs etablissements est une chaine ou un franchiseur :
# le gerant local n'a pas la main sur le site, ce n'est pas un prospect.
MAX_ETABLISSEMENTS = 3

# reseaux sociaux, annuaires et plateformes : ce n'est jamais le site du pro
SOCIAL_AND_DIRECTORY = (
    'facebook.com', 'fb.com', 'instagram.com', 'google.com', 'google.fr',
    'maps.google', 'yelp.com', 'tripadvisor.com', 'thefork.com', 'linkedin.com',
    'twitter.com', 'x.com', 'pinterest.com', 'foursquare.com', 'snapchat.com',
    'tiktok.com', 'youtube.com', 'pagesjaunes.fr', 'yellowpages',
    'ubereats.com', 'deliveroo.fr', 'justeat.fr', 'planity.com', 'treatwell.fr',
    'doctolib.fr', 'lafourchette.com', 'onataste.fr', 'petitscommerces.fr',
    'leboncoin.fr', 'houzz.fr', 'travaux.com', 'quotatis.fr', 'starofservice.com',
    'allogarage.fr', 'vroomly.com', 'idgarages.com', 'lespetitescantines.org',
    # plateformes croisees au lot 2 : le pro y est reference, il n'y a pas la main
    'touchnpay.fr', 'demosphere.net', 'demosphere.eu',
)

# Lecons de la premiere campagne : ce qui n'est pas un prospect qualifie.
#  - un site tiers (annuaire, reseau, plateforme) que le pro ne controle pas
#  - un etablissement rattache a un groupe/hotel, qui n'a pas la main sur son site
#  - une enseigne deja representee par un autre domaine (doublon multi-sites)
NOT_QUALIFIED_DOMAINS = {
    'niepceparis.com', 'alcazar.fr', 'lerecamier.com',
    'sushi-first.com', 'africanevasion94100.fr',
    # OSM le place a Lyon, son adresse est a Paris 15e : 392 km d'ecart.
    # Ecarte une premiere fois du lot 3, il etait revenu au lot 4 faute
    # d'etre inscrit ici - un retrait doit etre definitif.
    'max-poilane.fr',
}

# Chaines, franchises et constructeurs : le site est gere au niveau national.
# Le comptage d'etablissements par domaine en attrape la plupart tout seul ;
# cette liste couvre celles qui n'apparaissent qu'une ou deux fois.
CHAIN_DOMAINS = (
    # Groupes reperes en relisant les sites : leurs points de vente ne sont pas
    # tous dans OSM, le comptage d'etablissements ne les voyait donc pas.
    'api-france.com',              # reseau de distribution en franchise
    'attitudecoiffure-studiom.fr', # 9 salons sur 3 departements (holding)
    'batteries-energie.com',       # 7 agences
    'alizes-pressing.fr',          # 19 pressings, 3 regions
    'coiff1rst.com',               # groupe de salons parisiens
    # automobile
    'midas.fr', 'norauto.fr', 'feuvert.fr', 'speedy.fr', 'euromaster.',
    'roady.fr', 'vulco.com', 'point-s.fr', 'adaparts.', 'renault.fr',
    'peugeot.fr', 'citroen.fr', 'dacia.fr', 'toyota.fr', 'volkswagen.fr',
    'ford.fr', 'opel.fr', 'kia.com', 'hyundai.fr', 'nissan.fr', 'bmw.fr',
    'mercedes-benz.fr', 'audi.fr', 'fiat.fr', 'carglass.fr', 'mondialparebrise.fr',
    # beaute
    'franckprovost.com', 'jeanlouisdavid.com', 'dessange.com', 'camillealbane.com',
    'saintalgue.com', 'tchip.fr', 'bodyminute.com', 'yvesrocher.fr',
    'marionnaud.fr', 'nocibe.fr', 'sephora.fr', 'coiff-idis.',
    # restauration
    'mcdonalds.fr', 'burgerking.fr', 'kfc.fr', 'subway.', 'dominos.fr',
    'quick.fr', 'buffalo-grill.fr', 'flunch.fr', 'courtepaille.com',
    'delarte.fr', 'pizzahut.fr', 'paul.fr', 'briochedoree.fr', 'class-croute.com',
    'starbucks.fr', 'columbuscafe.com', 'bagelstein.com', 'pitaya.fr',
    'sushishop.fr', 'planetsushi.fr', 'bchef.fr', 'labrioche.fr',
    # services / btp
    '5asec.com', 'baptiste-pressing.', 'mondialrelay.fr', 'darty.com',
    'boulanger.com', 'fnac.com', 'leroymerlin.fr', 'castorama.fr',
    'brico-depot.fr', 'pointp.fr', 'saint-gobain.',
)


def is_directory(domain):
    d = (domain or '').lower()
    return any(b in d for b in SOCIAL_AND_DIRECTORY)


def is_chain(domain):
    d = (domain or '').lower()
    return any(c in d for c in CHAIN_DOMAINS)


def not_qualified(domain):
    d = (domain or '').lower()
    return d in NOT_QUALIFIED_DOMAINS or is_directory(d) or is_chain(d)
