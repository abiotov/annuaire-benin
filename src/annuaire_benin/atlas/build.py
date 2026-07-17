"""Étape 4 : construction de la page atlas.

Assemble les agrégats (aggregate), les contours projetés (geo) et le
gabarit HTML en une page unique entièrement autonome : aucune requête
externe, aucune donnée individuelle, publiable telle quelle (GitHub
Pages sert ``docs/atlas/index.html``).

Usage :
    python -m annuaire_benin.atlas.build --db data/annuaire.db --out docs/atlas/index.html
"""

from __future__ import annotations

import argparse
import datetime
import json
import sqlite3
import sys
from importlib import resources
from pathlib import Path

from annuaire_benin.atlas.aggregate import aggregate
from annuaire_benin.atlas.geo import bounds_of, export_geojson, match_features


def build(connection: sqlite3.Connection, out_path: Path) -> dict:
    """Construit la page et ses données annexes ; retourne les agrégats.

    Écrit deux fichiers : ``index.html`` et ``communes.geojson`` (la
    couche de contours que Leaflet dessine par-dessus le fond
    OpenStreetMap, servie depuis la même origine).
    """
    data = aggregate(connection)
    names = list(data["communes"])
    country = [[90.0, 180.0], [-90.0, -180.0]]
    for name, feature in match_features(names).items():
        min_lat, min_lon, max_lat, max_lon = bounds_of(feature)
        data["communes"][name]["bounds"] = [
            [round(min_lat, 3), round(min_lon, 3)],
            [round(max_lat, 3), round(max_lon, 3)],
        ]
        country[0] = [min(country[0][0], min_lat), min(country[0][1], min_lon)]
        country[1] = [max(country[1][0], max_lat), max(country[1][1], max_lon)]
    data["country_bounds"] = [
        [round(country[0][0], 3), round(country[0][1], 3)],
        [round(country[1][0], 3), round(country[1][1], 3)],
    ]

    template = (
        resources.files("annuaire_benin.atlas")
        .joinpath("template.html")
        .read_text(encoding="utf-8")
    )
    page = template.replace(
        "__PAYLOAD__", json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    ).replace("__GENERATED__", datetime.date.today().isoformat())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    geojson_path = out_path.parent / "communes.geojson"
    geojson_path.write_text(
        json.dumps(export_geojson(names), separators=(",", ":")), encoding="utf-8"
    )
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/annuaire.db"))
    parser.add_argument("--out", type=Path, default=Path("docs/atlas/index.html"))
    args = parser.parse_args(argv)
    if not args.db.exists():
        parser.error(f"base introuvable : {args.db}")

    connection = sqlite3.connect(args.db)
    data = build(connection, args.out)
    connection.close()

    size_kb = args.out.stat().st_size / 1024
    located = data["total_entities"] - data["unlocated"]
    print(f"Atlas écrit dans {args.out} ({size_kb:.0f} Ko)")
    print(f"  {data['total_entities']} entreprises, {located} localisées"
          f" ({data['unlocated']} sans commune), {len(data['communes'])} communes,"
          f" {len(data['sectors'])} secteurs")
    return 0


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
