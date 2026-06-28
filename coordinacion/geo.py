from __future__ import annotations

import re
from typing import Any

from django.contrib.gis.geos import Point
from django.contrib.gis.geos.error import GEOSException

COORD_RE = re.compile(
    r"^\s*(?P<wkt>POINT\s*\()?\s*"
    r"(?P<a>-?\d+(?:\.\d+)?)"
    r"[\s,;]+"
    r"(?P<b>-?\d+(?:\.\d+)?)"
    r"(?:\s+[-+]?\d+(?:\.\d+)?)?"
    r"\s*\)?\s*$",
    re.IGNORECASE,
)


def _es_latitud(valor: float) -> bool:
    return -90 <= valor <= 90


def _es_longitud(valor: float) -> bool:
    return -180 <= valor <= 180


def crear_point(latitud: float, longitud: float) -> Point:
    return Point(float(longitud), float(latitud), srid=4326)


def point_a_dict(point: Point | None) -> dict[str, Any] | None:
    if not point:
        return None
    return {
        "type": "Point",
        "coordinates": [point.x, point.y],
        "srid": point.srid or 4326,
    }


def normalizar_point(valor: Any) -> Point | None:
    """
    Acepta coordenadas en formatos comunes del cliente offline/KoBo:
    - GeoJSON: {"type": "Point", "coordinates": [lon, lat]}
    - Dict simple: {"lat": 10.5, "lon": -66.9}
    - Lista/tupla: [lon, lat]
    - Texto KoBo geopoint: "lat lon alt accuracy"
    - Texto simple: "lat, lon" o "lat lon"
    - WKT simple: "POINT(lon lat)"
    """
    if valor in (None, ""):
        return None

    if isinstance(valor, Point):
        if valor.srid is None:
            valor.srid = 4326
        return valor

    if isinstance(valor, dict):
        if valor.get("type") == "Point" and "coordinates" in valor:
            coords = valor["coordinates"]
            if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                lon, lat = float(coords[0]), float(coords[1])
                return crear_point(lat, lon)
        lat = valor.get("lat", valor.get("latitude", valor.get("latitud")))
        lon = valor.get("lon", valor.get("lng", valor.get("longitud")))
        if lat is not None and lon is not None:
            return crear_point(float(lat), float(lon))
        return None

    if isinstance(valor, (list, tuple)) and len(valor) >= 2:
        lon, lat = float(valor[0]), float(valor[1])
        return crear_point(lat, lon)

    texto = str(valor).strip()
    if not texto:
        return None

    match = COORD_RE.match(texto)
    if not match:
        return None

    a = float(match.group("a"))
    b = float(match.group("b"))

    # WKT usa lon lat por estándar.
    if match.group("wkt"):
        if _es_longitud(a) and _es_latitud(b):
            return crear_point(b, a)
        return None

    # KoBo geopoint y captura de campo suelen venir como lat lon.
    if _es_latitud(a) and _es_longitud(b):
        return crear_point(a, b)

    # Fallback para valores claramente lon lat.
    if _es_longitud(a) and _es_latitud(b):
        return crear_point(b, a)

    return None


def point_desde_texto(valor: str | None) -> Point | None:
    try:
        return normalizar_point(valor)
    except (TypeError, ValueError, GEOSException):
        return None
