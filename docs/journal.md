# Journal du projet

## 2026-07-16 (suite) : jeu de vérité, évaluation et calibration

- Annotation des 420 paires échantillonnées (règles explicites, voir docs/donnees.md) : 58 oui, 270 non, 92 incertain réservés à l'arbitrage humain.
- Nouveau module `dedupe/evaluate.py` : précision de la zone de fusion, rappel parmi les candidates, taux de vraies paires par bande de score.
- Verdict du premier réglage : 51,8 % de précision en zone de fusion, la moitié des fusions automatiques étaient fausses. La bande [0,80, 0,90) ne contenait que 20 % de vraies paires.
- Calibration : seuil de fusion remonté de 0,82 à 0,90 (justifié par la courbe par bande, commentaire dans scoring.py). Re-run complet : précision mesurée 82,5 %, rappel 81 %, 184 fusions appliquées, 235 176 entreprises finales.
- Les faux positifs restants sont des enseignes génériques identiques (expressions pieuses) : cible de l'étape d'arbitrage LLM, avec un jeu de test frais pour éviter le biais de calibration.

## 2026-07-16 (suite) : étape 2, déduplication (baseline)

- **2a, dédup exacte** (`dedupe/exact.py`) : 496 729 lignes regroupées en 235 360 entités en 56 s sur la clé (nom canonique, téléphone, email) ; table `entities`, chaque ligne brute reliée par `entity_id`.
- **2b, rapprochement flou baseline** :
  - `dedupe/blocking.py` : 280 377 paires candidates par trois canaux (téléphone valide, email, mot de nom rare), plafonds de taille de bloc, tout écart compté.
  - `dedupe/scoring.py` : score décomposé (similarité de noms avec cœur discriminant, contact pondéré par rareté, géographie). Double plancher de similarité de nom : jamais de fusion, ni même de zone grise, entre noms sans rapport, même à contact partagé (cas du propriétaire de plusieurs entreprises).
  - `dedupe/clustering.py` : union-find, garde-fou anti méga-cluster (jamais déclenché sur ce run, tous les clusters font 2).
  - Résultat : 351 fusions sûres, 56 729 paires en zone grise, 235 009 entreprises finales.
- Échantillon de 420 paires stratifié par zone généré dans `data/gold_pairs.csv` (privé) pour l'annotation manuelle.
- Leçon de calibration : les premiers seuils étaient réglés à l'intuition et deux tests l'ont sanctionné ; les similarités réelles ont été mesurées (rapidfuzz) avant de fixer les règles. Les seuils restent provisoires jusqu'au jeu de vérité.
- À faire : annotation du jeu de vérité, précision/rappel, calibration, arbitrage LLM de la zone grise mesuré contre le baseline.

## 2026-07-16 (suite) : publication et vitrine

- Dépôt publié sur GitHub (public) : https://github.com/abiotov/annuaire-benin, avec description et topics.
- CI GitHub Actions : ruff (lint) + pytest sur chaque push.
- Linter ruff ajouté au projet (config dans pyproject.toml), base de code conforme.
- README refondu en vitrine : chiffres clés, analyse de l'anomalie des numéros tronqués, diagramme d'architecture, roadmap, décisions de conception.

## 2026-07-16 : naissance du projet et étape 1

- Définition du projet : transformer l'annuaire brut des entreprises du Bénin (environ 235 000 fiches, 9 onglets Excel qui se recoupent) en une base propre et interrogeable, en 5 étapes mesurées (ingestion/validation, déduplication, classification des activités, atlas économique, recherche en langage naturel).
- Squelette du dépôt : layout `src/`, `pyproject.toml`, tests `pytest`, règles de confidentialité (données réelles jamais commitées).
- Étape 1 livrée :
  - `annuaire_benin.contacts.phone` : normalisation des numéros béninois vers E.164, avec prise en charge de la migration nationale de novembre 2024 (8 vers 10 chiffres), des zéros de tête perdus, des indicatifs pays et des cellules multi-numéros. Chaque échec est qualifié par un statut.
  - `annuaire_benin.contacts.emails` : validation syntaxique et normalisation des adresses.
  - `annuaire_benin.ingest` : chargement du classeur source vers SQLite (`raw_contacts`), normalisation à la volée, bilan chiffré par onglet et par statut.
- Première ingestion réelle : 496 729 lignes en 50 s. Découverte majeure : toutes les valeurs téléphone font 8 caractères, et les 109 780 numéros commençant par « 01 » sont très probablement des numéros du nouveau plan tronqués par l'export source (voir docs/donnees.md). La déduplication réduira la base à environ 235 000 entités.
