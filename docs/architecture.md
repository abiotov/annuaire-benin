# Architecture

## Vue d'ensemble

Le projet est un pipeline en étapes successives. Chaque étape lit la sortie de la précédente, produit un résultat mesurable, et peut être rejouée indépendamment.

1. **Ingestion et validation** (`annuaire_benin.ingest`) : lecture du classeur Excel source, normalisation des téléphones et des emails à la volée, chargement dans une table SQLite unique `raw_contacts`. Chaque anomalie est qualifiée par un statut plutôt qu'écartée en silence.
2. **Déduplication** (`annuaire_benin.dedupe`) : d'abord la dédup exacte (`exact`, clé nom canonique + téléphone + email, produit la table `entities`), puis le rapprochement flou en trois temps : `blocking` (paires candidates par téléphone, email ou mot de nom rare, avec plafonds de taille de bloc), `scoring` (score décomposé : similarité de noms dont le cœur discriminant, contact partagé pondéré par sa rareté, accord géographique, et double plancher de similarité de nom qui interdit toute fusion, même en zone grise, entre noms sans rapport), `clustering` (union-find avec garde-fou anti méga-cluster). Les seuils sont provisoires jusqu'à validation par un jeu de vérité annoté à la main (précision et rappel).
3. **Classification des activités** (`annuaire_benin.classify`) : le champ « activité » s'est révélé être un vocabulaire fermé de 334 valeurs de registre, pas du texte libre. La classification est donc une table de correspondance exhaustive et figée (`mapping.csv`, versionnée dans le repo, relue en entier) vers une taxonomie de 25 secteurs (`taxonomy.py`) adaptée à la réalité béninoise (le commerce de détail, dominant, est détaillé par famille de produits). Chaque entité reçoit le secteur de son activité majoritaire ; une activité hors table est comptée, jamais devinée.
4. **Atlas économique** (`annuaire_benin.atlas`) : `aggregate` produit les comptages commune × secteur (chaque entité comptée dans sa commune majoritaire, les non-localisées comptées à part) ; `geo` apparie les 77 communes aux contours geoBoundaries (7 alias d'orthographe explicites, échec bruyant si une commune manque), les projette en chemins SVG côté Python, calcule emprises et centres, et exporte un GeoJSON nommé comme le registre ; `build` assemble une page HTML riche (recherche, filtre, liens partageables, tableau triable, deux thèmes) publiée par GitHub Pages depuis `docs/atlas/`. Aucune donnée individuelle ne sort : uniquement des agrégats.

   La carte principale est une choroplèthe Leaflet posée sur un fond OpenStreetMap (Leaflet 1.9.4 vendorisé dans `docs/atlas/vendor/`, aucun CDN ; tuiles OSM chargées à l'exécution avec attribution, inversées en thème sombre). Un masque « monde moins Bénin » (contour geoBoundaries ADM0) estompe l'extérieur du pays pour que sa silhouette ressorte du fond de carte. La vue 3D (MapLibre GL 4.7 vendorisé, chargé au premier clic) extrude chaque commune en prisme dont la hauteur suit la racine carrée du nombre d'entreprises (une échelle linéaire rendrait tout illisible face à Cotonou). La seule dépendance tierce à l'exécution est le serveur de tuiles : si la couche de contours ou les tuiles manquent, le panneau et le tableau restent utilisables. Le registre ne fournissant aucune coordonnée GPS, et le projet ne publiant aucune donnée individuelle, la carte montre des densités par commune, jamais des entreprises pointées une à une.
5. **Recherche en langage naturel** (`annuaire_benin.atlas.lexicon` + l'interpréteur de `atlas.js`) : pas de LLM, une page statique publique exposerait sa clé API. Le lexique mot-clé → secteur (414 entrées) est dérivé automatiquement de la table de classification avec une règle de dominance à 80 % qui écarte les mots transverses (« vente », « produits ») ; les 77 communes sont reconnues avec ou sans accents et tirets ; une grammaire d'intentions (compter, classer, profil de commune, densité, spécialisation) traduit la question en état de la carte, et la réponse chiffrée s'affiche dans une carte dédiée. Les questions incomprises reçoivent un message de repli qui montre des exemples valides.

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
