---
name: verification-prospects
description: Pipeline et méthodologie complète de la campagne de prospection commerciale (sites web dégueu) — génération de lots, vérification manuelle des prospects (fermeture, doublon, visibilité SERP, chaîne, association, distance, catégorie, domaine détourné) et remplacement des prospects disqualifiés. Use when: vérifier un lot déjà livré, remplacer des prospects disqualifiés, comprendre ou relancer le pipeline candidates_v2/select_batch, ajouter aux listes de blacklist, livrer un nouveau lot.
---

# Prospection commerciale — sites web à refaire

## Contexte

Campagne v2 : prospects avec un site web visuellement dégueu (indéfendable),
répartis en 5 niches, livrés par lots de 35 (7 par niche), sur toute la
France (grandes villes + communes attractives). Objectif : 20 lots (700
prospects). Distinct de la campagne v1 (restaurants uniquement — fichiers
`*aging*`, `*_tourisme*`, `candidates.tsv` sans suffixe `_v2` : legacy, ne
pas relancer).

État actuel : `delivered.json` fait foi pour le numéro de lot en cours et
la liste cumulative de tous les domaines déjà livrés (jamais réutilisés).

## Les 5 niches

`artisanat_btp`, `beaute_bienetre`, `restauration`, `automobile`,
`services_proximite` — définies dans `config_prospect.py` (`NICHES`), avec
leurs clés OSM (`craft=`, `shop=`, `amenity=`, `leisure=`).

## Pipeline v2 — étapes numérotées

1. **`extract_prospects.py`** — collecte les commerces avec site web par
   (ville, clé OSM) via Overpass. Sortie : `candidates_v2.tsv` (domaine,
   nom, niche, ville, dept, nb_établissements).
2. **`check_live_v2.py`** — garde les domaines qui répondent (2 passes,
   12 fils puis 6, DNS local sature vite). Sortie : `live_v2.json`.
3. **`scan_sites_v2.py`** — profile chaque site en une passe (ancienneté +
   score de laideur design + CSS lié). Sortie : `sites_v2.json`.
4. **`select_batch.py`** — compose le lot suivant : `MIN_DESIGN=15`,
   `TAILLE_LOT=35`, `MIN_PAR_NICHE=5`, `MAX_PAR_NICHE=9` (souple depuis le
   lot 3 — la règle stricte 7/niche ne s'applique qu'aux lots 1-2 déjà
   figés). Dédoublonne par racine de domaine et par (nom, ville). Met à
   jour `delivered.json`. Sortie : `lot_NN.csv`.
5. **`export_xlsx.py`** — met en forme `lot_NN.csv` en `lot_NN.xlsx`
   (5 feuilles, une par niche).

## Scripts de maintenance (ponctuels, pas dans la boucle principale)

- **`fetch_cities.py`** — liste des grandes villes depuis OSM (rayon selon
  population) → à coller dans `config_prospect.py` (`GRANDES_VILLES`).
- **`fetch_attractives.py`** — résout les communes touristiques/attractives
  (littoral, montagne, villes d'eaux) en coordonnées → `attractives_generated.py`
  (`ATTRACTIVES`, rayon 4 km — pas de banlieue pour ces communes-là).
- **`check_depts.py`** — relit l'adresse affichée sur chaque site pour
  retrouver la vraie commune (la colonne "ville" n'est que le centre de
  recherche). Sortie : `_depts.json` (corrections + muets).
- **`ajoute_communes.py`** — applique `_depts.json` aux lots déjà livrés
  (colonne `commune`), sans jamais rien écraser ni deviner.
- **`check_chaines.py`** — repère les chaînes que le comptage OSM
  (`MAX_ETABLISSEMENTS=3`) laisse passer, en lisant le texte du site
  ("nos salons", "notre réseau", "19 pressings"...). Sortie : `_chaines.json`,
  à trancher à la main.
- **`remplace_eloignes.py FICHIERS...`** — remplace dans des lots déjà
  livrés (passés en argument, jamais tous par défaut) les prospects trop
  loin de leur ville-étiquette. `RAYON_MAX=22.0` km. Un remplacement retiré
  est ajouté définitivement à `delivered.json` (jamais rendu au vivier —
  bug historique "Poilane" : un domaine réintégré au pool était ressorti
  identique au lot suivant). `coord_cp(cp, nom_lu)` désambiguïse un code
  postal partagé par plusieurs communes en préférant le nom lu sur la page.

## Fichiers de données

- `candidates_v2.tsv` — pool source (TSV : domaine, nom, niche, ville, dept, nb_étab).
- `sites_v2.json` — score par domaine (`design`, `anciennete`, `responsive`,
  `https`, `generator`, `signaux`, `vide`).
- `delivered.json` — `{lot: N, domaines: [...]}`. Source de vérité pour la
  déduplication inter-lots. Toujours mettre à jour après un remplacement.
- `config_prospect.py` — seuils, `GRANDES_VILLES`, `ATTRACTIVES`,
  `SOCIAL_AND_DIRECTORY` (annuaires à ignorer), `NOT_QUALIFIED_DOMAINS` et
  `CHAIN_DOMAINS` (blacklists persistantes), `is_chain()`, `is_directory()`,
  `not_qualified()`.
- `lot_NN.csv` / `lot_NN.xlsx` — livrables, copiés vers
  `C:\Users\esteb\OneDrive\Documents\` après chaque correction.

---

## Méthodologie de vérification manuelle (12 critères)

Le pipeline automatique (score design + comptage OSM) ne détecte ni les
doublons de site, ni la visibilité Google, ni les fermetures, ni beaucoup
de chaînes. Chaque prospect livré doit être vérifié **un par un via Claude
dans Chrome** (navigateur réel, jamais le navigateur sandboxé — il faut des
résultats Google actuels) contre ces 12 critères avant d'être accepté :

1. **Site vivant** — pas d'erreur, pas de "en construction", pas de
   placeholder d'un constructeur de site jamais publié (ex. WebSelf).

2. **Pas de doublon réel** — chercher "nom + ville" (ou coordonnées/téléphone
   si ambigu) : aucun autre domaine actif ne doit représenter la même
   entreprise. Motif récurrent à tester systématiquement : suffixe `-lpa.fr`
   (agence Effilab, vu 4 fois). Les annuaires (Pages Jaunes, Mappy, 118712,
   Societe.com, Pappers, Facebook, Instagram, Tripadvisor...) et les pages
   scraper "réclamez ce site" ne comptent jamais comme doublon.

3. **Absence des résultats organiques Google** pour "métier générique +
   ville" (ex. "plombier Toulouse") — seul le lien bleu organique
   disqualifie, **jamais** le pack local Maps (n'importe quel commerce avec
   une fiche Google gratuite y apparaît, indépendamment de la qualité du site).

4. **Pas définitivement fermé** — recherche directe sur Google Maps
   (`https://www.google.com/maps/search/<nom>+<ville>`, bien plus rapide et
   fiable que la recherche web classique) : statut "Définitivement fermé"
   ou non, avis récents ou non. Si Maps est muet/vieux, croiser avec le
   registre officiel (`annuaire-entreprises.data.gouv.fr` ou Societe.com :
   "EN ACTIVITÉ" vs "Radiée"/liquidation judiciaire) — le registre officiel
   fait foi, pas des avis Google qui dorment depuis des années.

5. **Indépendant, pas une chaîne** — même 2-3 adresses sous la même enseigne
   disqualifient (vu jusqu'à des petits groupes locaux de 3 entités liées),
   tout comme un concessionnaire/distributeur de marque officiel (Toyota,
   Xerox, Harley-Davidson...). **Distinction importante** : l'adhésion à un
   réseau fournisseur ou d'assurance qui laisse le commerce garder son
   propre nom (Bosch Car Service, Eurorepar Car Service, CARFLEX,
   ZeCarrossery) n'est **pas** disqualifiante — c'est de la certification,
   pas une chaîne. Ce qui disqualifie, c'est le même nom d'enseigne répété
   à plusieurs adresses indépendantes.

6. **Pas une association** — loi 1901, atelier solidaire/bénévole, café
   associatif militant : peu importe le tag OSM commercial, si l'activité
   est bénévole ce n'est pas un prospect commercial.

7. **Distance ≤ 22 km** du centre-ville étiqueté (`RAYON_MAX` dans
   `remplace_eloignes.py`) — croiser via `geo.api.gouv.fr` en désambiguïsant
   par le nom réel de la commune (un code postal peut couvrir plusieurs
   communes ; ne jamais prendre le premier résultat API sans vérifier le nom
   — bug trouvé et corrigé dans `coord_cp()`).

8. **Bonne catégorie** — OSM mécatégorise parfois (un peintre plasticien
   taggé "Artisanat & BTP", un arboriste-sculpteur, un fabricant B2B de
   triporteurs taggé "vélo", un château viticole taggé "restauration", un
   site d'association de commerçants de village taggé sur un commerce
   précis). Vérifier que l'activité réelle correspond à la niche assignée.

9. **Domaine non détourné** — vérifier que le domaine représente toujours
   la même entreprise : pas de redirection vers une autre entreprise
   (rachat/rebranding), une page marketing générique de créateur de sites,
   un agrégateur d'annonces, ou pire un réseau publicitaire suspect
   (domaine expiré squatté).

10. **Pas manifestement moderne/professionnel** — si le site est
    visiblement récent (réservation en ligne, bandeau cookies RGPD soigné,
    refonte revendiquée par une agence en portfolio), ça contredit la
    prémisse "site dégueu" même si le score automatique dit le contraire.

11. **Bonne échelle** — pas un domaine événementiel/hôtelier de plusieurs
    hectares faussement catégorisé "restaurant", pas une marque nationale
    avec e-commerce et réseau de distribution faussement catégorisée
    "salon local".

12. **Pas d'instabilité financière visible** — menace de liquidation
    judiciaire relayée par la presse locale (même sans fermeture actée à
    ce jour) : trop risqué à recommander, même si techniquement encore ouvert.

## Processus concret pour vérifier/remplacer un lot déjà livré

1. Lire `lot_NN.csv`, lister les 35 domaines.
2. Ouvrir un fichier de suivi dans le scratchpad (`verif_lotNN.txt`) : logger
   chaque domaine testé avec son verdict et sa raison précise, pour ne
   jamais retester deux fois le même domaine dans la même passe.
3. Passer chaque domaine par les 12 critères ci-dessus (le check Maps du
   critère 4 est le plus rapide — le faire en premier permet d'éliminer vite
   les cas évidents avant les recherches plus longues).
4. Pour chaque prospect disqualifié : chercher un remplaçant dans le même
   pool (`candidates_v2.tsv` + `sites_v2.json`, filtré par
   `not_qualified()`/`is_chain()`/`is_directory()`, niche identique,
   design ≥ 15, non déjà dans `delivered.json`, non déjà utilisé dans le lot),
   puis **revérifier le remplaçant contre les 12 mêmes critères** avant de
   l'accepter — ne jamais substituer sans revérifier, sous peine de
   réintroduire le même défaut.
5. Écrire un script de remplacement ponctuel (`REMPLACEMENTS = {ancien:
   nouveau}`, relit `candidates_v2.tsv`/`sites_v2.json` pour les métadonnées,
   réécrit `lot_NN.csv` en place) — supprimer le script après usage, il est
   spécifique à cette passe.
6. Remplir la colonne `commune` pour les nouveaux domaines dont l'adresse
   réelle diffère de la ville-étiquette (format `Commune (CP)`), puis
   relancer `python remplace_eloignes.py --dry-run lot_NN.csv` pour
   confirmer qu'aucun prospect n'est au-delà de 22 km.
7. Vérifier l'absence de doublon interne (35 domaines uniques, 7 par niche)
   et l'absence de conflit avec `delivered.json`.
8. Régénérer le xlsx (`python export_xlsx.py lot_NN.csv`).

## Persistance des découvertes

- Tout motif **structurel** confirmé (chaîne, association, société dissoute,
  domaine détourné/squatté, fermeture définitive) part directement dans
  `NOT_QUALIFIED_DOMAINS` ou `CHAIN_DOMAINS` (`config_prospect.py`), avec un
  commentaire expliquant pourquoi — sinon le même travail de vérification
  est refait à chaque lot futur. Un rejet pour simple visibilité SERP
  (ponctuel, peut changer dans le temps) n'a pas besoin d'être blacklisté.
- Tout domaine retiré d'un lot **et** tout nouveau domaine qui y entre
  doivent être répercutés dans `delivered.json` — sinon un domaine écarté
  peut revenir dans un lot ultérieur (bug "Poilane" déjà rencontré).

## Livraison

1. Copier `lot_NN.xlsx` vers `C:\Users\esteb\OneDrive\Documents\` (écrase la
   version précédemment livrée).
2. `git add` les fichiers modifiés (`config_prospect.py`, `delivered.json`,
   `lot_NN.csv`, `lot_NN.xlsx` — jamais les scripts de remplacement ponctuels
   s'ils ont été supprimés).
3. Commit avec un message expliquant précisément quoi et pourquoi (nombre de
   remplacements, raisons principales, découvertes notables).
4. `git push` (le déploiement se fait depuis `main`).
5. Envoyer le fichier xlsx corrigé à l'utilisateur via l'outil d'envoi de
   fichier.
