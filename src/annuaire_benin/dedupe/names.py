"""Normalisation des noms d'entreprise pour la déduplication.

Deux usages distincts :

- ``normalize`` produit la forme canonique d'un nom (majuscules sans
  accents, ponctuation neutralisée) : c'est la clé de la déduplication
  exacte et l'entrée des mesures de similarité.
- ``blocking_tokens`` extrait les mots discriminants d'un nom : ce sont
  les clés de blocage qui décident quelles fiches méritent d'être
  comparées. Les mots génériques du registre du commerce (ETS, SARL,
  SERVICES...) en sont exclus car ils rapprocheraient tout avec tout.
"""

from __future__ import annotations

import re
import unicodedata

# Mots trop fréquents dans les raisons sociales béninoises pour être
# discriminants. Retirés du blocage seulement : la similarité de noms,
# elle, travaille sur le nom complet.
STOPWORDS = frozenset({
    "AGENCE", "AU", "AUX", "BENIN", "BUSINESS", "CHEZ", "CIE", "COMPAGNIE",
    "DE", "DES", "DIEU", "DU", "EN", "ET", "ETABLISSEMENT", "ETABLISSEMENTS",
    "ETS", "FILS", "FRERES", "GENERAL", "GENERALE", "GIE", "GLOBAL", "GROUP",
    "GROUPE", "INTER", "INTERNATIONAL", "LA", "LE", "LES", "MULTI",
    "MULTISERVICES", "ONG", "PLUS", "SA", "SARL", "SAS", "SERVICE",
    "SERVICES", "SOCIETE", "SOEURS", "STE",
})

_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]+")
_MIN_TOKEN_LENGTH = 3


def normalize(name: str | None) -> str:
    """Forme canonique : majuscules, sans accents ni ponctuation."""
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFD", name)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(_NON_ALNUM_RE.sub(" ", ascii_only.upper()).split())


def tokens(name: str | None) -> list[str]:
    """Mots du nom canonique."""
    return normalize(name).split()


def blocking_tokens(name: str | None) -> list[str]:
    """Mots discriminants du nom, utilisables comme clés de blocage."""
    return [
        token
        for token in tokens(name)
        if token not in STOPWORDS and len(token) >= _MIN_TOKEN_LENGTH and not token.isdigit()
    ]
