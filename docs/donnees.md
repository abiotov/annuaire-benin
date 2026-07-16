# Dictionnaire des données

## Source

Un classeur Excel privé (jamais commité) issu de l'annuaire national des établissements et sociétés du Bénin : 9 onglets de données partageant les mêmes 7 colonnes (nom, activité, commune, quartier, téléphone, email, segment), plus un onglet de tableau de bord ignoré à l'ingestion. Les onglets se recoupent volontairement : une même entreprise apparaît dans plusieurs onglets thématiques et géographiques.

## Table `raw_contacts` (sortie de l'étape 1)

| Colonne | Description |
|---|---|
| `sheet` | onglet d'origine |
| `row_index` | ligne dans l'onglet (1 = première ligne de données) |
| `name`, `activity`, `commune`, `quartier`, `segment` | colonnes source, épurées (espaces, vides ramenés à NULL) |
| `phone_raw`, `email_raw` | valeurs d'origine, conservées telles quelles |
| `phone_e164` | numéro canonique `+22901XXXXXXXX`, NULL si non convertible |
| `phone_status` | `migre`, `deja_migre`, `zero_restaure`, `suspect_01_court`, `invalide`, `vide` |
| `phone_extra` | nombre de numéros supplémentaires trouvés dans la cellule |
| `email_norm` | adresse normalisée (minuscules, sans espaces), NULL si invalide |
| `email_status` | `valide`, `invalide`, `vide` |

## Volumétrie (ingestion du 2026-07-16)

| Mesure | Valeur |
|---|---|
| Lignes chargées | 496 729 |
| Noms d'entreprise distincts | 234 017 |
| Couples (nom, téléphone) distincts | 235 350 |
| Téléphones valides distincts | 178 837 |
| Emails valides distincts | 215 895 |

Le rapport lignes / entités distinctes confirme que la déduplication (étape 2) réduira la base de moitié environ.

## Qualité de la source : constats chiffrés

### Téléphones

| Statut | Lignes | Part |
|---|---|---|
| `migre` (ancien plan à 8 chiffres, converti) | 386 893 | 77,9 % |
| `suspect_01_court` | 109 780 | 22,1 % |
| `invalide` | 56 | ~0 % |

Constat clé : **toutes** les valeurs téléphone de la source font exactement 8 caractères. Les 109 780 numéros `suspect_01_court` (8 chiffres commençant par « 01 ») sont donc très probablement des numéros du nouveau plan à 10 chiffres **tronqués à 8 caractères par l'export source**, avec perte des 2 derniers chiffres. Deux indices convergent :

1. l'ancien plan n'autorisait aucun numéro commençant par 0 ;
2. le chiffre qui suit leur préfixe « 01 » suit la même distribution que les premiers chiffres des mobiles de l'ancien plan (9 : 51 011, 6 : 36 579, 5 : 14 563, 4 : 7 542), exactement ce qu'on attend de numéros migrés puis coupés.

Ces numéros sont irrécupérables sans re-collecte : le pipeline les marque au lieu d'inventer des chiffres.

### Emails

| Statut | Lignes | Part |
|---|---|---|
| `valide` (syntaxe) | 495 444 | 99,7 % |
| `invalide` | 1 285 | 0,3 % |

Validation purement syntaxique à ce stade : elle ne dit pas si la boîte existe. Une vérification des domaines (MX) est envisageable plus tard.

## Tables de l'étape 2

### `entities` (déduplication exacte, 2a)

Une ligne par groupe de fiches strictement identiques sur la clé (nom canonique, téléphone brut, email normalisé). Colonnes : nom canonique (le plus long des membres), `name_norm`, contacts, listes JSON des communes / quartiers / segments / onglets d'origine, `member_rows` (nombre de lignes brutes regroupées), `cluster_id` (rempli par 2b). Chaque ligne de `raw_contacts` porte l'`entity_id` de son entité.

### `candidate_pairs` (rapprochement flou, 2b)

Une ligne par paire candidate issue du blocking : canaux qui l'ont proposée, score décomposé (`name_sim`, `contact`, `geo`), score total et zone (`fusion`, `zone_grise`, `rejet`).

### Volumétrie de l'étape 2 (run du 2026-07-16)

| Mesure | Valeur |
|---|---:|
| Entités après dédup exacte | 235 360 (496 729 lignes, 53 % de copies) |
| Paires candidates | 280 377 (canaux : nom 256 267, email 23 311, téléphone 1 668) |
| Blocs écartés car trop gros | 351 emails, 3 174 tokens de nom |
| Zone de fusion | 351 |
| Zone grise | 56 729 |
| Rejets | 223 297 |
| Fusions refusées par le garde-fou anti méga-cluster | 0 |
| Entreprises finales (baseline) | 235 009 |

Les seuils du score sont provisoires : un échantillon stratifié de 420 paires (`data/gold_pairs.csv`, privé) attend son annotation manuelle pour mesurer précision et rappel, calibrer les seuils et évaluer l'arbitrage LLM de la zone grise.

### Divers

- Aucune cellule ne contient plusieurs numéros (le cas est géré par le code car il est classique dans ce genre de source, mais il ne se présente pas ici).
- Aucune cellule téléphone ou email vide.
