"""Tests de la déduplication exacte (2a) sur une base en mémoire.

Toutes les valeurs sont fictives.
"""

import json
import sqlite3

import pytest

from annuaire_benin.dedupe.exact import build_entities

FIXTURE_ROWS = [
    # Même entreprise copiée dans deux onglets : une seule entité attendue.
    (1, "ATELIER FICTIF", "97000001", "+2290197000001", "migre",
     "atelier@example.com", "COTONOU", "QUARTIER A", "Site Internet", "Prioritaires"),
    (2, "ATELIER FICTIF", "97000001", "+2290197000001", "migre",
     "atelier@example.com", "COTONOU", "QUARTIER B", "Site Internet", "Cotonou"),
    # Variante de ponctuation et d'accent : même clé après normalisation.
    (3, "Atelier   Fictif", "97000001", "+2290197000001", "migre",
     "atelier@example.com", None, None, None, "Site Internet"),
    # Même nom mais autre téléphone : entité distincte.
    (4, "ATELIER FICTIF", "96000002", "+2290196000002", "migre",
     "atelier@example.com", "COTONOU", None, None, "Prioritaires"),
    # Entreprise sans rapport.
    (5, "BOUTIQUE EXEMPLE", "95000003", "+2290195000003", "migre",
     "boutique@example.com", "PARAKOU", None, None, "Boutique en Ligne"),
]


@pytest.fixture
def connection():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE raw_contacts (id INTEGER PRIMARY KEY, name TEXT, phone_raw TEXT,"
        " phone_e164 TEXT, phone_status TEXT, email_norm TEXT, commune TEXT,"
        " quartier TEXT, segment TEXT, sheet TEXT)"
    )
    conn.executemany(
        "INSERT INTO raw_contacts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", FIXTURE_ROWS
    )
    yield conn
    conn.close()


def test_build_entities_groups_exact_copies(connection):
    assert build_entities(connection) == 3

    grouped = connection.execute(
        "SELECT member_rows, sheets, quartiers FROM entities WHERE phone_raw = '97000001'"
    ).fetchone()
    assert grouped[0] == 3
    assert json.loads(grouped[1]) == ["Cotonou", "Prioritaires", "Site Internet"]
    assert json.loads(grouped[2]) == ["QUARTIER A", "QUARTIER B"]


def test_build_entities_links_raw_rows(connection):
    build_entities(connection)
    entity_ids = dict(connection.execute("SELECT id, entity_id FROM raw_contacts"))
    assert entity_ids[1] == entity_ids[2] == entity_ids[3]
    assert entity_ids[4] != entity_ids[1]
    assert entity_ids[5] != entity_ids[1]


def test_build_entities_is_idempotent(connection):
    assert build_entities(connection) == build_entities(connection) == 3
