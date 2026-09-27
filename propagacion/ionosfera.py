"""Análisis de ionosondas (GIRO/DIDBase): control de calidad, perfiles horarios,
interpolación a la latitud de Vigo, LUF por absorción, esporádica E y anomalías.

Solo cálculos: las descargas están en ``sources/giro.py``.
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

from . import solar


@dataclass
class Medida:
    """Un ionograma escalado: instante, confianza (CS) y magnitudes (None = sin valor)."""
    time: datetime
    cs: int
    valores: dict[str, float | None] = field(default_factory=dict)

    def get(self, car: str) -> float | None:
        return self.valores.get(car)


# --- Control de calidad ----------------------------------------------------------------

CS_MINIMO = 70           # confianza del autoescalado ARTIST (999 = escalado manual)

# Desviación máxima respecto a la mediana de los vecinos (±60 min) para no ser atípico:
# (tolerancia absoluta, tolerancia relativa). Se usa la mayor de las dos.
TOLERANCIAS = {
    "foF2": (1.0, 0.20),
    "foF1": (0.7, 0.20),
    "MUF(D)": (3.0, 0.20),
    "M(D)": (0.3, 0.12),
    "hmF2": (50.0, 0.20),
    "fmin": (0.8, 0.40),
    "foEs": (2.0, 0.60),     # la Es es muy variable de verdad: solo quitamos saltos absurdos
}


def filtrar_confianza(medidas: list[Medida], cs_min: int = CS_MINIMO) -> list[Medida]:
    return [m for m in medidas if m.cs >= cs_min]


def quitar_atipicos(medidas: list[Medida], car: str, ventana_min: int = 60,
                    minimo_vecinos: int = 2) -> list[tuple[datetime, float]]:
    """Serie (t, valor) de ``car`` sin valores atípicos.

    Un valor se descarta si se aleja de la mediana de sus vecinos (±``ventana_min``)
    más que la tolerancia de esa magnitud, o si está aislado (sin vecinos con valor):
    los errores del autoescalado suelen ser picos sueltos.
    """
    serie = sorted((m.time, v) for m in medidas if (v := m.get(car)) is not None)
    if not serie:
        return []
    tabs, trel = TOLERANCIAS.get(car, (math.inf, math.inf))
    tiempos = np.array([t.timestamp() for t, _ in serie])
    valores = np.array([v for _, v in serie])
    w = ventana_min * 60
    out = []
    for i, (t, v) in enumerate(serie):
        lo = np.searchsorted(tiempos, tiempos[i] - w, side="left")
        hi = np.searchsorted(tiempos, tiempos[i] + w, side="right")
        vecinos = np.delete(valores[lo:hi], i - lo)
        if len(vecinos) < minimo_vecinos:
            continue
        med = float(np.median(vecinos))
        if abs(v - med) <= max(tabs, trel * abs(med)):
            out.append((t, v))
    return out


FOF1_MAXIMO = 7.0        # MHz: ni en máximo solar pasa de ~6,5


def limpiar(medidas: list[Medida], car: str, cs_min: int = CS_MINIMO) -> list[tuple[datetime, float]]:
    validas = filtrar_confianza(medidas, cs_min)
    if car == "foF1":
        # ARTIST a veces escala mal todo el ionograma (foF2 y foF1 disparadas a la vez):
        # la F1 solo vale si la F2 de ese mismo ionograma pasó el control de calidad,
        # y siempre por debajo de ella.
        fof2_ok = dict(quitar_atipicos(validas, "foF2"))
        validas = [m for m in validas if (v := m.get("foF1")) is not None and v <= FOF1_MAXIMO
                   and m.time in fof2_ok and v < fof2_ok[m.time]]
    return quitar_atipicos(validas, car)


# --- Perfiles horarios --------------------------------------------------------------------

def perfil(serie: list[tuple[datetime, float]], minimo: int = 3) -> dict[int, tuple[float, float, float]]:
    """{hora UTC: (p25, mediana, p75)}; horas con menos de ``minimo`` datos se omiten."""
    por_hora: dict[int, list[float]] = defaultdict(list)
    for t, v in serie:
        por_hora[t.hour].append(v)
    out = {}
    for h, vals in sorted(por_hora.items()):
        if len(vals) >= minimo:
            q = np.percentile(vals, [25, 50, 75])
            out[h] = (float(q[0]), float(q[1]), float(q[2]))
    return out


def mediana_horaria(serie: list[tuple[datetime, float]], minimo: int = 3) -> dict[int, float]:
    return {h: q[1] for h, q in perfil(serie, minimo).items()}


def valor_en_hora(perf: dict[int, float], hora: float) -> float | None:
    """Interpolación lineal circular (24 h) de un perfil horario en una hora fraccionaria."""
    if not perf:
        return None
    hora %= 24
    h0 = int(math.floor(hora))
    h1 = (h0 + 1) % 24
    if h0 in perf and h1 in perf:
        f = hora - h0
        return perf[h0] * (1 - f) + perf[h1] * f
    if h0 in perf and hora - h0 < 0.5:
        return perf[h0]
    if h1 in perf and hora - h0 >= 0.5:
        return perf[h1]
    return None


def a_hora_local_de(perf: dict[int, float], lon_estacion: float, lon_destino: float
                    ) -> dict[int, float]:
    """Traslada un perfil horario (UTC) de una estación a la misma hora solar local
    en otra longitud: el valor de las h UTC en destino es el de la estación a las
    h + (lon_destino − lon_estación)/15 UTC."""
    desfase = (lon_destino - lon_estacion) / 15.0
    out = {}
    for h in range(24):
        v = valor_en_hora(perf, h + desfase)
        if v is not None:
            out[h] = v
    return out


def interpolar_latitud(puntos: list[tuple[float, float]], lat: float,
                       max_extrapolacion: float = 3.0) -> float | None:
    """Valor en ``lat`` a partir de (latitud, valor) de varias estaciones.

    Con dos o más estaciones ajusta una recta por mínimos cuadrados (el gradiente
    latitudinal de foF2 es suave a escala de unos pocos grados). Si ``lat`` queda
    fuera del rango cubierto más de ``max_extrapolacion`` grados, usa la estación
    más próxima.
    """
    if not puntos:
        return None
    if len(puntos) == 1:
        return puntos[0][1]
    lats = np.array([p[0] for p in puntos])
    vals = np.array([p[1] for p in puntos])
    if lat < lats.min() - max_extrapolacion or lat > lats.max() + max_extrapolacion:
        return float(vals[np.argmin(np.abs(lats - lat))])
    b, a = np.polyfit(lats, vals, 1)
    return float(a + b * lat)


def perfil_interpolado(perfiles: dict[str, dict[int, float]], estaciones: dict[str, tuple[float, float]],
                       lat: float, lon: float) -> dict[int, float]:
    """Combina perfiles horarios de varias estaciones en uno para (lat, lon).

    ``estaciones``: código -> (lat, lon). Primero lleva cada perfil a la hora
    local del destino y luego interpola en latitud hora a hora.
    """
    locales = {c: a_hora_local_de(p, estaciones[c][1], lon) for c, p in perfiles.items() if p}
    out = {}
    for h in range(24):
        puntos = [(estaciones[c][0], p[h]) for c, p in locales.items() if h in p]
        v = interpolar_latitud(puntos, lat)
        if v is not None:
            out[h] = v
    return out


# --- MUF y LUF ----------------------------------------------------------------------------

ALTURA_CAPA_D_KM = 90.0


def luf_absorcion(fmin: float, distancia_km: float) -> float:
    """LUF aproximada a partir de fmin (frecuencia mínima del ionograma vertical).

    La absorción no desviativa en la capa D crece con la secante del ángulo con que
    la atraviesa la señal y cae con 1/f². A igual absorción que la del sondeo
    vertical: f_LUF ≈ fmin · √sec(φ_D). Es una estimación: fmin depende también de
    la sensibilidad de la ionosonda y del ruido local.
    """
    return fmin * math.sqrt(solar.sec_incidence(distancia_km, ALTURA_CAPA_D_KM))


def estado_banda(f: float, muf: float | None, luf: float | None, margen: float = 0.9) -> str:
    """'abierta' | 'muf' (la MUF no llega) | 'absorcion' (MUF bien, pero la D la cierra)."""
    if muf is None or muf * margen < f:
        return "muf"
    if luf is not None and luf >= f:
        return "absorcion"
    return "abierta"


# --- Esporádica E -------------------------------------------------------------------------

FACTOR_MUF_ES = 5.0      # MUF de la Es para un salto de 1500-2000 km ≈ 5 · foEs


@dataclass
class EpisodioEs:
    inicio: datetime
    fin: datetime
    foes_max: float

    @property
    def muf_max(self) -> float:
        return self.foes_max * FACTOR_MUF_ES


def episodios_es(serie: list[tuple[datetime, float]], umbral: float,
                 hueco_max_min: int = 30) -> list[EpisodioEs]:
    """Agrupa las medidas con foEs ≥ ``umbral`` en episodios (huecos ≤ ``hueco_max_min``)."""
    altos = sorted((t, v) for t, v in serie if v >= umbral)
    out: list[EpisodioEs] = []
    for t, v in altos:
        if out and t - out[-1].fin <= timedelta(minutes=hueco_max_min):
            out[-1].fin = t
            out[-1].foes_max = max(out[-1].foes_max, v)
        else:
            out.append(EpisodioEs(t, t, v))
    return out


# --- Comparación con lo normal ---------------------------------------------------------------

def desviacion_relativa(serie: list[tuple[datetime, float]], referencia: dict[int, float]
                        ) -> list[tuple[datetime, float]]:
    """(t, % respecto a la mediana de referencia de esa hora UTC)."""
    out = []
    for t, v in serie:
        ref = referencia.get(t.hour)
        if ref:
            out.append((t, 100.0 * (v - ref) / ref))
    return out


def desviacion_horaria(desv: list[tuple[datetime, float]]) -> list[tuple[datetime, float]]:
    """Mediana por hora (t truncado a la hora) de una serie de desviaciones."""
    por_hora: dict[datetime, list[float]] = defaultdict(list)
    for t, d in desv:
        por_hora[t.replace(minute=0, second=0, microsecond=0)].append(d)
    return [(t, statistics.median(v)) for t, v in sorted(por_hora.items())]


def desviacion_diaria(desv: list[tuple[datetime, float]]) -> dict:
    por_dia: dict = defaultdict(list)
    for t, d in desv:
        por_dia[t.date()].append(d)
    return {d: statistics.median(v) for d, v in sorted(por_dia.items())}


UMBRAL_TORMENTA_NEGATIVA = -20.0     # %


# --- Curiosidades: spread-F y capa F1 ----------------------------------------------------------

def horas_spread_f(medidas: list[Medida], umbral_ff: float = 0.5) -> list[datetime]:
    """Horas (truncadas) con spread-F: rango (QF) presente o dispersión en frecuencia FF ≥ umbral."""
    horas = set()
    for m in filtrar_confianza(medidas):
        qf, ff = m.get("QF"), m.get("FF")
        if (qf is not None and qf > 0) or (ff is not None and ff >= umbral_ff):
            horas.add(m.time.replace(minute=0, second=0, microsecond=0))
    return sorted(horas)
