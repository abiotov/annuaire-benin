"""Tests de l'atlas : agrégation, appariement géographique, construction."""

import sqlite3

import pytest

from annuaire_benin.atlas.aggregate import aggregate
from annuaire_benin.atlas.build import build
from annuaire_benin.atlas.geo import ALIASES, _norm, build_paths, load_features


@pytest.fixture
def connection():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE raw_contacts (id INTEGER PRIMARY KEY, entity_id INTEGER,"
        " commune TEXT)"
    )
    conn.execute("CREATE TABLE entities (id INTEGER PRIMARY KEY, sector TEXT)")
    conn.executemany("INSERT INTO raw_contacts VALUES (?, ?, ?)", [
        # Entité 1 : majoritairement à COTONOU.
        (1, 1, "COTONOU"), (2, 1, "COTONOU"), (3, 1, "PARAKOU"),
        # Entité 2 : SEME-PODJI (teste l'alias geoBoundaries).
        (4, 2, "SEME-PODJI"),
        # Entité 3 : aucune commune -> non localisée.
        (5, 3, None),
    ])
    conn.executemany("INSERT INTO entities VALUES (?, ?)", [
        (1, "commerce-alimentaire"), (2, "services-divers"), (3, "immobilier"),
    ])
    yield conn
    conn.close()


def test_aggregate_counts_majority_commune_and_unlocated(connection):
    data = aggregate(connection)
    assert data["total_entities"] == 3
    assert data["unlocated"] == 1
    assert data["communes"]["COTONOU"] == {
        "total": 1, "sectors": {"commerce-alimentaire": 1},
    }
    assert "PARAKOU" not in data["communes"]  # minoritaire pour l'entité 1
    assert data["sectors"]["immobilier"]["total"] == 1  # comptée nationalement


def test_geojson_has_all_77_communes_and_aliases_resolve():
    names = {_norm(f["properties"]["shapeName"]) for f in load_features()}
    assert len(names) == 77
    for target in ALIASES.values():
        assert _norm(target) in names


def test_build_paths_projects_into_viewbox():
    paths = build_paths(["COTONOU", "SEME-PODJI", "N'DALI"])
    assert set(paths) == {"COTONOU", "SEME-PODJI", "N'DALI"}
    assert all(d.startswith("M") and d.endswith("Z") for d in paths.values())


def test_build_paths_fails_loudly_on_unknown_commune():
    with pytest.raises(ValueError, match="sans contour"):
        build_paths(["COMMUNE INCONNUE"])


def test_build_writes_self_contained_page(connection, tmp_path):
    out = tmp_path / "atlas" / "index.html"
    build(connection, out)
    page = out.read_text(encoding="utf-8")
    assert "__PAYLOAD__" not in page and "__GENERATED__" not in page
    assert "Atlas économique du Bénin" in page
    assert "COTONOU" in page and "SEME-PODJI" in page
    # Autonome : aucun script ni style externe.
    assert 'src="http' not in page and 'href="http' not in page.replace(
        'href="https://www.geoboundaries.org/"', "").replace(
        'href="https://github.com/abiotov/annuaire-benin"', "")
