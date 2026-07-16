"""Étape 2 : évaluation de la déduplication contre le jeu de vérité.

Lit le CSV de paires annotées à la main (colonne ``same_business`` :
oui / non / incertain) et mesure ce que valent réellement les zones du
score : précision de la zone de fusion, répartition des vraies paires,
taux de « oui » par bande de score.

Les paires ``incertain`` sont écartées des métriques mais comptées :
elles attendent un arbitrage humain.

Limites assumées (documentées dans docs/donnees.md) : l'échantillon
est stratifié par zone, pas exhaustif, et le rappel est mesuré au sein
des paires candidates ; une vraie paire jamais proposée par le
blocking reste invisible ici.

Usage :
    python -m annuaire_benin.dedupe.evaluate data/gold_pairs_annotated.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from annuaire_benin.dedupe import scoring

LABEL_SAME = "oui"
LABEL_DIFFERENT = "non"
LABEL_UNSURE = "incertain"
VALID_LABELS = {LABEL_SAME, LABEL_DIFFERENT, LABEL_UNSURE}

SCORE_BANDS = ((0.0, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01))


@dataclass(frozen=True)
class Metrics:
    """Métriques calculées sur les paires annotées."""

    by_zone: dict[str, Counter]
    merge_precision: float | None  # précision de la zone de fusion
    recall_among_candidates: float | None  # part des vraies paires en zone de fusion
    band_positive_rate: dict[tuple[float, float], tuple[int, int]]  # bande -> (oui, total)
    unsure_count: int


def read_annotations(path: Path) -> list[dict]:
    """Charge le CSV annoté et valide les labels."""
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        label = row.get("same_business", "").strip().lower()
        if label not in VALID_LABELS:
            raise ValueError(
                f"label invalide {label!r} pour la paire"
                f" ({row.get('entity_a')}, {row.get('entity_b')})"
            )
        row["same_business"] = label
        row["score"] = float(row["score"])
    return rows


def compute_metrics(rows: list[dict]) -> Metrics:
    """Calcule les métriques ; les paires incertaines sont écartées."""
    by_zone: dict[str, Counter] = {}
    for row in rows:
        by_zone.setdefault(row["zone"], Counter())[row["same_business"]] += 1

    decided = [row for row in rows if row["same_business"] != LABEL_UNSURE]

    merge_zone = [row for row in decided if row["zone"] == scoring.ZONE_MERGE]
    true_in_merge = sum(1 for row in merge_zone if row["same_business"] == LABEL_SAME)
    merge_precision = true_in_merge / len(merge_zone) if merge_zone else None

    all_true = sum(1 for row in decided if row["same_business"] == LABEL_SAME)
    recall = true_in_merge / all_true if all_true else None

    band_rate = {}
    for low, high in SCORE_BANDS:
        in_band = [row for row in decided if low <= row["score"] < high]
        positives = sum(1 for row in in_band if row["same_business"] == LABEL_SAME)
        band_rate[(low, high)] = (positives, len(in_band))

    unsure = sum(1 for row in rows if row["same_business"] == LABEL_UNSURE)
    return Metrics(
        by_zone=by_zone,
        merge_precision=merge_precision,
        recall_among_candidates=recall,
        band_positive_rate=band_rate,
        unsure_count=unsure,
    )


def print_report(metrics: Metrics) -> None:
    print("Répartition des labels par zone :")
    for zone in (scoring.ZONE_MERGE, scoring.ZONE_GRAY, scoring.ZONE_REJECT):
        counter = metrics.by_zone.get(zone, Counter())
        print(f"  {zone:<12} oui {counter[LABEL_SAME]:>4}  non {counter[LABEL_DIFFERENT]:>4}"
              f"  incertain {counter[LABEL_UNSURE]:>4}")

    print("\nSur les paires tranchées (incertaines écartées :"
          f" {metrics.unsure_count}) :")
    if metrics.merge_precision is not None:
        print(f"  précision de la zone de fusion : {metrics.merge_precision:.1%}")
    if metrics.recall_among_candidates is not None:
        print("  part des vraies paires captées par la zone de fusion :"
              f" {metrics.recall_among_candidates:.1%}")

    print("\nTaux de vraies paires par bande de score :")
    for (low, high), (positives, total) in metrics.band_positive_rate.items():
        rate = f"{positives / total:.1%}" if total else "  n/a"
        print(f"  [{low:.1f}, {high:.1f})  {positives:>3} / {total:<4} {rate}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("annotations", type=Path, help="CSV annoté (same_business rempli)")
    args = parser.parse_args(argv)
    print_report(compute_metrics(read_annotations(args.annotations)))
    return 0


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
