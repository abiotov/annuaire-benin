"""Étape 3 : classification des entités par secteur d'activité.

Détermine l'activité principale de chaque entité (l'activité la plus
fréquente parmi ses lignes brutes), la traduit en secteur via la table
exhaustive, écrit ``entities.activity_main`` et ``entities.sector``,
et imprime la distribution par secteur.

Usage :
    python -m annuaire_benin.classify.run --db data/annuaire.db
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter
from pathlib import Path

from annuaire_benin.classify.mapping import load_mapping
from annuaire_benin.classify.taxonomy import SECTORS


def _ensure_columns(connection: sqlite3.Connection) -> None:
    columns = [row[1] for row in connection.execute("PRAGMA table_info(entities)")]
    if "activity_main" not in columns:
        connection.execute("ALTER TABLE entities ADD COLUMN activity_main TEXT")
    if "sector" not in columns:
        connection.execute("ALTER TABLE entities ADD COLUMN sector TEXT")


def _main_activities(connection: sqlite3.Connection) -> dict[int, str]:
    """Activité la plus fréquente de chaque entité."""
    per_entity: dict[int, Counter] = {}
    query = (
        "SELECT entity_id, activity, COUNT(*) FROM raw_contacts"
        " WHERE activity IS NOT NULL AND entity_id IS NOT NULL"
        " GROUP BY entity_id, activity"
    )
    for entity_id, activity, count in connection.execute(query):
        per_entity.setdefault(entity_id, Counter())[activity] += count
    return {
        entity_id: activities.most_common(1)[0][0]
        for entity_id, activities in per_entity.items()
    }


def classify(connection: sqlite3.Connection) -> Counter:
    """Classe toutes les entités ; retourne la distribution par secteur."""
    mapping = load_mapping()
    _ensure_columns(connection)

    distribution: Counter = Counter()
    unknown: Counter = Counter()
    updates = []
    for entity_id, activity in _main_activities(connection).items():
        sector = mapping.get(activity)
        if sector is None:
            unknown[activity] += 1
            continue
        distribution[sector] += 1
        updates.append((activity, sector, entity_id))

    connection.executemany(
        "UPDATE entities SET activity_main = ?, sector = ? WHERE id = ?", updates
    )
    connection.commit()

    if unknown:
        print(f"ATTENTION : {sum(unknown.values())} entités à activité inconnue"
              f" ({len(unknown)} valeurs), à ajouter à mapping.csv :")
        for activity, count in unknown.most_common(10):
            print(f"  {count:>6}  {activity[:70]}")
    return distribution


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/annuaire.db"))
    args = parser.parse_args(argv)
    if not args.db.exists():
        parser.error(f"base introuvable : {args.db}")

    connection = sqlite3.connect(args.db)
    distribution = classify(connection)
    total = sum(distribution.values())
    print(f"{total} entités classées dans {len(distribution)} secteurs :\n")
    for sector, count in distribution.most_common():
        print(f"  {count:>7}  {SECTORS[sector]}")
    connection.close()
    return 0


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
