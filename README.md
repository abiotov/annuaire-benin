# annuaire-benin

Pipeline de nettoyage, de déduplication et d'exploration de l'annuaire des entreprises du Bénin : environ 235 000 fiches brutes (nom, activité en texte libre, commune, quartier, téléphone, email) transformées en une base propre, mesurée et interrogeable.

## Le problème

Les données sources proviennent de l'annuaire national des établissements et sociétés. Elles sont réelles, massives et sales :

- la même entreprise apparaît dans plusieurs onglets, avec des variantes de nom ;
- le champ « activité » est du texte libre en français, sans nomenclature ;
- les numéros de téléphone mélangent l'ancien plan à 8 chiffres et le nouveau plan à 10 chiffres (migration nationale du 30 novembre 2024), avec des zéros de tête perdus et des formats variés ;
- les emails contiennent fautes de frappe et valeurs fantaisistes.

Ce projet traite chacun de ces problèmes avec des résultats chiffrés à chaque étape.

## Architecture

```
source Excel (privée, jamais commitée)
        |
   [1] Ingestion + validation des contacts      <- src/annuaire_benin/ingest.py
        |                                          src/annuaire_benin/contacts/
   [2] Déduplication (record linkage)           <- à venir
        |
   [3] Classification des activités             <- à venir
        |
   base propre (SQLite)
        |
        +-- [4] Atlas économique (carte interactive)      <- à venir
        +-- [5] Recherche en langage naturel              <- à venir
```

Le détail des choix techniques est dans [docs/architecture.md](docs/architecture.md), le dictionnaire des données dans [docs/donnees.md](docs/donnees.md), et l'historique du projet dans [docs/journal.md](docs/journal.md).

## État d'avancement

| Étape | Statut |
|---|---|
| 1. Ingestion et validation des contacts | Fait : 496 729 lignes chargées, 100 % des contacts qualifiés, voir [docs/donnees.md](docs/donnees.md) |
| 2. Déduplication | À venir |
| 3. Classification des activités | À venir |
| 4. Atlas économique | À venir |
| 5. Recherche en langage naturel | À venir |

## Démarrage rapide

```bash
pip install -e ".[dev]"

# Lancer les tests
pytest

# Ingérer le fichier source vers SQLite
python -m annuaire_benin.ingest chemin/vers/source.xlsx --db data/annuaire.db
```

## Confidentialité des données

Les données sources contiennent des informations personnelles (emails, téléphones). Elles ne sont **jamais** commitées dans ce dépôt : le dossier `data/` est ignoré par git et le fichier source reste hors du dépôt. Seuls le code, les métriques agrégées et des échantillons synthétiques sont publiés.

## Licence

MIT.
