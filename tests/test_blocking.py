"""Tests de la génération de paires candidates (blocking)."""

from annuaire_benin.dedupe.blocking import (
    CHANNEL_EMAIL,
    CHANNEL_NAME,
    CHANNEL_PHONE,
    CONTACT_BLOCK_CAP,
    candidate_pairs,
)


def _entity(entity_id, tokens=(), phone=None, email=None):
    return (entity_id, list(tokens), phone, email)


def test_pairs_from_each_channel():
    pairs, stats = candidate_pairs([
        _entity(1, ["KOFFI"], "+2290197000001", "a@example.com"),
        _entity(2, ["KOFFI"], "+2290197000001", "b@example.com"),
        _entity(3, ["AUTRE"], None, "b@example.com"),
    ])
    assert pairs[(1, 2)] == {CHANNEL_PHONE, CHANNEL_NAME}
    assert pairs[(2, 3)] == {CHANNEL_EMAIL}
    assert (1, 3) not in pairs
    assert stats.total_pairs == 2


def test_oversized_contact_block_is_dropped_and_counted():
    shared = [
        _entity(i, [f"NOM{i}"], "+2290197000001", None)
        for i in range(CONTACT_BLOCK_CAP + 2)
    ]
    pairs, stats = candidate_pairs(shared)
    assert not pairs  # le téléphone partagé par 12 entités ne prouve rien
    assert stats.oversized_blocks[CHANNEL_PHONE] == 1


def test_truncated_phones_never_block():
    # Une entité sans phone_e164 (numéro tronqué) ne rejoint aucun bloc téléphone.
    pairs, _ = candidate_pairs([
        _entity(1, ["ALPHA"], None, None),
        _entity(2, ["BETA"], None, None),
    ])
    assert not pairs
