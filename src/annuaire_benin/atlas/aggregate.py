"""Étape 4 : agrégation commune × secteur pour l'atlas.

Produit uniquement des comptages agrégés (jamais de donnée
individuelle) : c'est ce qui rend l'atlas publiable.

Chaque entité est comptée dans sa commune principale (la commune la
plus fréquente parmi ses lignes brutes). Les entités sans commune sont
comptées à part (« non localisées »), jamais écartées en silence.
"""

from __future__ import annotations

import sqlite3
from collections import Counter

from annuaire_benin.classify.taxonomy import SECTORS


def _main_communes(connection: sqlite3.Connection) -> dict[int, str]:
    """Commune la plus fréquente de chaque entité (absentes exclues)."""
    per_entity: dict[int, Counter] = {}
    query = (
        "SELECT entity_id, commune, COUNT(*) FROM raw_contacts"
        " WHERE commune IS NOT NULL AND entity_id IS NOT NULL"
        " GROUP BY entity_id, commune"
    )
    for entity_id, commune, count in connection.execute(query):
        per_entity.setdefault(entity_id, Counter())[commune] += count
    return {
        entity_id: communes.most_common(1)[0][0]
        for entity_id, communes in per_entity.items()
    }


def aggregate(connection: sqlite3.Connection) -> dict:
    """Comptages agrégés : national, par secteur, par commune × secteur."""
    communes = _main_communes(connection)

    sector_totals: Counter = Counter()
    commune_data: dict[str, dict] = {}
    total = 0
    unlocated = 0

    for entity_id, sector in connection.execute(
        "SELECT id, sector FROM entities WHERE sector IS NOT NULL"
    ):
        total += 1
        sector_totals[sector] += 1
        commune = communes.get(entity_id)
        if commune is None:
            unlocated += 1
            continue
        entry = commune_data.setdefault(commune, {"total": 0, "sectors": Counter()})
        entry["total"] += 1
        entry["sectors"][sector] += 1

    return {
        "total_entities": total,
        "unlocated": unlocated,
        "sectors": {
            sector: {"label": SECTORS[sector], "total": count}
            for sector, count in sector_totals.most_common()
        },
        "communes": {
            commune: {"total": entry["total"], "sectors": dict(entry["sectors"])}
            for commune, entry in sorted(commune_data.items())
        },
    }
