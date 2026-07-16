"""Étape 2 : orchestration de la déduplication.

Enchaîne la dédup exacte (2a), le blocking, le scoring et le
clustering (2b), persiste les paires candidates et les clusters dans
la base, et imprime le bilan chiffré de chaque temps.

Usage :
    python -m annuaire_benin.dedupe.run --db data/annuaire.db
    python -m annuaire_benin.dedupe.run --db data/annuaire.db --sample-gold data/gold_pairs.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from annuaire_benin.dedupe import blocking, clustering, exact, names, scoring

PAIRS_SCHEMA = """
DROP TABLE IF EXISTS candidate_pairs;
CREATE TABLE candidate_pairs (
    entity_a  INTEGER NOT NULL,
    entity_b  INTEGER NOT NULL,
    channels  TEXT NOT NULL,   -- canaux de blocage, séparés par des virgules
    name_sim  REAL NOT NULL,
    contact   REAL NOT NULL,
    geo       REAL NOT NULL,
    score     REAL NOT NULL,
    zone      TEXT NOT NULL,
    PRIMARY KEY (entity_a, entity_b)
);
"""

GOLD_SAMPLE_PER_ZONE = 140
GOLD_SEED = 20260716  # échantillon reproductible


def _load_entities(connection: sqlite3.Connection) -> dict[int, dict]:
    """Charge les entités avec leurs clés de blocage et leurs communes."""
    entities = {}
    query = "SELECT id, name, name_norm, phone_e164, email_norm, communes FROM entities"
    for entity_id, name, name_norm, phone_e164, email_norm, communes in connection.execute(query):
        entities[entity_id] = {
            "name": name,
            "name_norm": name_norm,
            "tokens": names.blocking_tokens(name_norm),
            "phone": phone_e164,
            "email": email_norm,
            "communes": set(json.loads(communes)),
        }
    return entities


def _contact_degrees(entities: dict[int, dict]) -> tuple[dict[str, int], dict[str, int]]:
    """Nombre d'entités portant chaque téléphone / email."""
    phone_degree: dict[str, int] = defaultdict(int)
    email_degree: dict[str, int] = defaultdict(int)
    for entity in entities.values():
        if entity["phone"]:
            phone_degree[entity["phone"]] += 1
        if entity["email"]:
            email_degree[entity["email"]] += 1
    return phone_degree, email_degree


def run(db_path: Path, gold_path: Path | None) -> None:
    connection = sqlite3.connect(db_path)

    print("2a. Déduplication exacte...")
    started = time.perf_counter()
    entity_count = exact.build_entities(connection)
    total_rows = connection.execute("SELECT COUNT(*) FROM raw_contacts").fetchone()[0]
    print(f"  {total_rows} lignes brutes -> {entity_count} entités"
          f" en {time.perf_counter() - started:.0f} s")

    print("\n2b. Blocking...")
    entities = _load_entities(connection)
    phone_degree, email_degree = _contact_degrees(entities)
    blocking_input = [
        (entity_id, e["tokens"], e["phone"], e["email"]) for entity_id, e in entities.items()
    ]
    pairs, block_stats = blocking.candidate_pairs(blocking_input)
    print(f"  {block_stats.total_pairs} paires candidates"
          f" (par canal : {block_stats.pairs_by_channel})")
    print(f"  blocs écartés car trop gros : {block_stats.oversized_blocks}")

    print("\n2b. Scoring...")
    started = time.perf_counter()
    connection.executescript(PAIRS_SCHEMA)
    zone_counter: Counter[str] = Counter()
    merge_edges = []
    rows = []
    for (a, b), channels in pairs.items():
        ea, eb = entities[a], entities[b]
        shared_phone = ea["phone"] if ea["phone"] == eb["phone"] else None
        shared_email = ea["email"] if ea["email"] == eb["email"] else None
        result = scoring.score_pair(
            ea["name_norm"], eb["name_norm"], ea["communes"], eb["communes"], channels,
            phone_degree.get(shared_phone, 0), email_degree.get(shared_email, 0),
        )
        zone_counter[result.zone] += 1
        if result.zone == scoring.ZONE_MERGE:
            merge_edges.append((a, b, result.score))
        rows.append((a, b, ",".join(sorted(channels)), result.name_sim,
                     result.contact, result.geo, result.score, result.zone))
    connection.executemany(
        "INSERT INTO candidate_pairs VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows
    )
    print(f"  {len(rows)} paires scorées en {time.perf_counter() - started:.0f} s")
    for zone in (scoring.ZONE_MERGE, scoring.ZONE_GRAY, scoring.ZONE_REJECT):
        print(f"  {zone:<12} {zone_counter[zone]:>8}")

    print("\n2b. Clustering...")
    assignment, cluster_stats = clustering.cluster(merge_edges, list(entities))
    connection.executemany(
        "UPDATE entities SET cluster_id = ? WHERE id = ?",
        [(cluster_id, entity_id) for entity_id, cluster_id in assignment.items()],
    )
    connection.commit()
    final_count = len(set(assignment.values()))
    sizes = Counter(assignment.values())
    largest = sizes.most_common(5)
    print(f"  fusions appliquées : {cluster_stats.clusters_merged},"
          f" refusées par le garde-fou : {cluster_stats.edges_skipped_by_guard}")
    print(f"  {entity_count} entités -> {final_count} entreprises finales")
    print(f"  plus gros clusters : {[count for _, count in largest]}")

    if gold_path is not None:
        _sample_gold(connection, entities, gold_path)
    connection.close()


def _sample_gold(connection: sqlite3.Connection, entities: dict[int, dict],
                 gold_path: Path) -> None:
    """Échantillonne des paires par zone pour l'annotation manuelle.

    Le fichier produit contient des données réelles : il reste dans
    data/ (ignoré par git). La colonne ``same_business`` est à remplir
    à la main avec oui / non.
    """
    rng = random.Random(GOLD_SEED)
    sample = []
    for zone in (scoring.ZONE_MERGE, scoring.ZONE_GRAY, scoring.ZONE_REJECT):
        zone_pairs = connection.execute(
            "SELECT entity_a, entity_b, score, zone FROM candidate_pairs WHERE zone = ?",
            (zone,),
        ).fetchall()
        rng.shuffle(zone_pairs)
        sample.extend(zone_pairs[:GOLD_SAMPLE_PER_ZONE])

    gold_path.parent.mkdir(parents=True, exist_ok=True)
    with gold_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "entity_a", "entity_b", "name_a", "name_b", "communes_a", "communes_b",
            "score", "zone", "same_business",
        ])
        for a, b, score, zone in sample:
            ea, eb = entities[a], entities[b]
            writer.writerow([
                a, b, ea["name"], eb["name"],
                " / ".join(sorted(ea["communes"])), " / ".join(sorted(eb["communes"])),
                score, zone, "",
            ])
    print(f"\nJeu à annoter : {len(sample)} paires dans {gold_path}"
          " (colonne same_business à remplir, fichier privé)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/annuaire.db"))
    parser.add_argument("--sample-gold", type=Path, default=None,
                        help="chemin du CSV de paires à annoter à la main")
    args = parser.parse_args(argv)
    if not args.db.exists():
        parser.error(f"base introuvable : {args.db} (lancer l'ingestion d'abord)")
    run(args.db, args.sample_gold)
    return 0


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
