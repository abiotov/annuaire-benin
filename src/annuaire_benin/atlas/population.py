"""Populations communales du recensement RGPH-4 (2013).

Source : INSAE (Institut National de la Statistique du Bénin),
chiffres du 4e Recensement Général de la Population et de
l'Habitation, mai 2013. Fichier figé dans le paquet, clés aux noms du
registre. Ces populations servent à la métrique « entreprises pour
1 000 habitants » : sans normalisation, une choroplèthe de volume ne
fait que redessiner la carte de la population.
"""

from __future__ import annotations

import csv
from importlib import resources

EXPECTED_COMMUNES = 77


def load_population() -> dict[str, int]:
    """Population 2013 par commune (nom du registre) ; validée à 77 entrées."""
    source = resources.files("annuaire_benin.atlas").joinpath("population_2013.csv")
    with source.open(encoding="utf-8", newline="") as handle:
        population = {
            row["commune"]: int(row["population_2013"]) for row in csv.DictReader(handle)
        }
    if len(population) != EXPECTED_COMMUNES:
        raise ValueError(
            f"population_2013.csv : {len(population)} communes au lieu de {EXPECTED_COMMUNES}"
        )
    return population
