"""Étape 4 : agrégation commune × secteur pour l'atlas.

Produit uniquement des comptages agrégés (jamais de donnée
individuelle) : c'est ce qui rend l'atlas publiable.

L'unité comptée est l'entreprise finale : les entités fusionnées par
la déduplication (baseline + fusions validées en revue) partagent un
``cluster_id`` et comptent pour une seule entreprise, dans la commune
et le secteur majoritaires de leurs lignes. Les entreprises sans
commune sont comptées à part (« non localisées »), jamais écartées en
silence.
"""

from __future__ import annotations

import sqlite3
from collections import Counter

from annuaire_benin.atlas.population import load_population
from annuaire_benin.classify.taxonomy import SECTORS

TOP_QUARTIERS = 8


def _commune_counters(connection: sqlite3.Connection) -> dict[int, Counter]:
    """Occurrences de chaque commune dans les lignes brutes, par entité."""
    per_entity: dict[int, Counter] = {}
    query = (
        "SELECT entity_id, commune, COUNT(*) FROM raw_contacts"
        " WHERE commune IS NOT NULL AND entity_id IS NOT NULL"
        " GROUP BY entity_id, commune"
    )
    for entity_id, commune, count in connection.execute(query):
        per_entity.setdefault(entity_id, Counter())[commune] += count
    return per_entity


def _top_quartiers(connection: sqlite3.Connection) -> dict[str, list]:
    """Les quartiers comptant le plus d'entités, par commune (agrégats)."""
    per_commune: dict[str, list] = {}
    query = (
        "SELECT commune, quartier, COUNT(DISTINCT entity_id) AS n FROM raw_contacts"
        " WHERE commune IS NOT NULL AND quartier IS NOT NULL AND entity_id IS NOT NULL"
        " GROUP BY commune, quartier ORDER BY commune, n DESC"
    )
    for commune, quartier, count in connection.execute(query):
        bucket = per_commune.setdefault(commune, [])
        if len(bucket) < TOP_QUARTIERS:
            bucket.append([quartier, count])
    return per_commune


def aggregate(connection: sqlite3.Connection) -> dict:
    """Comptages agrégés : national, par secteur, par commune × secteur.

    Une entreprise = un cluster de déduplication ; ses attributs sont
    les majoritaires de ses membres, pondérés par leurs lignes brutes.
    """
    commune_counters = _commune_counters(connection)
    population = load_population()
    quartiers = _top_quartiers(connection)

    clusters: dict[int, dict] = {}
    for entity_id, cluster_id, sector, member_rows in connection.execute(
        "SELECT id, COALESCE(cluster_id, id), sector, member_rows FROM entities"
        " WHERE sector IS NOT NULL"
    ):
        cluster = clusters.setdefault(
            cluster_id, {"sectors": Counter(), "communes": Counter()}
        )
        cluster["sectors"][sector] += member_rows
        cluster["communes"].update(commune_counters.get(entity_id, {}))

    sector_totals: Counter = Counter()
    commune_data: dict[str, dict] = {}
    total = len(clusters)
    unlocated = 0

    for cluster in clusters.values():
        sector = cluster["sectors"].most_common(1)[0][0]
        sector_totals[sector] += 1
        if not cluster["communes"]:
            unlocated += 1
            continue
        commune = cluster["communes"].most_common(1)[0][0]
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
            commune: {
                "total": entry["total"],
                "sectors": dict(entry["sectors"]),
                "pop": population.get(commune, 0),
                "quartiers": quartiers.get(commune, []),
            }
            for commune, entry in sorted(commune_data.items())
        },
    }
