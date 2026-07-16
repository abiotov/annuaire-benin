"""Étape 2a : déduplication exacte.

Regroupe les lignes brutes strictement identiques sur la clé
(nom canonique, téléphone brut, email normalisé) : c'est le cas des
copies inter-onglets, qui représentent plus de la moitié du fichier
source. Produit la table ``entities`` et relie chaque ligne brute à
son entité (``raw_contacts.entity_id``).

Aucune fusion approximative ici : deux fiches ne sont regroupées que
si leurs trois champs clés coïncident exactement après normalisation.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from annuaire_benin.dedupe import names

ENTITY_SCHEMA = """
DROP TABLE IF EXISTS entities;
CREATE TABLE entities (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,      -- nom canonique (le plus long des membres)
    name_norm    TEXT NOT NULL,
    phone_raw    TEXT,
    phone_e164   TEXT,               -- NULL si le numéro est tronqué ou invalide
    phone_status TEXT,
    email_norm   TEXT,
    communes     TEXT NOT NULL,      -- listes JSON triées
    quartiers    TEXT NOT NULL,
    segments     TEXT NOT NULL,
    sheets       TEXT NOT NULL,
    member_rows  INTEGER NOT NULL,   -- nb de lignes brutes regroupées
    cluster_id   INTEGER             -- rempli par l'étape 2b
);
CREATE INDEX idx_entities_name_norm ON entities (name_norm);
CREATE INDEX idx_entities_phone ON entities (phone_e164);
CREATE INDEX idx_entities_email ON entities (email_norm);
"""


@dataclass
class _Group:
    """Agrégat d'un groupe de lignes strictement identiques."""

    name: str = ""
    phone_raw: str | None = None
    phone_e164: str | None = None
    phone_status: str | None = None
    email_norm: str | None = None
    communes: set = field(default_factory=set)
    quartiers: set = field(default_factory=set)
    segments: set = field(default_factory=set)
    sheets: set = field(default_factory=set)
    row_ids: list = field(default_factory=list)


def build_entities(connection: sqlite3.Connection) -> int:
    """Construit ``entities`` depuis ``raw_contacts`` ; retourne leur nombre."""
    groups: dict[tuple[str, str, str], _Group] = {}

    query = (
        "SELECT id, name, phone_raw, phone_e164, phone_status, email_norm,"
        " commune, quartier, segment, sheet FROM raw_contacts"
    )
    for (
        row_id, name, phone_raw, phone_e164, phone_status, email_norm,
        commune, quartier, segment, sheet,
    ) in connection.execute(query):
        key = (names.normalize(name), phone_raw or "", email_norm or "")
        group = groups.setdefault(key, _Group())
        if name and len(name) > len(group.name):
            group.name = name
        group.phone_raw = group.phone_raw or phone_raw
        group.email_norm = group.email_norm or email_norm
        if phone_e164 and not group.phone_e164:
            group.phone_e164, group.phone_status = phone_e164, phone_status
        elif not group.phone_status:
            group.phone_status = phone_status
        for target, value in (
            (group.communes, commune), (group.quartiers, quartier),
            (group.segments, segment), (group.sheets, sheet),
        ):
            if value:
                target.add(value)
        group.row_ids.append(row_id)

    connection.executescript(ENTITY_SCHEMA)
    insert_sql = (
        "INSERT INTO entities (id, name, name_norm, phone_raw, phone_e164, phone_status,"
        " email_norm, communes, quartiers, segments, sheets, member_rows)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    member_updates = []
    for entity_id, ((name_norm, _, _), group) in enumerate(groups.items(), start=1):
        connection.execute(insert_sql, (
            entity_id, group.name, name_norm, group.phone_raw, group.phone_e164,
            group.phone_status, group.email_norm,
            json.dumps(sorted(group.communes)), json.dumps(sorted(group.quartiers)),
            json.dumps(sorted(group.segments)), json.dumps(sorted(group.sheets)),
            len(group.row_ids),
        ))
        member_updates.extend((entity_id, row_id) for row_id in group.row_ids)

    columns = [row[1] for row in connection.execute("PRAGMA table_info(raw_contacts)")]
    if "entity_id" not in columns:
        connection.execute("ALTER TABLE raw_contacts ADD COLUMN entity_id INTEGER")
    connection.executemany(
        "UPDATE raw_contacts SET entity_id = ? WHERE id = ?", member_updates
    )
    connection.commit()
    return len(groups)
