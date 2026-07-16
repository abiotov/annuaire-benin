"""Tests de l'évaluation contre le jeu de vérité (données fictives)."""

import pytest

from annuaire_benin.dedupe.evaluate import compute_metrics, read_annotations


def _row(zone, label, score):
    return {"zone": zone, "same_business": label, "score": score}


def test_compute_metrics_precision_and_recall():
    rows = [
        _row("fusion", "oui", 0.9),
        _row("fusion", "oui", 0.85),
        _row("fusion", "non", 0.83),
        _row("fusion", "incertain", 0.84),
        _row("zone_grise", "oui", 0.7),
        _row("zone_grise", "non", 0.65),
        _row("rejet", "non", 0.4),
    ]
    metrics = compute_metrics(rows)
    assert metrics.merge_precision == pytest.approx(2 / 3)
    # 3 vraies paires tranchées, 2 captées par la zone de fusion.
    assert metrics.recall_among_candidates == pytest.approx(2 / 3)
    assert metrics.unsure_count == 1
    assert metrics.by_zone["fusion"]["incertain"] == 1


def test_compute_metrics_band_rates():
    rows = [
        _row("fusion", "oui", 0.95),
        _row("fusion", "non", 0.95),
        _row("rejet", "non", 0.3),
    ]
    metrics = compute_metrics(rows)
    assert metrics.band_positive_rate[(0.9, 1.01)] == (1, 2)
    assert metrics.band_positive_rate[(0.0, 0.6)] == (0, 1)


def test_read_annotations_rejects_bad_label(tmp_path):
    csv_path = tmp_path / "gold.csv"
    csv_path.write_text(
        "entity_a,entity_b,score,zone,same_business\n1,2,0.9,fusion,peut-etre\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="label invalide"):
        read_annotations(csv_path)
