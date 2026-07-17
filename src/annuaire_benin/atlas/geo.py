"""Contours des communes pour l'atlas.

Source : geoBoundaries (gbOpen BEN ADM2, domaine public, version
simplifiée), fichier embarqué dans le paquet. Les 7 écarts
d'orthographe entre le registre et geoBoundaries sont résolus par une
table d'alias explicite ; toute commune non appariée fait échouer la
construction plutôt que de disparaître de la carte.
"""

from __future__ import annotations

import json
import unicodedata
from importlib import resources

# Nom du registre -> shapeName geoBoundaries, pour les 7 écarts d'orthographe.
ALIASES = {
    "SEME-PODJI": "Seme-Kpodji",
    "AKPRO-MISSERETE": "Akpo-Misserete",
    "BOUKOUMBE": "Boukombe",
    "COBLY": "Kobli",
    "KLOUEKANMEY": "Klouekanme",
    "OUASSA-PEHUNCO": "Pehunco",
    "TOUKOUNTOUNA": "Toucountouna",
}


def _norm(name: str) -> str:
    decomposed = unicodedata.normalize("NFD", name.upper())
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return "".join(ch for ch in ascii_only if ch.isalnum())


def load_features() -> list[dict]:
    source = resources.files("annuaire_benin.atlas").joinpath("benin_adm2.geojson")
    with source.open(encoding="utf-8") as handle:
        return json.load(handle)["features"]


def _rings(geometry: dict):
    if geometry["type"] == "Polygon":
        yield from geometry["coordinates"]
    elif geometry["type"] == "MultiPolygon":
        for polygon in geometry["coordinates"]:
            yield from polygon


def match_features(commune_names: list[str]) -> dict[str, dict]:
    """Contour geoBoundaries de chaque commune du registre.

    Lève ValueError si une commune n'a pas de contour : une commune qui
    disparaîtrait de la carte en silence serait un mensonge visuel.
    """
    by_norm = {_norm(f["properties"]["shapeName"]): f for f in load_features()}
    matched: dict[str, dict] = {}
    for name in commune_names:
        feature = by_norm.get(_norm(ALIASES.get(name, name)))
        if feature is None:
            raise ValueError(f"commune sans contour geoBoundaries : {name!r}")
        matched[name] = feature
    return matched


def bounds_of(feature: dict) -> tuple[float, float, float, float]:
    """Emprise (min_lat, min_lon, max_lat, max_lon) d'un contour."""
    lons, lats = [], []
    for ring in _rings(feature["geometry"]):
        for lon, lat in ring:
            lons.append(lon)
            lats.append(lat)
    return min(lats), min(lons), max(lats), max(lons)


def export_geojson(commune_names: list[str], decimals: int = 3) -> dict:
    """FeatureCollection des contours, nommés comme le registre.

    Servie à côté de la page : c'est la couche de données que Leaflet
    dessine par-dessus le fond OpenStreetMap. Coordonnées arrondies :
    ~100 m suffisent largement pour des contours de communes.
    """

    def round_geometry(geometry: dict) -> dict:
        def round_ring(ring):
            return [[round(lon, decimals), round(lat, decimals)] for lon, lat in ring]

        if geometry["type"] == "Polygon":
            coordinates = [round_ring(r) for r in geometry["coordinates"]]
        else:
            coordinates = [
                [round_ring(r) for r in polygon] for polygon in geometry["coordinates"]
            ]
        return {"type": geometry["type"], "coordinates": coordinates}

    features = [
        {
            "type": "Feature",
            "properties": {"name": name},
            "geometry": round_geometry(feature["geometry"]),
        }
        for name, feature in match_features(commune_names).items()
    ]
    return {"type": "FeatureCollection", "features": features}
