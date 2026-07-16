"""Tests du score de similarité et de ses garde-fous."""

from annuaire_benin.dedupe.blocking import CHANNEL_EMAIL, CHANNEL_NAME, CHANNEL_PHONE
from annuaire_benin.dedupe.scoring import (
    ZONE_MERGE,
    ZONE_REJECT,
    contact_rarity_score,
    score_pair,
)


def test_near_identical_names_same_place_merge():
    result = score_pair(
        "ETS KOFFI", "KOFFI BENIN", {"COTONOU"}, {"COTONOU"},
        {CHANNEL_NAME, CHANNEL_PHONE}, phone_degree=2, email_degree=0,
    )
    assert result.zone == ZONE_MERGE


def test_shared_contact_alone_never_merges_different_names():
    # Le cas du propriétaire de plusieurs entreprises : même téléphone
    # rare, noms sans rapport. Ne doit JAMAIS fusionner.
    result = score_pair(
        "KOFFI TRANSPORT", "BOULANGERIE MODERNE", {"COTONOU"}, {"COTONOU"},
        {CHANNEL_PHONE}, phone_degree=2, email_degree=0,
    )
    assert result.zone == ZONE_REJECT
    assert result.name_sim < 0.70


def test_high_score_without_name_similarity_stays_out_of_merge():
    # Même avec contact fort et géo parfaite, un name_sim sous le
    # plancher interdit la zone de fusion.
    result = score_pair(
        "ALPHA DISTRIBUTION", "GAMMA COUTURE", {"PARAKOU"}, {"PARAKOU"},
        {CHANNEL_PHONE, CHANNEL_EMAIL}, phone_degree=2, email_degree=2,
    )
    assert result.zone != ZONE_MERGE


def test_disjoint_communes_pull_score_down():
    same_place = score_pair(
        "ETS KOFFI", "ETS KOFFI", {"COTONOU"}, {"COTONOU"}, {CHANNEL_NAME}, 0, 0,
    )
    other_place = score_pair(
        "ETS KOFFI", "ETS KOFFI", {"COTONOU"}, {"PARAKOU"}, {CHANNEL_NAME}, 0, 0,
    )
    assert other_place.score < same_place.score


def test_contact_rarity_decreases_with_degree():
    assert contact_rarity_score(2) == 1.0
    assert contact_rarity_score(5) == 0.5
    assert contact_rarity_score(9) == 0.25
    assert contact_rarity_score(10) == 0.0
    assert contact_rarity_score(50) == 0.0
