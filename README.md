# prospect-locaux

Prospection de **commerces et artisans français dotés d'un site web daté** (à refondre).

---

# Campagne v2 — en cours

**Champ de recherche** : les 50 plus grosses villes de France et leur banlieue
extra-muros la plus proche. Un rayon autour de chaque centre-ville englobe la
commune et sa première couronne (Paris 25 km, Lyon/Marseille/Lille 18 km,
métropoles 12-15 km).

**Méthode** : livraison **7 par 7, 7 par niche** — soit 35 prospects à chaque
passage. Les prospects déjà livrés sont mémorisés dans `delivered.json` et ne
ressortent jamais, y compris les 60 restaurants de la campagne v1.

**Niches** (5) :

| clé | niche | ce qu'on cherche |
|---|---|---|
| `artisanat_btp` | Artisanat & BTP | plombiers, électriciens, couvreurs, jardiniers, paysagistes, constructeurs |
| `beaute_bienetre` | Beauté & Bien-être | coiffeurs, instituts d'esthétique, ongleries, centres de bien-être |
| `restauration` | Restauration | restaurants de centre-ville, food-trucks |
| `automobile` | Automobile | garages indépendants, mécaniciens, detailing |
| `services_proximite` | Services de proximité | nettoyage, réparation (dont vélo en itinérance) |

## Pipeline v2

| étape | script | sortie |
|---|---|---|
| 1 | `extract_prospects.py` | `candidates_v2.tsv` — Overpass, une requête par (ville × niche) |
| 2 | `check_live_v2.py` | `live_v2.json` — sites qui répondent |
| 3 | `scan_sites_v2.py` | `sites_v2.json` — score design + ancienneté en un seul fetch |
| 4 | `select_batch.py` | `lot_NN.csv` — les 7 suivants par niche |

Configuration commune dans `config_prospect.py` (villes, niches, filtres, taille de lot).

```bash
python extract_prospects.py && python check_live_v2.py && python scan_sites_v2.py
python select_batch.py            # livre le lot suivant
python select_batch.py --dry-run  # aperçu sans marquer comme livré
```

Les étapes 1 à 3 reprennent où elles se sont arrêtées si on les relance.
Seule l'étape 4 est à rejouer pour obtenir le lot suivant.

## Ce qui est écarté automatiquement

Les leçons de la campagne v1 sont codées dans les filtres :

- **sites tiers** — annuaires, plateformes et réseaux sociaux (Pages Jaunes,
  Planity, Doctolib, UberEats, OnaTaste…) : le pro n'a pas la main dessus ;
- **chaînes et franchises** — détectées automatiquement quand un même domaine
  porte 3 établissements ou plus (`nb_etablissements`), plus une liste des
  enseignes connues (Midas, Franck Provost, McDonald's, concessionnaires…) ;
- **doublons d'enseigne** — un même commerce présent sur deux domaines
  (`sushifirst.fr` / `sushi-first.com`) ne compte qu'une fois, y compris quand
  le premier domaine a déjà été livré lors d'un lot précédent ;
- **sites trop récents** — score de design inférieur à 10 : pas d'argumentaire.

Note technique : Overpass renvoie **HTTP 406** aux User-Agent qui imitent un
navigateur. `OVERPASS_UA` est donc descriptif, alors que la visite des sites
prospects utilise bien `BROWSER_UA`.

---

# Campagne v1 — restaurants (historique)

Restaurants au site ancien dans 3 régions touristiques. 60 prospects livrés
(`restaurants_tourisme_top40.csv` + `restaurants_tourisme_next20.csv`), repris
comme déjà démarchés par la v2.

## Livrables principaux

### `restaurants_vieux_200.csv` — 200 restaurants au site ancien
Colonnes : `site_web; nom_restaurant; ville; code_postal; score_anciennete;
non_responsive; sans_https; techno; copyright; indices_anciennete`.

- 200 lignes, chacune avec un nom de restaurant.
- 157 sites non-responsifs, 111 sans HTTPS (cibles les plus faciles pour une refonte).
- Score d'ancienneté ≥ 5.

### `restaurants_design_top40.csv` / `restaurants_design_200.csv` — design le plus "vieillot"
Classés par `score_design` décroissant (sous-scores `html_s`, `css_s`, `tech_s` :
tableaux, `<font>`, `<center>`, `bgcolor=`, `<marquee>/<blink>`, `document.write`,
absence de viewport, pas de `@media`/flex/grid, générateur FrontPage/Dreamweaver/Joomla/WP…).

### `restaurants_tourisme_top40.csv` — 40 sites vieillots ET à forte attractivité touristique (livrable final)
Version affinée : restaurants au design daté situés dans **3 régions touristiques** :
**Normandie** (plages du Débarquement, Rouen…), **Côte d'Azur** (Marseille, Verdon…)
et **Île-de-France** (Paris, Fontainebleau…). Quotas équilibrés : **14 / 13 / 13**.

Critères de sélection : `design ≥ 10` (`≥ 8` pour la Normandie afin d'atteindre son quota),
`tourisme ≥ 4` (note par département), plus double filtrage des établissements étrangers :
1. marqueurs de nom/domaine (`FOREIGN_TOKENS`, `LOCATION_MARKERS`), puis
2. **vérification du `<title>` de la page d'accueil** (`TITLE_FOREIGN` + `EXCLUDE_DOMAINS`)
   qui a éliminé des faux positifs (restaurants à Londres/`Cologne`/`Es''.pons`, sites de presse…).

Script : `select_tourisme.py` — évalue les candidats (pool de 100 dans
`restaurants_tourisme_pool.csv`), applique les quotas par région et les filtres étrangers.

### `restaurants_tourisme_next20.csv` — 20 prospects suivants (2e vague)
Même pool de 100, mêmes critères (`design`/`tourisme`/filtres étrangers), en excluant
les 40 déjà retenus dans `restaurants_tourisme_top40.csv`. Les 60 candidats restants du
pool sont classés par `score_design` puis `tourisme` décroissants ; les 20 meilleurs sont
tous en **Île-de-France** — Normandie et Côte d'Azur n'ont plus que 3-4 candidats
résiduels de score très faible (8-10) après le premier tirage.
Script : `select_tourisme_next20.py`.

## Source des données

**OpenStreetMap** (publique, licence ODbL) via l'API Overpass : requêtes
`amenity=restaurant` avec tag `website`/`contact:website`, France métropolitaine en grille
de bounding-box + découpage récursif des cellules denses/en échec.

## Pipeline

1. `extract_restaurants.py` — requêtes Overpass, normalise/dédoublonne → `candidates.tsv`.
2. `check_domains.py` — teste HTTPS puis HTTP, sites en ligne dans `live.json` (5 880).
3. `scan_aging.py` — analyse de la page d'accueil (copyright, générateur, balises désuètes,
   responsive, HTTPS) → `aging.json`.
4. `score_aging.py` — score d'ancienneté cumulé → `aging_scored.json`.
5. `write_aging_csv.py` — filtre externe, priorise les TLD français → `restaurants_vieux_200.csv`.
6. `analyze_design.py` → `output_design.py` — profilage design des 200 → CSVs design.
7. `extract_region.py` — code postal/département/région (par repérage dans le HTML, faute
   d'Overpass) sur les sites vivants → `region_geo.json` (798 localisés dans les 3 régions ciblées).
8. `compute_target.py` — score design + attractivité par département sur ces 798 → `design_target.json`.
9. `select_tourisme.py` — quotas par région + filtre externe renforcé → `restaurants_tourisme_top40.csv`.

## Fichiers intermédiaires
- `candidates.tsv`, `live.json`, `aging.json`, `aging_scored.json`,
  `region_geo.json`, `design_target.json`, `restaurants_tourisme_pool.csv`.

## Limites
- Couverture = OpenStreetMap/Overpass ; Overpass était indisponible pour la passe géograp.
  → région détectée via code postal trouvé dans le HTML (peut échouer sur sites en JS pur),
  et étrangers piéges (CP parasite sur des sites .com) corrigés par la lecture du `<title>`.
- `ville` non extraite séparément (déduite du code postal).
- `restaurants_vieux_200.csv` : `ville`/`code_postal` non renseignés (faute de coordonnées).