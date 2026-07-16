"""Validation et normalisation des données de contact béninoises.

Ce sous-paquet a vocation à être extrait en bibliothèque autonome
publiée sur PyPI une fois stabilisé (voir docs/architecture.md).
"""

from annuaire_benin.contacts.emails import EmailResult, EmailStatus
from annuaire_benin.contacts.phone import PhoneResult, PhoneStatus, extract_all, normalize

__all__ = [
    "EmailResult",
    "EmailStatus",
    "PhoneResult",
    "PhoneStatus",
    "extract_all",
    "normalize",
]
