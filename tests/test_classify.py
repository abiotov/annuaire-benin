"""Tests de la classification par secteur (données fictives)."""

import sqlite3

import pytest

from annuaire_benin.classify.mapping import load_mapping
from annuaire_benin.classify.run import classify
from annuaire_benin.classify.taxonomy import SECTORS


def test_mapping_loads_and_is_valid():
    mapping = load_mapping()
    assert len(mapping) == 334
    assert set(mapping.values()) <= set(SECTORS)
    # Chaque secteur de la taxonomie est réellement utilisé.
    assert set(mapping.values()) == set(SECTORS)


def test_mapping_spot_checks():
    mapping = load_mapping()
    assert mapping["Transfert d'argent via réseaux mobiles"] == "finance-mobile-money"
    assert mapping["Transformation agroalimentaire"] == "industrie-transformation"
    assert mapping["Formation en Informatique"] == "education-formation"
    assert mapping["Agro Business"] == "agriculture-elevage-peche"
    assert mapping["Achat et vente de jeux vidéos"] == "commerce-telephonie-electronique"


@pytest.fixture
def connection():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE raw_contacts (id INTEGER PRIMARY KEY, entity_id INTEGER,"
        " activity TEXT)"
    )
    conn.execute("CREATE TABLE entities (id INTEGER PRIMARY KEY)")
    rows = [
        # Entité 1 : deux lignes, activité majoritaire = pressing.
        (1, 1, "Pressing"),
        (2, 1, "Pressing"),
        (3, 1, "Coiffure et soins de beauté"),
        # Entité 2 : activité hors table -> comptée, jamais devinée.
        (4, 2, "Activité inventée pour le test"),
    ]
    conn.executemany("INSERT INTO raw_contacts VALUES (?, ?, ?)", rows)
    conn.executemany("INSERT INTO entities (id) VALUES (?)", [(1,), (2,)])
    yield conn
    conn.close()


def test_classify_majority_activity_and_unknowns(connection):
    distribution = classify(connection)
    assert distribution == {"services-divers": 1}
    activity, sector = connection.execute(
        "SELECT activity_main, sector FROM entities WHERE id = 1"
    ).fetchone()
    assert activity == "Pressing"
    assert sector == "services-divers"
    # L'entité à activité inconnue reste non classée.
    assert connection.execute(
        "SELECT sector FROM entities WHERE id = 2"
    ).fetchone() == (None,)
