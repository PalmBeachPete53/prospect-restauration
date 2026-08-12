# prospect-restaurateurs

Prospection de **restaurants français dotés d'un site web ancien** (à refondre).
Réplique du pipeline utilisé dans `project-avocats`, appliqué au secteur de la restauration.

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