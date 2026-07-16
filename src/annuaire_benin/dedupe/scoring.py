"""Étape 2b, temps 2 : score de similarité des paires candidates.

Le score combine trois familles de signaux :

- la similarité des noms (Jaro-Winkler et comparaison d'ensembles de
  mots, on garde la meilleure des deux) : c'est le signal principal ;
- le contact partagé, pondéré par sa rareté : un téléphone porté par
  exactement 2 entités est un indice fort, un email porté par 8
  entités un indice faible, au-delà il ne vaut plus rien (un même
  propriétaire déclare souvent plusieurs entreprises distinctes) ;
- l'accord géographique (communes).

Règle absolue : un contact partagé ne suffit JAMAIS à fusionner deux
fiches dont les noms diffèrent trop (MIN_NAME_SIM_FOR_MERGE). Deux
entreprises d'un même propriétaire restent deux entités.

Les seuils sont provisoires tant que le jeu de vérité annoté à la main
(docs/architecture.md) ne les a pas validés.
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

from annuaire_benin.dedupe import names
from annuaire_benin.dedupe.blocking import CHANNEL_EMAIL, CHANNEL_PHONE

WEIGHT_NAME = 0.65
WEIGHT_CONTACT = 0.20
WEIGHT_GEO = 0.15

MERGE_THRESHOLD = 0.82
REJECT_THRESHOLD = 0.60
MIN_NAME_SIM_FOR_MERGE = 0.70
# En dessous de ce plancher, les noms n'ont rien en commun : la paire est
# rejetée d'office, elle ne mérite même pas la zone grise (deux entreprises
# d'un même propriétaire partagent un contact, pas un nom).
MIN_NAME_SIM_FOR_GRAY = 0.60

ZONE_MERGE = "fusion"
ZONE_GRAY = "zone_grise"
ZONE_REJECT = "rejet"

# Score d'un contact partagé selon le nombre d'entités qui le portent.
_CONTACT_RARITY = ((2, 1.0), (5, 0.5), (9, 0.25))


@dataclass(frozen=True)
class PairScore:
    """Score décomposé d'une paire candidate, pour rester explicable."""

    name_sim: float
    contact: float
    geo: float
    score: float
    zone: str


def contact_rarity_score(degree: int) -> float:
    """Valeur d'un contact partagé par ``degree`` entités."""
    for cap, value in _CONTACT_RARITY:
        if degree <= cap:
            return value
    return 0.0


def name_similarity(name_norm_a: str, name_norm_b: str) -> float:
    """Similarité de noms dans [0, 1], meilleure de trois mesures.

    La troisième compare les noms réduits à leurs mots discriminants :
    « ETS KOFFI » et « KOFFI BENIN » partagent le même cœur « KOFFI »
    alors que les mesures sur noms complets les éloignent. Le tri des
    mots (token_sort et non token_set) évite qu'un cœur inclus dans un
    autre (« KOFFI » dans « KOFFI BOUTIQUE ») passe pour identique.
    """
    jaro = JaroWinkler.similarity(name_norm_a, name_norm_b)
    token_set = fuzz.token_set_ratio(name_norm_a, name_norm_b) / 100
    core_a = " ".join(names.blocking_tokens(name_norm_a))
    core_b = " ".join(names.blocking_tokens(name_norm_b))
    core = fuzz.token_sort_ratio(core_a, core_b) / 100 if core_a and core_b else 0.0
    return max(jaro, token_set, core)


def geo_agreement(communes_a: set[str], communes_b: set[str]) -> float:
    """1.0 si commune commune, 0.0 si disjointes, 0.5 si inconnue."""
    if not communes_a or not communes_b:
        return 0.5
    return 1.0 if communes_a & communes_b else 0.0


def score_pair(
    name_norm_a: str,
    name_norm_b: str,
    communes_a: set[str],
    communes_b: set[str],
    channels: set[str],
    phone_degree: int,
    email_degree: int,
) -> PairScore:
    """Score complet d'une paire candidate.

    ``phone_degree`` / ``email_degree`` : nombre d'entités portant le
    contact partagé (0 si le canal n'a pas proposé la paire).
    """
    name_sim = name_similarity(name_norm_a, name_norm_b)

    contact = 0.0
    if CHANNEL_PHONE in channels:
        contact = contact_rarity_score(phone_degree)
    if CHANNEL_EMAIL in channels:
        contact = max(contact, 0.8 * contact_rarity_score(email_degree))

    geo = geo_agreement(communes_a, communes_b)
    score = WEIGHT_NAME * name_sim + WEIGHT_CONTACT * contact + WEIGHT_GEO * geo

    if score >= MERGE_THRESHOLD and name_sim >= MIN_NAME_SIM_FOR_MERGE:
        zone = ZONE_MERGE
    elif score <= REJECT_THRESHOLD or name_sim < MIN_NAME_SIM_FOR_GRAY:
        zone = ZONE_REJECT
    else:
        zone = ZONE_GRAY

    return PairScore(
        name_sim=round(name_sim, 4),
        contact=round(contact, 4),
        geo=geo,
        score=round(score, 4),
        zone=zone,
    )
