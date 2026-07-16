"""Normalisation des numéros de téléphone béninois.

Le Bénin est passé le 30 novembre 2024 d'un plan de numérotation à
8 chiffres à un plan à 10 chiffres : chaque numéro existant a reçu le
préfixe « 01 ». Les données sources mélangent les deux formats, avec
en plus des zéros de tête perdus (cellules stockées en numérique) et
des écritures variées (+229, espaces, points, tirets).

Ce module ramène chaque écriture vers le format E.164 canonique
« +22901XXXXXXXX » et qualifie précisément ce qu'il n'a pas pu
convertir, pour que les anomalies soient mesurables plutôt que
silencieusement écartées.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

COUNTRY_CODE = "229"
NEW_PLAN_PREFIX = "01"

# Premiers chiffres valides d'un numéro de l'ancien plan à 8 chiffres :
# 2 pour les lignes fixes, 4/5/6/9 pour les mobiles.
_VALID_FIRST_DIGITS = frozenset("24569")

# Caractères de mise en forme à supprimer (le « / » et la virgule sont
# au contraire des séparateurs entre plusieurs numéros, voir extract_all).
_FORMATTING_RE = re.compile(r"[\s.\-()]")
_DIGIT_RUN_RE = re.compile(r"\d+")


class PhoneStatus(Enum):
    """Issue de la normalisation d'un numéro."""

    ALREADY_MIGRATED = "deja_migre"  # 10 chiffres, déjà au nouveau plan
    MIGRATED = "migre"  # 8 chiffres ancien plan, préfixe 01 ajouté
    LEADING_ZERO_RESTORED = "zero_restaure"  # 9 chiffres, zéro de tête perdu
    SUSPICIOUS_SHORT_01 = "suspect_01_court"  # 8 chiffres commençant par 01
    INVALID = "invalide"
    EMPTY = "vide"

    @property
    def is_valid(self) -> bool:
        return self in (
            PhoneStatus.ALREADY_MIGRATED,
            PhoneStatus.MIGRATED,
            PhoneStatus.LEADING_ZERO_RESTORED,
        )


@dataclass(frozen=True)
class PhoneResult:
    """Résultat de la normalisation d'un numéro.

    Attributes:
        raw: la valeur d'origine, telle que trouvée dans la source.
        e164: le numéro canonique « +22901XXXXXXXX », ou None si invalide.
        status: la qualification de la conversion.
    """

    raw: str
    e164: str | None
    status: PhoneStatus

    @property
    def national(self) -> str | None:
        """Numéro au format national à 10 chiffres (« 01XXXXXXXX »)."""
        return self.e164[4:] if self.e164 else None


def _coerce_text(raw: object) -> str:
    """Ramène une valeur de cellule (str, int, float, None) vers du texte."""
    if raw is None:
        return ""
    if isinstance(raw, float) and raw.is_integer():
        return str(int(raw))
    return str(raw).strip()


def _strip_country_code(digits: str) -> str:
    """Retire un éventuel indicatif pays écrit en préfixe."""
    if digits.startswith("00" + COUNTRY_CODE):
        return digits[5:]
    if digits.startswith(COUNTRY_CODE) and len(digits) > 10:
        return digits[3:]
    return digits


def _classify(digits: str) -> tuple[str | None, PhoneStatus]:
    """Classe une suite de chiffres et retourne (national, statut)."""
    if len(digits) == 10 and digits.startswith(NEW_PLAN_PREFIX):
        if digits[2] in _VALID_FIRST_DIGITS:
            return digits, PhoneStatus.ALREADY_MIGRATED
        return None, PhoneStatus.INVALID

    # Zéro de tête perdu par un stockage numérique : 0197065700 devient
    # 197065700. On le restaure puis on revalide comme un numéro à 10 chiffres.
    if len(digits) == 9 and digits.startswith("1"):
        restored = "0" + digits
        if restored[2] in _VALID_FIRST_DIGITS:
            return restored, PhoneStatus.LEADING_ZERO_RESTORED
        return None, PhoneStatus.INVALID

    if len(digits) == 8:
        if digits.startswith(NEW_PLAN_PREFIX):
            # Ni un ancien numéro plausible (pas de 0 en tête dans l'ancien
            # plan), ni un nouveau complet (il manque 2 chiffres) : on marque
            # sans convertir plutôt que d'inventer.
            return None, PhoneStatus.SUSPICIOUS_SHORT_01
        if digits[0] in _VALID_FIRST_DIGITS:
            return NEW_PLAN_PREFIX + digits, PhoneStatus.MIGRATED
        return None, PhoneStatus.INVALID

    return None, PhoneStatus.INVALID


def normalize(raw: object) -> PhoneResult:
    """Normalise une cellule censée contenir un seul numéro.

    Une cellule contenant plusieurs numéros est marquée INVALID ici ;
    utiliser extract_all pour la traiter.
    """
    text = _coerce_text(raw)
    if not text:
        return PhoneResult(raw=text, e164=None, status=PhoneStatus.EMPTY)

    cleaned = _FORMATTING_RE.sub("", text)
    runs = _DIGIT_RUN_RE.findall(cleaned)
    if len(runs) != 1:
        return PhoneResult(raw=text, e164=None, status=PhoneStatus.INVALID)

    digits = _strip_country_code(runs[0])
    national, status = _classify(digits)
    e164 = f"+{COUNTRY_CODE}{national}" if national else None
    return PhoneResult(raw=text, e164=e164, status=status)


def extract_all(raw: object) -> list[PhoneResult]:
    """Extrait et normalise tous les numéros d'une cellule.

    Gère les cellules du type « 95 85 17 64 / 97 44 07 00 » : la mise en
    forme est retirée, puis chaque suite de chiffres restante est
    normalisée indépendamment.
    """
    text = _coerce_text(raw)
    if not text:
        return [PhoneResult(raw=text, e164=None, status=PhoneStatus.EMPTY)]

    cleaned = _FORMATTING_RE.sub("", text)
    runs = _DIGIT_RUN_RE.findall(cleaned)
    if not runs:
        return [PhoneResult(raw=text, e164=None, status=PhoneStatus.INVALID)]

    results = []
    for run in runs:
        digits = _strip_country_code(run)
        national, status = _classify(digits)
        e164 = f"+{COUNTRY_CODE}{national}" if national else None
        results.append(PhoneResult(raw=text, e164=e164, status=status))
    return results
