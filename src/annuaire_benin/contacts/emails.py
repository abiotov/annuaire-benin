"""Validation et normalisation des adresses email.

Validation syntaxique volontairement pragmatique : le but est d'écarter
les valeurs manifestement inutilisables (mentions « aucun », numéros de
téléphone saisis dans la colonne email, fautes de frappe grossières),
pas de couvrir l'intégralité de la RFC 5322.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_EMAIL_RE = re.compile(r"^[a-z0-9][a-z0-9._%+\-]*@[a-z0-9][a-z0-9.\-]*\.[a-z]{2,}$")


class EmailStatus(Enum):
    VALID = "valide"
    INVALID = "invalide"
    EMPTY = "vide"


@dataclass(frozen=True)
class EmailResult:
    """Résultat de la normalisation d'une adresse.

    Attributes:
        raw: la valeur d'origine.
        normalized: l'adresse en minuscules sans espaces, ou None.
        status: la qualification.
    """

    raw: str
    normalized: str | None
    status: EmailStatus


def normalize(raw: object) -> EmailResult:
    """Normalise une adresse : casse, espaces, puis validation syntaxique."""
    text = "" if raw is None else str(raw).strip()
    if not text:
        return EmailResult(raw=text, normalized=None, status=EmailStatus.EMPTY)

    candidate = text.lower().replace(" ", "")
    if _EMAIL_RE.match(candidate):
        return EmailResult(raw=text, normalized=candidate, status=EmailStatus.VALID)
    return EmailResult(raw=text, normalized=None, status=EmailStatus.INVALID)
