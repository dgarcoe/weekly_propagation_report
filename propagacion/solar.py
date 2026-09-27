"""Cálculos puros: SSN efectivo, semáforo geomagnético, orto/ocaso y MUF.

Sin dependencias de red para que sean fáciles de testear.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone


# --- Índices solares ---------------------------------------------------------

SFI_VALIDO_MIN = 70.0
SFI_VALIDO_MAX = 250.0


def ssn_from_sfi(sfi: float) -> float:
    """SSN efectivo aproximado: SSN ≈ 1,14·SFI − 73,2 (válida ~70-250 SFI).

    Se recorta a 0 por abajo porque un número de manchas negativo no tiene sentido.
    """
    return max(0.0, 1.14 * sfi - 73.2)


def ssn_formula_valida(sfi: float) -> bool:
    return SFI_VALIDO_MIN <= sfi <= SFI_VALIDO_MAX


@dataclass(frozen=True)
class Semaforo:
    nivel: str      # "tranquilo" | "inquieto" | "tormenta"
    emoji: str
    texto: str


def semaforo_kp(kp: float) -> Semaforo:
    """≤3 tranquilo, 4 inquieto, ≥5 tormenta (G1 o superior)."""
    if kp >= 5:
        g = min(5, int(math.floor(kp)) - 4)
        return Semaforo("tormenta", "🔴", f"tormenta geomagnética (G{g})")
    if kp >= 4:
        return Semaforo("inquieto", "🟡", "inquieto")
    return Semaforo("tranquilo", "🟢", "tranquilo")


def tendencia(actual: float, anterior: float | None, umbral_pct: float = 3.0) -> str:
    if anterior is None or anterior == 0:
        return "sin referencia"
    delta = 100 * (actual - anterior) / anterior
    if delta > umbral_pct:
        return f"al alza (+{delta:.0f} %)"
    if delta < -umbral_pct:
        return f"a la baja ({delta:.0f} %)"
    return f"estable ({delta:+.0f} %)"


def flare_class_value(cls: str) -> float:
    """'M2.5' -> 2.5e-5 W/m² (útil para ordenar fulguraciones)."""
    cls = cls.strip().upper()
    base = {"A": 1e-8, "B": 1e-7, "C": 1e-6, "M": 1e-5, "X": 1e-4}[cls[0]]
    try:
        return base * float(cls[1:] or 1)
    except ValueError:
        return base


# --- MUF ---------------------------------------------------------------------

def sec_incidence(distance_km: float, height_km: float = 300.0) -> float:
    """sec(φ) para un salto de ``distance_km`` reflejado a ``height_km``.

    Incluye la curvatura terrestre (geometría esférica simple).
    """
    R = 6371.0
    if distance_km <= 0:
        return 1.0
    theta = distance_km / (2 * R)          # medio ángulo central
    # Ángulo de elevación en tierra
    elev = math.atan2(math.cos(theta) - R / (R + height_km), math.sin(theta))
    # Ángulo de incidencia en la capa (ley de los senos)
    sin_phi = R * math.cos(elev) / (R + height_km)
    return 1.0 / math.sqrt(1 - sin_phi ** 2)


def muf_one_hop(fof2: float, distance_km: float, height_km: float = 300.0) -> float:
    """MUF de un salto ≈ foF2 · sec(φ) (ley de la secante)."""
    return fof2 * sec_incidence(distance_km, height_km)


# --- Orto y ocaso (algoritmo NOAA) ---------------------------------------------

def _julian_day(d: date) -> float:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() / 86400.0 + 2440587.5


def _sun_eq(jd: float) -> tuple[float, float]:
    """Declinación (rad) y ecuación del tiempo (min) para el día juliano ``jd``."""
    t = (jd - 2451545.0) / 36525.0
    l0 = math.radians((280.46646 + t * (36000.76983 + t * 0.0003032)) % 360)
    m = math.radians(357.52911 + t * (35999.05029 - 0.0001537 * t))
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    c = (math.sin(m) * (1.914602 - t * (0.004817 + 0.000014 * t))
         + math.sin(2 * m) * (0.019993 - 0.000101 * t) + math.sin(3 * m) * 0.000289)
    true_long = l0 + math.radians(c)
    omega = math.radians(125.04 - 1934.136 * t)
    app_long = true_long - math.radians(0.00569 + 0.00478 * math.sin(omega))
    eps0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60
    eps = math.radians(eps0 + 0.00256 * math.cos(omega))
    decl = math.asin(math.sin(eps) * math.sin(app_long))
    y = math.tan(eps / 2) ** 2
    eqt = 4 * math.degrees(
        y * math.sin(2 * l0) - 2 * e * math.sin(m) + 4 * e * y * math.sin(m) * math.cos(2 * l0)
        - 0.5 * y * y * math.sin(4 * l0) - 1.25 * e * e * math.sin(2 * m))
    return decl, eqt


def sun_events(lat: float, lon: float, d: date, zenith: float = 90.833
               ) -> tuple[datetime | None, datetime | None]:
    """Orto y ocaso (UTC) para ``d`` en (lat, lon).

    Devuelve ``(None, None)`` en día o noche polar. Precisión ~1 minuto.
    """
    def event(rising: bool, jd_guess: float) -> datetime | None:
        # Dos iteraciones: calcula la posición del Sol a la hora aproximada del evento.
        minutes = 720.0
        for _ in range(2):
            decl, eqt = _sun_eq(jd_guess + minutes / 1440.0)
            cos_ha = (math.cos(math.radians(zenith)) / (math.cos(math.radians(lat)) * math.cos(decl))
                      - math.tan(math.radians(lat)) * math.tan(decl))
            if not -1 <= cos_ha <= 1:
                return None
            ha = math.degrees(math.acos(cos_ha))
            # Longitud positiva al este: orto = 720 − 4·(lon + H) − EqT; ocaso con −H.
            minutes = 720 - 4 * (lon + (ha if rising else -ha)) - eqt
        base = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        return base + timedelta(minutes=minutes)

    jd = _julian_day(d)
    return event(True, jd), event(False, jd)
