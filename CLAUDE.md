# annuaire-benin : conventions du projet

## Langue

- Toute la documentation, les docstrings, les commentaires et les messages de commit sont en français.
- Les identifiants de code (modules, fonctions, variables, classes) sont en anglais.
- Jamais de tiret cadratin dans les textes : virgules, deux-points, parenthèses ou tirets simples.

## Confidentialité (règle absolue)

- Le fichier source (`E:\Personnals\Prospect\Prospection_GCT.xlsx`) et le dossier `data/` ne sont JAMAIS commités.
- Aucune donnée personnelle réelle (nom d'entreprise, téléphone, email tirés de la source) dans le code, les tests, les docs, les exemples ou les messages de commit. Les exemples utilisent des valeurs fictives (numéros non attribués, domaines example.*).
- Seules des statistiques agrégées sont publiables.

## Qualité

- Chaque module a ses tests ; `pytest` doit passer avant tout commit.
- Chaque étape du pipeline produit des chiffres (statuts, taux), jamais de rejet silencieux.
- La documentation (`README.md`, `docs/`) est mise à jour dans le même commit que le code qu'elle décrit, et `docs/journal.md` reçoit une entrée par session de travail.

## Contexte

- Projet portfolio : la lisibilité du repo par un recruteur prime. Commits atomiques, messages clairs, README qui raconte le problème avant la solution.
- Le sous-paquet `annuaire_benin.contacts` est destiné à être extrait en bibliothèque PyPI autonome : ne pas y introduire de dépendance vers le reste du projet.
- Étapes du pipeline : 1 ingestion/validation (fait), 2 déduplication, 3 classification des activités, 4 atlas économique, 5 recherche en langage naturel.
