"""Étape 5 : lexique français mot-clé -> secteur pour la recherche.

Dérivé automatiquement de la table de classification (les 334 libellés
d'activité du registre et les libellés de secteurs) : « pressing »
mène à services-divers, « quincaillerie » aux matériaux, « anacarde »
au commerce agricole. Un mot n'entre au lexique que s'il désigne un
secteur de façon dominante (au moins 80 % de ses occurrences), ce qui
élimine naturellement les mots transverses comme « vente » ou
« services ».
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

from annuaire_benin.classify.mapping import load_mapping
from annuaire_benin.classify.taxonomy import SECTORS

_MIN_LENGTH = 3  # « BTP » et « GSM » sont des mots-clés légitimes
_DOMINANCE = 0.8

# Mots de liaison et verbes du registre, sans valeur de recherche.
_STOPWORDS = {
    "achat", "vente", "exercice", "toutes", "tous", "autres", "divers",
    "diverses", "activites", "prestations", "dans", "pour", "avec", "sans",
    "liees", "connexes", "generale", "general", "detail", "gros",
    "des", "les", "aux", "une", "ses", "sur", "via",
}

_TOKEN_RE = re.compile(r"[a-z]+")


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(fold(text))
            if len(t) >= _MIN_LENGTH and t not in _STOPWORDS]


def build_lexicon() -> dict[str, str]:
    """Mot-clé (plié, sans accents) -> identifiant de secteur."""
    occurrences: dict[str, Counter] = {}
    for activity, sector in load_mapping().items():
        for token in set(tokens(activity)):
            occurrences.setdefault(token, Counter())[sector] += 1
    for sector, label in SECTORS.items():
        for token in set(tokens(label)):
            occurrences.setdefault(token, Counter())[sector] += 1

    lexicon = {}
    for token, sectors in occurrences.items():
        (sector, top), total = sectors.most_common(1)[0], sum(sectors.values())
        if top / total >= _DOMINANCE:
            lexicon[token] = sector
    return lexicon
