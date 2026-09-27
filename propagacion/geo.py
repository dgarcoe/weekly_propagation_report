"""Utilidades geográficas: locators Maidenhead, distancias y continentes."""
from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0

CONTINENTES = {
    "EU": "Europa",
    "NA": "Norteamérica",
    "SA": "Sudamérica",
    "AF": "África",
    "AS": "Asia",
    "OC": "Oceanía",
    "AN": "Antártida",
}


def locator_to_latlon(loc: str) -> tuple[float, float]:
    """Centro de la cuadrícula Maidenhead (2, 4, 6 u 8 caracteres) -> (lat, lon)."""
    loc = loc.strip()
    if len(loc) < 2 or len(loc) % 2 or len(loc) > 8:
        raise ValueError(f"locator no válido: {loc!r}")
    loc = loc[:2].upper() + loc[2:4] + loc[4:6].lower() + loc[6:8]
    a, b = ord(loc[0]) - 65, ord(loc[1]) - 65
    if not (0 <= a < 18 and 0 <= b < 18):
        raise ValueError(f"locator no válido: {loc!r}")
    lon, lat = -180.0 + a * 20, -90.0 + b * 10
    size_lon, size_lat = 20.0, 10.0
    if len(loc) >= 4:
        c, d = int(loc[2]), int(loc[3])
        lon += c * 2
        lat += d * 1
        size_lon, size_lat = 2.0, 1.0
    if len(loc) >= 6:
        e, f = ord(loc[4]) - 97, ord(loc[5]) - 97
        if not (0 <= e < 24 and 0 <= f < 24):
            raise ValueError(f"locator no válido: {loc!r}")
        lon += e * (2 / 24)
        lat += f * (1 / 24)
        size_lon, size_lat = 2 / 24, 1 / 24
    if len(loc) == 8:
        g, h = int(loc[6]), int(loc[7])
        lon += g * (2 / 240)
        lat += h * (1 / 240)
        size_lon, size_lat = 2 / 240, 1 / 240
    return lat + size_lat / 2, lon + size_lon / 2


def latlon_to_locator(lat: float, lon: float, precision: int = 6) -> str:
    lon += 180
    lat += 90
    out = chr(65 + int(lon // 20)) + chr(65 + int(lat // 10))
    if precision >= 4:
        out += str(int((lon % 20) // 2)) + str(int(lat % 10))
    if precision >= 6:
        out += chr(97 + int((lon % 2) * 12)) + chr(97 + int((lat % 1) * 24))
    return out


def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia de círculo máximo (fórmula del haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Rumbo inicial (azimut) de 1 hacia 2, en grados 0-360."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def distance_from_locator(loc_a: str, loc_b: str) -> float:
    return great_circle_km(*locator_to_latlon(loc_a), *locator_to_latlon(loc_b))


def continent(lat: float, lon: float) -> str:
    """Continente aproximado (criterio DXCC) a partir de coordenadas.

    Es una clasificación gruesa por cajas, suficiente para agrupar rutas;
    puede fallar en islas fronterizas.
    """
    if lat < -60:
        return "AN"
    # Oceanía: Australia, Indonesia, Filipinas, Pacífico (incl. Hawái).
    if (lat < 0 and lon >= 95) or (-12 <= lat < 20 and lon >= 115) or (lat < 30 and lon <= -140):
        return "OC"
    # América
    if lon < -30 or (lat > 59 and -75 < lon < -15 and not (lat < 67.5 and lon > -25)):
        if lat < 12.5 and lon > -82 and not (lat > 7 and lon < -77):
            return "SA"
        return "NA"
    # África
    if lat < 37.5 and -26 < lon < 60:
        levante_arabia = (lon > 32.5 and lat > 29.5) or (lon >= 34.5 and lat > 12)
        islas_med = lat > 34.8 and 11.1 < lon < 30
        iberia_sur = lat > 35.95 and -10 < lon < 10
        oceano_indico_norte = lon >= 52 and lat >= 0
        if not (levante_arabia or islas_med or iberia_sur or oceano_indico_norte):
            return "AF"
    # Europa vs Asia
    if lon > 60:
        return "AS"
    if (lon > 29.5 and lat < 42) or (lon > 38 and lat < 44) or lat < 34.8:
        return "AS"
    return "EU"


def continent_from_locator(loc: str) -> str:
    return continent(*locator_to_latlon(loc))
