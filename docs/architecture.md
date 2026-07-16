# Architecture

## Vue d'ensemble

Le projet est un pipeline en étapes successives. Chaque étape lit la sortie de la précédente, produit un résultat mesurable, et peut être rejouée indépendamment.

1. **Ingestion et validation** (`annuaire_benin.ingest`) : lecture du classeur Excel source, normalisation des téléphones et des emails à la volée, chargement dans une table SQLite unique `raw_contacts`. Chaque anomalie est qualifiée par un statut plutôt qu'écartée en silence.
2. **Déduplication** (à venir) : rapprochement des fiches désignant la même entreprise à travers les onglets (record linkage), avec un jeu de vérité annoté à la main pour mesurer précision et rappel.
3. **Classification des activités** (à venir) : passage du texte libre du champ « activité » vers une nomenclature de secteurs, avec mesure du taux d'erreur sur un échantillon annoté.
4. **Atlas économique** (à venir) : statistiques agrégées par commune, quartier et secteur, publiables car sans donnée personnelle.
5. **Recherche en langage naturel** (à venir) : interrogation de la base propre en français.

## Choix techniques

- **SQLite** comme format pivot : fichier unique, zéro dépendance serveur, requêtable par n'importe quel outil. Suffisant pour un demi-million de lignes, et remplaçable plus tard si besoin.
- **Layout `src/`** : évite les imports accidentels du dossier de travail, force l'installation en mode éditable.
- **Statuts explicites partout** : la normalisation ne retourne jamais « échec » sans dire pourquoi (`PhoneStatus`, `EmailStatus`). C'est ce qui permet de chiffrer la qualité de la source au lieu de la subir.
- **`annuaire_benin.contacts`** est conçu comme une future bibliothèque autonome : aucune dépendance vers le reste du projet, API stable, tests exhaustifs. Elle sera extraite et publiée sur PyPI une fois stabilisée.

## Normalisation des téléphones : les cas gérés

Le Bénin est passé le 30 novembre 2024 d'un plan à 8 chiffres à un plan à 10 chiffres (préfixe « 01 » ajouté à tous les numéros). La source mélange les époques et les formats :

| Cas rencontré | Exemple | Traitement | Statut |
|---|---|---|---|
| Nouveau plan complet | `0195851764` | conservé | `deja_migre` |
| Ancien plan | `95851764` | préfixe 01 ajouté | `migre` |
| Zéro de tête perdu (cellule numérique) | `195851764` | zéro restauré puis validé | `zero_restaure` |
| 8 chiffres commençant par 01 | `01970657` | non convertible sans inventer des chiffres | `suspect_01_court` |
| Indicatif pays en préfixe | `+229 95 85 17 64` | indicatif retiré puis cas ci-dessus | selon le cas |
| Plusieurs numéros par cellule | `95851764 / 97440700` | chaque numéro traité séparément | selon le cas |
| Tout le reste | `1234`, `aucun` | rejeté | `invalide` |

Le format canonique de sortie est E.164 : `+22901XXXXXXXX`.

## Règles de confidentialité

- Le fichier source et le dossier `data/` ne sont jamais commités.
- Aucune donnée personnelle (nom, téléphone, email) dans les documents, les messages de commit, les tests ou les exemples : les exemples utilisent des numéros plausibles mais non attribués et des adresses génériques.
- Seules des statistiques agrégées sont publiables.
