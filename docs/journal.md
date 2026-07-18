# Journal du projet

## 2026-07-18 (suite) : le jeu de vérité complété, dernières fusions

- Les 92 paires « incertaines » du jeu de vérité ont été tranchées une à une (revue déléguée), en s'appuyant sur le signal décisif ignoré lors de la première annotation : les contacts partagés. Même cœur de nom + téléphone/email identique + même commune → oui (37) ; deux enseignes différentes d'un même propriétaire, ou homonymes familiaux inter-communes sans contact commun → non (55). **Gold complet : 95 oui, 325 non, 0 incertaine.**
- Métriques re-mesurées sur les 420 paires : précision de la fusion **83,1 %**, rappel parmi les candidates 67,4 %. La baisse du rappel est une information : 31 vraies paires vivent en zone grise, hors de portée du seuil ; les 37 nouvelles validées ont été fusionnées via la table `arbitrations` (modèle `revue-gold`).
- Clustering rejoué : 184 + 87 fusions validées, **235 360 entités → 235 107 entreprises finales** ; atlas et encart méthodologique realignés.

## 2026-07-18 (suite) : retrait de la vue 3D

Décision produit d'Etienne : la 3D sort de la page. Retirés : le bouton et le conteneur, tout le code MapLibre de `atlas.js`, la bibliothèque vendorisée (environ 850 Ko de dépôt en moins), les mentions dans les docs ; l'image Open Graph est régénérée depuis la vue 2D, et les anciens liens `v=3d`/`m=3d` retombent proprement sur la carte. Le harnais passe à 21 vérifications. La 3D reste dans l'historique git si un jour elle doit revenir.

## 2026-07-18 (suite) : harnais de test complet et refonte du design

Sur exigence d'Etienne (« teste tout », « hyper dynamique et très impressionnant ») :

- **Harnais Playwright local** (`playwright-core` sur le Edge installé) : matrice de 18 vérifications rejouable en une commande : 12 questions types (locales, IA, comparaison, exclusion, charabia), les 4 vues, le thème, l'export CSV, l'absence de débordement mobile à 390 px, la collecte des erreurs JS.
- **Bugs débusqués par le harnais et corrigés** : « azerty » sélectionnait la commune ZE (correspondance en sous-chaîne, remplacée par des frontières de mots) ; « en dehors de Cotonou » répondait Cotonou (notion d'exclusion ajoutée de bout en bout : routage local, schéma du Worker, classement filtré : « hors COTONOU : 1. Abomey-Calavi... ») ; ordinaux cassés par une passe de correction antérieure (« 5 commune » → « 5ᵉ », « 1ʳᵉ »).
- **Refonte du design** : héros « Posez une question à l'économie béninoise » avec la recherche en barre de commande centrale (halo de focus, pilules d'exemples cliquables), ligne de statistiques animée, barre d'outils collante en verre dépoli avec bascule de vues unifiée [Carte · 3D · Tableau · Panorama], **panneau flottant en verre par-dessus la carte** (glissement à la sélection), légende flottante, carte de réponse animée, micro-interactions sur tous les contrôles, apparition orchestrée au chargement, le tout débrayé par `prefers-reduced-motion` et fonctionnel en clair, sombre et mobile (vérifié sur captures).
- L'état 3D vit maintenant dans l'URL comme une vue (`v=3d`), les anciens liens `m=3d` restent compris.

## 2026-07-18 (suite) : la couche LLM de la recherche, déployée proprement

Etienne a validé l'option « proxy serveur » : la recherche gagne une seconde couche pour la langue libre, sans jamais exposer de clé.

- `worker/` : Worker Cloudflare (déployé sur <https://annuaire-nlq.abiotov.workers.dev>, code versionné, clé en secret via `wrangler secret put`). Garde-fous : CORS restreint à l'atlas et au serveur local de dev, 8 requêtes/minute/IP, question tronquée à 300 caractères, sortie plafonnée, JSON validé (action et secteur contre listes fermées). Le LLM (gemini-2.5-flash-lite, température 0, sortie JSON native) traduit la question en intention structurée ; les chiffres restent calculés par la page : une hallucination de nombre est architecturalement impossible.
- `atlas.js` : bascule automatique vers le Worker quand la grammaire locale ne comprend pas ou quand la question contient deux communes (leçon du test : « est-ce que Parakou a plus de restaurants que Bohicon ? » était à moitié comprise localement et répondait un comptage ; désormais deux communes = interprète). Nouvelle action `compare` branchée sur le comparateur existant. Toute réponse passée par l'IA est étiquetée « question interprétée par IA (Gemini), chiffres calculés depuis les données ». Hors ligne ou Worker muet : repli pédagogique, et un drapeau anti-récursion protège la boucle.
- Incidents de déploiement documentés : sous-domaine workers.dev d'un compte neuf enregistré via l'API (wrangler ne sait pas le faire en non-interactif), retour chariot injecté par le pipe PowerShell dans le secret (400 Gemini, corrigé par un trim côté Worker), outillage Cloudflare officiel installé pour les sessions futures.
- Vérifié de bout en bout sur capture : intention `compare` correcte, panneau de comparaison à barres doubles, étiquette IA visible. 77 tests unitaires verts.

## 2026-07-18 (suite) : étape 5, la recherche en langage naturel

- Décision d'architecture : pas de LLM (page statique publique = clé API exposée). Interpréteur français embarqué : lexique de 414 mots-clés → secteur dérivé de la table de classification (`atlas/lexicon.py`, règle de dominance à 80 % qui écarte « vente », « produits », « gsm » ambigu), reconnaissance des 77 communes, grammaire d'intentions (combien, où le plus, profil, densité, spécialisation).
- La réponse s'affiche dans une carte dédiée ET pilote l'atlas : « où le BTP est-il sur-représenté ? » répond « Lokossa (1,7×), Natitingou (1,7×), Parakou (1,5×) », passe la carte en spécialisation et sélectionne le secteur. Exemples cliquables sous la barre, messages de repli qui guident.
- Bugs attrapés par la vérification visuelle : seuil de mots-clés à 4 lettres qui excluait « BTP » (abaissé à 3, la dominance contient le bruit), intention spécialisation sans secteur qui tombait dans le repli générique (message dédié). Deux artefacts de harnais aussi diagnostiqués (encodage d'une copie de test, apostrophe PowerShell).
- Test e2e ajouté : la question tapée doit afficher une réponse et changer le filtre de secteur. 77 tests unitaires verts.
- La feuille de route des 5 étapes est complète.

## 2026-07-18 : revue des paires arbitrées et atlas cohérent avec la déduplication

- Revue une à une des 63 paires « même » confirmées par l'arbitrage (déléguée à l'assistant par Etienne) : **52 validées** (typos, réordonnancements, suffixes sur nom distinctif, souvent avec contact partagé), **7 rejetées** (deux boutiques d'un même propriétaire comme IBM ESTHETIK / IBM FASHION, membres d'une famille comme SAIBOU / MOUSSA SEYBOU), **4 laissées indécises**. Décisions tracées dans `data/revue_zone_grise_validee.csv` (privé) et dans la table `arbitrations`.
- Clustering rejoué avec les fusions validées : 184 + 52 arêtes, **235 360 entités → 235 125 entreprises finales** (un triangle de 3 fiches, FEMI FESTI'HALL, fusionne en une).
- Incohérence de la revue senior réglée : l'atlas comptait les entités, il compte désormais les **entreprises finales** (une par cluster de déduplication, commune et secteur majoritaires pondérés par les lignes brutes). Tuiles de l'atlas : 235 125 entreprises, 235 022 localisées, 103 sans commune.
- Incident mineur : le CSV de revue était verrouillé par Excel, les validations sont écrites dans un nouveau fichier `_validee.csv`.

## 2026-07-17 (suite) : étape 2c, l'arbitrage LLM mesuré puis refusé

Etienne a fourni une clé Gemini (stockée dans `data/.env`, ignorée par git, `.gitignore` renforcé sur `*.env`).

- `dedupe/arbitrate.py` : juge LLM par lots de 25 paires (API REST Gemini, urllib, température 0, retries et respect des quotas), contexte par paire (noms, communes, quartiers, secteurs, contacts partagés, similarité), verdicts persistés dans la table `arbitrations` par tranches de 100 (interruption sans perte, reprise exacte), modes `--gold` (évaluation contre le jeu de vérité), arbitrage borné (`--limit`, `--min-score`) et `--apply`.
- Protocole gold-first : 4 configurations mesurées sur les 203 paires grises annotées avant tout déploiement (tableau dans docs/donnees.md). Meilleure précision : 71,4 % avec contre-examen adversarial, au prix du rappel (45,5 %) ; gemini-3-flash-preview seul trouve 100 % des vraies paires mais à 44 % de précision.
- Incidents documentés : le thinking par défaut de gemini-2.5-flash tronquait le JSON des lots (ses jetons comptent dans maxOutputTokens) ; la persistance de fin de run aurait perdu un run interrompu par timeout, rendue incrémentale.
- **Décision : pas de fusion automatique.** Précision insuffisante et échantillon de 11 positifs trop petit pour certifier. L'arbitrage devient un pré-tri : 1 500 meilleures paires grises jugées et persistées pour revue humaine. Renoncer sur mesure est un résultat d'ingénierie, pas un échec.
- Run de pré-tri exécuté (3 passes reprenables de 500) : **63 « même » confirmées au contre-examen, 1 024 « différentes », 413 incertaines**. Le taux de « même » s'effondre avec le score (49 puis 6 puis 8 par tranche de 500), cohérent avec l'ordre de score. Export de revue : `data/revue_zone_grise.csv` (privé), colonne `validation_humaine` à remplir ; en tête de liste, des quasi-doublons évidents (« ADRI O ET FILS » / « ADRIENEETFILS »).

## 2026-07-17 (suite) : atlas v5, la revue senior appliquée en entier

Suite de la revue complète de la page (« fais tout ») :

- **Trois métriques** : Volume (quantiles), **Pour 1 000 habitants** (populations RGPH-4 2013 par commune, source INSAE, figées dans `atlas/population_2013.csv` avec 5 alias d'orthographe validés 77/77) et **Spécialisation** (location quotient : part locale du secteur / part nationale, échelle divergente bleu-gris-rouge à seuils fixes, l'invite guide vers le choix d'un secteur). La carte d'agriculture en spécialisation raconte enfin quelque chose : vallée du Niger et centre rural en rouge, villes en bleu.
- **Panorama** : 25 mini-cartes canvas (une par secteur, projection normalisée calculée une fois), cliquables, réagissant à la métrique et au thème.
- **Comparateur** : épingler une commune puis en choisir une autre, panneau côte à côte (totaux, densité, rang, 6 secteurs en barres doubles), état `cmp` dans l'URL.
- **Panneau enrichi** : population, densité pour 1 000 habitants, top 5 des quartiers en agrégats (le champ quartier était inexploité).
- **Partage** : favicon SVG (drapeau), balises Open Graph avec image `og.png` (1200×630 issue de la capture 3D).
- **Robustesse et honnêteté** : état de chargement de la couche, encart « À propos des données et de la méthode » dans la page (source, méthode, métriques, limites dont la date d'export inconnue, accessibilité via la vue tableau, crédits), 4e tuile doublonnante remplacée par « 25 secteurs », communes à zéro en gris neutre au lieu de trous.
- **Export CSV** des agrégats commune × secteur (avec population), côté client.
- **Dette réglée** : tout le JS extrait de `template.html` vers `atlas.js` (copié par le build), et **smoke test Playwright** dans la CI (nouveau job e2e : page chargée, 77 communes dessinées, tableau, invite de spécialisation, absence de débordement horizontal en 390 px, ce que Edge headless ne sait pas tester avec sa largeur minimale d'environ 492 px).
- Vérifications visuelles : spécialisation agriculture, panorama, panneau Cotonou (quartiers réels : Menontin, Zogbo, Vèdoko).

## 2026-07-17 (suite) : atlas v4, masque national et vue 3D

- Retour d'Etienne : « la carte du Bénin a disparu » ; sur fond OSM, le pays se fondait dans ses voisins. Réponse : un masque « monde moins Bénin » (contour geoBoundaries ADM0, ajouté à `communes.geojson` sous le nom `__mask__`) estompe tout l'extérieur du pays ; la silhouette nationale ressort à nouveau tout en gardant le détail OSM à l'intérieur. Vérifié en production au passage : la page et ses fichiers se servaient correctement (200), le problème était bien la lisibilité.
- Vue 3D à la demande : MapLibre GL 4.7 vendorisé (784 Ko, chargé au premier clic sur « Vue 3D »), chaque commune extrudée en prisme, hauteur = racine carrée du nombre d'entreprises (documenté : le linéaire serait illisible face à Cotonou), rotation et inclinaison libres, tuiles estompées en thème sombre, survol et clic synchronisés avec le panneau, état `m=3d` partageable dans l'URL.
- Premier réglage de hauteur trop timide constaté sur capture (facteur 110 → 260) : Cotonou et Abomey-Calavi se dressent maintenant nettement sur la côte.
- 67 tests verts, captures de vérification en 2D masquée et en 3D.

## 2026-07-17 (suite) : atlas v3, la carte OpenStreetMap devient l'expérience principale

Retours d'Etienne sur la v2 : la météo ne sert à rien, pas d'emojis, et OpenStreetMap ne doit pas être caché derrière un bouton.

- La choroplèthe est désormais dessinée par Leaflet directement sur le fond OpenStreetMap : pan/zoom libre jusqu'à la rue, vol animé vers la commune cliquée, contour surligné, tuiles inversées en thème sombre. L'ancienne carte SVG maison et sa projection sont retirées (code mort supprimé de geo.py).
- Météo Open-Meteo retirée : jolie mais sans valeur informative (décision documentée dans le README).
- Tous les emojis remplacés par des icônes SVG inline (sprite de symboles, trait 2 px).
- Légende interactive : survoler une classe isole ses communes sur la carte.
- Robustesse constatée en vérification visuelle et corrigée : l'échec de chargement de la couche de contours n'empêche plus le panneau et le tableau de fonctionner.
- Limite posée explicitement : pas de points par entreprise, le registre n'a pas de coordonnées GPS et pointer des entreprises individuelles publierait des données personnelles ; l'atlas montre des densités par commune.
- Captures de vérification sur serveur HTTP local : vue nationale sombre (tuiles inversées) et lien profond #c=COTONOU zoomé au niveau des rues. 67 tests verts.

## 2026-07-17 (suite) : atlas v2, expérience enrichie

- UX : recherche de commune avec autocomplétion, liens partageables (état commune/secteur/vue dans l'URL), bascule de thème (auto/clair/sombre), tableau triable par colonne, bouton « commune au hasard », badge de classement, compteurs et barres animés, tout respectant `prefers-reduced-motion`.
- OpenStreetMap : vue de détail Leaflet (1.9.4 vendorisé dans `docs/atlas/vendor/`, aucun CDN), contour de la commune surligné, tuiles OSM chargées à la demande avec attribution ; filtre d'inversion des tuiles en thème sombre.
- Open-Meteo : météo actuelle de la commune sélectionnée (API sans clé, CORS ouvert), cache de session 30 min, dégradation silencieuse hors ligne. OpenWeatherMap écarté : il exige une clé API, inexposable dans une page statique (décision documentée).
- Correctif issu de la vérification visuelle : l'emoji drapeau 🇧🇯 s'affiche « BJ » sous Windows, remplacé par un drapeau SVG inline.
- `geo.py` : emprises, centres et export GeoJSON (coordonnées arrondies, ~100 m) servis à côté de la page pour Leaflet.
- Vérification headless des deux thèmes et d'un lien profond `#c=COTONOU` : sélection, badge et météo réelle (« couvert, 26 °C ») constatés sur capture. 68 tests verts.

## 2026-07-17 (suite) : étape 4, l'atlas économique

- `atlas/aggregate.py` : comptages commune × secteur, entité comptée dans sa commune majoritaire, 104 entités non localisées comptées à part. Agrégats seulement, rien d'individuel.
- `atlas/geo.py` : contours des 77 communes (geoBoundaries gbOpen BEN ADM2, domaine public, 173 Ko simplifiés, embarqués dans le paquet), 7 écarts d'orthographe résolus par alias explicites (SEME-PODJI/Seme-Kpodji, COBLY/Kobli...), projection équirectangulaire vers des chemins SVG côté Python, échec bruyant si une commune n'a pas de contour.
- `atlas/build.py` + `template.html` : page unique autonome (126 Ko, zéro requête externe), carte choroplèthe interactive, filtre par secteur, panneau de détail par commune, vue tableau, infobulles, thèmes clair et sombre (rampe séquentielle bleue inversée en sombre), navigation clavier sur la carte.
- Rendu vérifié par captures headless (Edge) dans les deux thèmes avant publication.
- Publication : GitHub Pages sert `docs/` ; l'atlas est en ligne sur <https://abiotov.github.io/annuaire-benin/atlas/>
- 67 tests verts. Incident d'environnement noté : le PATH du shell s'est mis à pointer vers le venv d'un autre projet ; l'interpréteur global est désormais appelé explicitement.

## 2026-07-17 : étape 3, classification par secteur

- Profilage du champ « activité » : vocabulaire fermé de 334 valeurs de registre (et non du texte libre). Conséquence assumée : ni LLM ni fine-tuning, une table de correspondance exhaustive suffit et elle est auditable.
- Taxonomie de 25 secteurs (`classify/taxonomy.py`), commerce détaillé par famille de produits.
- Table `classify/mapping.csv` générée par règles puis relue en entier ; pièges corrigés à la relecture : « trans-formation » capturé par « formation » (932 fiches d'agro-industrie parties en éducation), « b-usine-ss » capturé par « usine » (1 328 « Agro Business » partis en industrie), « jeux vidéos » capturé par « video ».
- `classify/run.py` : activité majoritaire par entité, secteur écrit dans `entities`, distribution imprimée. 235 360 entités classées, couverture 100 %, aucune valeur devinée.
- 62 tests verts. L'arbitrage LLM de la zone grise (étape 2) reste en attente d'une clé API.

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

- Dépôt publié sur GitHub (public) : <https://github.com/abiotov/annuaire-benin>, avec description et topics.
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
