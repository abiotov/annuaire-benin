"""Chargement de la table activité -> secteur.

La table ``mapping.csv`` est exhaustive et figée : le champ « activité »
du registre béninois est un vocabulaire fermé de 334 valeurs, chacune a
été affectée à la main à un secteur de la taxonomie (relecture complète,
voir docs/donnees.md). Toute activité inconnue rencontrée à
la classification est comptée, jamais devinée.
"""

from __future__ import annotations

import csv
from importlib import resources

from annuaire_benin.classify.taxonomy import SECTORS


def load_mapping() -> dict[str, str]:
    """Charge et valide la table activité -> secteur."""
    source = resources.files("annuaire_benin.classify").joinpath("mapping.csv")
    mapping: dict[str, str] = {}
    with source.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            activity = row["activity"].strip()
            sector = row["sector"].strip()
            if not activity:
                raise ValueError("activité vide dans mapping.csv")
            if activity in mapping:
                raise ValueError(f"activité en double dans mapping.csv : {activity!r}")
            if sector not in SECTORS:
                raise ValueError(f"secteur inconnu {sector!r} pour {activity!r}")
            mapping[activity] = sector
    return mapping
