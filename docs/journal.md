# Journal du projet

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
