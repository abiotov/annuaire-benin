"""Ingestion du fichier source Excel vers une base SQLite.

Lit chaque onglet de données (le tableau de bord est ignoré), normalise
les téléphones et les emails à la volée, et charge le tout dans une
table unique. La base produite est l'entrée de toutes les étapes
suivantes du pipeline (déduplication, classification).

Usage :
    python -m annuaire_benin.ingest CHEMIN/VERS/source.xlsx [--db data/annuaire.db]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

import openpyxl

from annuaire_benin.contacts import emails, phone

DASHBOARD_SHEET = "Tableau de Bord"
BATCH_SIZE = 5_000
EXPECTED_COLUMNS = 7  # Nom, Activité, Commune, Quartier, Téléphone, Email, Segment

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_contacts (
    id            INTEGER PRIMARY KEY,
    sheet         TEXT NOT NULL,      -- onglet d'origine
    row_index     INTEGER NOT NULL,   -- ligne dans l'onglet (1 = première ligne de données)
    name          TEXT,
    activity      TEXT,
    commune       TEXT,
    quartier      TEXT,
    segment       TEXT,
    phone_raw     TEXT,
    phone_e164    TEXT,               -- numéro canonique +22901XXXXXXXX, NULL si invalide
    phone_status  TEXT NOT NULL,
    phone_extra   INTEGER NOT NULL DEFAULT 0,  -- nb de numéros supplémentaires dans la cellule
    email_raw     TEXT,
    email_norm    TEXT,               -- adresse normalisée, NULL si invalide
    email_status  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_raw_contacts_sheet ON raw_contacts (sheet);
CREATE INDEX IF NOT EXISTS idx_raw_contacts_phone ON raw_contacts (phone_e164);
CREATE INDEX IF NOT EXISTS idx_raw_contacts_email ON raw_contacts (email_norm);
"""


def _cell_text(value: object) -> str | None:
    """Ramène une cellule vers du texte épuré, None si vide."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _row_record(sheet: str, row_index: int, row: tuple) -> tuple:
    """Transforme une ligne Excel en enregistrement pour raw_contacts."""
    cells = list(row[:EXPECTED_COLUMNS])
    cells += [None] * (EXPECTED_COLUMNS - len(cells))
    name, activity, commune, quartier, phone_raw, email_raw, segment = cells

    phone_results = phone.extract_all(phone_raw)
    best = next((r for r in phone_results if r.status.is_valid), phone_results[0])
    email_result = emails.normalize(email_raw)

    return (
        sheet,
        row_index,
        _cell_text(name),
        _cell_text(activity),
        _cell_text(commune),
        _cell_text(quartier),
        _cell_text(segment),
        _cell_text(phone_raw),
        best.e164,
        best.status.value,
        len(phone_results) - 1,
        _cell_text(email_raw),
        email_result.normalized,
        email_result.status.value,
    )


def ingest(xlsx_path: Path, db_path: Path) -> None:
    """Charge le classeur Excel dans la base SQLite, puis affiche un bilan."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(SCHEMA)
    connection.execute("DELETE FROM raw_contacts")

    workbook = openpyxl.load_workbook(xlsx_path, read_only=True)
    started = time.perf_counter()
    total = 0
    insert_sql = (
        "INSERT INTO raw_contacts (sheet, row_index, name, activity, commune,"
        " quartier, segment, phone_raw, phone_e164, phone_status, phone_extra,"
        " email_raw, email_norm, email_status)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )

    for sheet in workbook.worksheets:
        if sheet.title == DASHBOARD_SHEET:
            continue
        batch = []
        for index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=1):
            if not row or all(cell is None for cell in row):
                continue
            batch.append(_row_record(sheet.title, index, row))
            if len(batch) >= BATCH_SIZE:
                connection.executemany(insert_sql, batch)
                total += len(batch)
                batch.clear()
        if batch:
            connection.executemany(insert_sql, batch)
            total += len(batch)
        print(f"  {sheet.title}: onglet chargé")

    workbook.close()
    connection.commit()
    elapsed = time.perf_counter() - started
    print(f"\n{total} lignes chargées en {elapsed:.0f} s dans {db_path}\n")
    _print_report(connection)
    connection.close()


def _print_report(connection: sqlite3.Connection) -> None:
    """Affiche la distribution des statuts de validation."""

    def section(title: str, query: str) -> None:
        print(title)
        for label, count in connection.execute(query):
            print(f"  {label:<20} {count:>8}")
        print()

    section(
        "Lignes par onglet :",
        "SELECT sheet, COUNT(*) FROM raw_contacts GROUP BY sheet ORDER BY COUNT(*) DESC",
    )
    section(
        "Statuts téléphone :",
        "SELECT phone_status, COUNT(*) FROM raw_contacts"
        " GROUP BY phone_status ORDER BY COUNT(*) DESC",
    )
    section(
        "Statuts email :",
        "SELECT email_status, COUNT(*) FROM raw_contacts"
        " GROUP BY email_status ORDER BY COUNT(*) DESC",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="classeur Excel source")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/annuaire.db"),
        help="base SQLite de destination (défaut : data/annuaire.db)",
    )
    args = parser.parse_args(argv)

    if not args.source.exists():
        parser.error(f"fichier source introuvable : {args.source}")

    ingest(args.source, args.db)
    return 0


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
