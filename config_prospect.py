"""Configuration partagee de la prospection v2 : villes ciblees, niches, filtres.

Champ de recherche : les grosses villes de France et leur banlieue extra-muros
la plus proche. Le rayon autour du centre-ville fait le travail : il englobe la
commune et la premiere couronne (ex. Paris 25 km couvre la petite couronne,
Lille 18 km couvre Roubaix/Tourcoing/Villeneuve-d'Ascq).
"""

# (nom, departement, lat, lon, rayon en metres)
CITIES = [
    ('Paris',              75, 48.8566,  2.3522, 25000),
    ('Lyon',               69, 45.7640,  4.8357, 18000),
    ('Marseille',          13, 43.2965,  5.3698, 18000),
    ('Lille',              59, 50.6292,  3.0573, 18000),
    ('Toulouse',           31, 43.6047,  1.4442, 15000),
    ('Bordeaux',           33, 44.8378, -0.5792, 15000),
    ('Nantes',             44, 47.2184, -1.5536, 15000),
    ('Nice',               6,  43.7102,  7.2620, 15000),
    ('Strasbourg',         67, 48.5734,  7.7521, 15000),
    ('Montpellier',        34, 43.6108,  3.8767, 15000),
    ('Rennes',             35, 48.1173, -1.6778, 15000),
    ('Grenoble',           38, 45.1885,  5.7245, 14000),
    ('Rouen',              76, 49.4432,  1.0999, 14000),
    ('Toulon',             83, 43.1242,  5.9280, 14000),
    ('Saint-Etienne',      42, 45.4397,  4.3872, 13000),
    ('Nancy',              54, 48.6921,  6.1844, 13000),
    ('Tours',              37, 47.3941,  0.6848, 13000),
    ('Clermont-Ferrand',   63, 45.7772,  3.0870, 13000),
    ('Reims',              51, 49.2583,  4.0317, 12000),
    ('Le Havre',           76, 49.4944,  0.1079, 12000),
    ('Dijon',              21, 47.3220,  5.0415, 12000),
    ('Angers',             49, 47.4784, -0.5632, 12000),
    ('Nimes',              30, 43.8367,  4.3601, 12000),
    ('Aix-en-Provence',    13, 43.5297,  5.4474, 12000),
    ('Le Mans',            72, 48.0061,  0.1996, 12000),
    ('Brest',              29, 48.3904, -4.4861, 12000),
    ('Amiens',             80, 49.8941,  2.2958, 12000),
    ('Limoges',            87, 45.8336,  1.2611, 12000),
    ('Metz',               57, 49.1193,  6.1757, 12000),
    ('Besancon',           25, 47.2378,  6.0241, 12000),
    ('Orleans',            45, 47.9029,  1.9093, 12000),
    ('Mulhouse',           68, 47.7508,  7.3359, 12000),
    ('Caen',               14, 49.1829, -0.3707, 12000),
    ('Perpignan',          66, 42.6887,  2.8948, 12000),
    ('Avignon',            84, 43.9493,  4.8055, 12000),
    ('Poitiers',           86, 46.5802,  0.3404, 12000),
    ('Annecy',             74, 45.8992,  6.1294, 12000),
    ('Pau',                64, 43.2951, -0.3708, 12000),
    ('La Rochelle',        17, 46.1591, -1.1520, 12000),
    ('Bayonne',            64, 43.4929, -1.4748, 12000),
    ('Valence',            26, 44.9334,  4.8924, 12000),
    ('Troyes',             10, 48.2973,  4.0744, 12000),
    ('Lorient',            56, 47.7477, -3.3660, 12000),
    ('Chambery',           73, 45.5646,  5.9178, 12000),
    ('Colmar',             68, 48.0794,  7.3585, 12000),
    ('Beziers',            34, 43.3440,  3.2159, 12000),
    ('Quimper',            29, 47.9960, -4.1024, 12000),
    ('Saint-Nazaire',      44, 47.2735, -2.2134, 12000),
    ('Dunkerque',          59, 51.0344,  2.3768, 12000),
    ('Bourges',            18, 47.0810,  2.3988, 12000),
]

# niche -> (libelle, selecteurs OpenStreetMap)
NICHES = {
    'artisanat_btp': (
        'Artisanat & BTP',
        [('craft', 'plumber'), ('craft', 'electrician'), ('craft', 'roofer'),
         ('craft', 'gardener'), ('craft', 'carpenter'), ('craft', 'builder'),
         ('craft', 'hvac'), ('craft', 'painter'), ('craft', 'tiler'),
         ('craft', 'stonemason'), ('craft', 'window_construction'),
         ('craft', 'scaffolder'), ('craft', 'insulation'), ('craft', 'plasterer'),
         ('craft', 'metal_construction'), ('craft', 'joiner')],
    ),
    'beaute_bienetre': (
        'Beaute & Bien-etre',
        [('shop', 'hairdresser'), ('shop', 'beauty'), ('shop', 'massage'),
         ('leisure', 'spa'), ('shop', 'nail_salon'), ('shop', 'herbalist')],
    ),
    'restauration': (
        'Restauration',
        [('amenity', 'restaurant'), ('amenity', 'fast_food')],
    ),
    'automobile': (
        'Automobile',
        [('shop', 'car_repair'), ('shop', 'tyres'), ('shop', 'car_parts'),
         ('amenity', 'car_wash'), ('shop', 'car_wash'),
         ('shop', 'motorcycle_repair')],
    ),
    'services_proximite': (
        'Services de proximite',
        [('shop', 'laundry'), ('shop', 'dry_cleaning'), ('craft', 'cleaning'),
         ('shop', 'bicycle'), ('craft', 'shoemaker'),
         ('craft', 'electronics_repair'), ('shop', 'repair')],
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
}

# Chaines, franchises et constructeurs : le site est gere au niveau national.
# Le comptage d'etablissements par domaine en attrape la plupart tout seul ;
# cette liste couvre celles qui n'apparaissent qu'une ou deux fois.
CHAIN_DOMAINS = (
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
