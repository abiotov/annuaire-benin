"""Tests de l'arbitrage LLM (sans réseau : parsing, prompt, application)."""

import sqlite3

import pytest

from annuaire_benin.dedupe.arbitrate import (
    ARBITRATIONS_SCHEMA,
    VERDICT_SAME,
    VERDICT_UNSURE,
    build_prompt,
    parse_verdicts,
    run_apply,
)


def test_parse_verdicts_happy_path():
    text = 'Voici : [{"i": 1, "v": "meme"}, {"i": 2, "v": "diff"}, {"i": 3, "v": "incertain"}]'
    assert parse_verdicts(text, 3) == ["meme", "diff", "incertain"]


def test_parse_verdicts_defends_against_garbage():
    # JSON invalide, indices hors bornes, verdicts inconnus : tout retombe
    # en incertain plutôt que de fabriquer des fusions.
    assert parse_verdicts("pas de json", 2) == ["incertain", "incertain"]
    assert parse_verdicts('[{"i": 9, "v": "meme"}, {"i": 1, "v": "peut-etre"}]', 2) == [
        "incertain", "incertain",
    ]
    assert parse_verdicts('[{"i": 2, "v": "MEME"}]', 2) == ["incertain", "meme"]


def test_build_prompt_mentions_names_and_contacts():
    entities = {
        1: {"name": "ATELIER FICTIF", "communes": "COTONOU",
            "quartiers": "QUARTIER A", "sector": "Services divers"},
        2: {"name": "ATELIER FIKTIF", "communes": "COTONOU",
            "quartiers": "QUARTIER A", "sector": "Services divers"},
    }
    pairs = [{"a": 1, "b": 2, "channels": "name,phone", "name_sim": 0.91}]
    prompt = build_prompt(pairs, entities)
    assert "ATELIER FICTIF" in prompt and "ATELIER FIKTIF" in prompt
    assert "téléphone identique" in prompt
    assert "quartier QUARTIER A" in prompt
    assert "0.91" in prompt
    assert "tableau JSON" in prompt


@pytest.fixture
def connection():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE entities (id INTEGER PRIMARY KEY, cluster_id INTEGER)")
    conn.executemany("INSERT INTO entities (id) VALUES (?)", [(1,), (2,), (3,), (4,)])
    conn.execute(
        "CREATE TABLE candidate_pairs (entity_a INTEGER, entity_b INTEGER,"
        " score REAL, zone TEXT)"
    )
    conn.executemany("INSERT INTO candidate_pairs VALUES (?, ?, ?, ?)", [
        (1, 2, 0.95, "fusion"),      # fusion du baseline
        (3, 4, 0.78, "zone_grise"),  # paire grise arbitrée « même »
    ])
    conn.executescript(ARBITRATIONS_SCHEMA)
    conn.execute("INSERT INTO arbitrations VALUES (3, 4, ?, 'test', '2026-07-17T00:00:00')",
                 (VERDICT_SAME,))
    yield conn
    conn.close()


def test_run_apply_merges_baseline_and_arbitrated(connection, capsys):
    run_apply(connection)
    clusters = dict(connection.execute("SELECT id, cluster_id FROM entities"))
    assert clusters[1] == clusters[2]  # baseline
    assert clusters[3] == clusters[4]  # arbitrée
    assert clusters[1] != clusters[3]
    assert "4 entités -> 2 entreprises finales" in capsys.readouterr().out


def test_unsure_verdicts_never_merge(connection):
    connection.execute("UPDATE arbitrations SET verdict = ?", (VERDICT_UNSURE,))
    run_apply(connection)
    clusters = dict(connection.execute("SELECT id, cluster_id FROM entities"))
    assert clusters[3] != clusters[4]
