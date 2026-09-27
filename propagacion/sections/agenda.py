"""Sección 4 · Agenda y efemérides: concursos, lluvias de meteoros y satélites."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .. import config, geo
from ..http import FuenteNoDisponible
from ..periodo import Periodo, fecha_corta
from ..sources import celestrak, contests

log = logging.getLogger(__name__)

FUENTES = {
    "contests": "WA7BNM Contest Calendar (https://www.contestcalendar.com/)",
    "imo": "International Meteor Organization — calendario de lluvias (https://www.imo.net/)",
    "celestrak": "CelesTrak — TLE de satélites de radioaficionado (https://celestrak.org/)",
    "amsat": "AMSAT — TLE de satélites de radioaficionado (https://www.amsat.org/)",
}
TZ_LOCAL = ZoneInfo("Europe/Madrid")


# --- Lluvias de meteoros ---------------------------------------------------------------
# (nombre, inicio (mes, día), máximo (mes, día), fin (mes, día), THZ, nota)
# Fechas aproximadas del calendario de la IMO; el máximo puede variar ±1 día según el año.

@dataclass(frozen=True)
class Lluvia:
    nombre: str
    inicio: tuple[int, int]
    maximo: tuple[int, int]
    fin: tuple[int, int]
    thz: int
    nota: str = ""


LLUVIAS = (
    Lluvia("Cuadrántidas", (12, 28), (1, 3), (1, 12), 110, "máximo corto (~6 h)"),
    Lluvia("Líridas", (4, 14), (4, 22), (4, 30), 18),
    Lluvia("η-Acuáridas", (4, 19), (5, 6), (5, 28), 50),
    Lluvia("Aríetidas (diurna)", (5, 14), (6, 7), (6, 24), 30,
           "diurna: invisible a simple vista, ideal para radio"),
    Lluvia("ζ-Perseidas (diurna)", (5, 20), (6, 9), (7, 5), 20, "diurna"),
    Lluvia("δ-Acuáridas del sur", (7, 12), (7, 31), (8, 23), 25),
    Lluvia("Perseidas", (7, 17), (8, 12), (8, 24), 100, "la gran cita del verano en 6 m/2 m"),
    Lluvia("Dracónidas", (10, 6), (10, 8), (10, 10), 10, "variable, a veces estallidos"),
    Lluvia("Oriónidas", (10, 2), (10, 21), (11, 7), 20),
    Lluvia("Leónidas", (11, 6), (11, 17), (11, 30), 15),
    Lluvia("Gemínidas", (12, 4), (12, 14), (12, 20), 150, "la más intensa del año"),
    Lluvia("Úrsidas", (12, 17), (12, 22), (12, 26), 10),
)


def _fecha(anio: int, md: tuple[int, int]) -> date:
    return date(anio, *md)


def rango_lluvia(ll: Lluvia, anio: int) -> tuple[date, date, date]:
    """Inicio, máximo y fin para la edición cuyo máximo cae en ``anio``
    (maneja las que cruzan el cambio de año, como las Cuadrántidas)."""
    maximo = _fecha(anio, ll.maximo)
    inicio = _fecha(anio if ll.inicio <= ll.maximo else anio - 1, ll.inicio)
    fin = _fecha(anio if ll.fin >= ll.maximo else anio + 1, ll.fin)
    return inicio, maximo, fin


def lluvias_activas(desde: date, hasta: date, horizonte_dias: int = 30) -> list[dict]:
    """Lluvias activas entre ``desde`` y ``hasta`` o con máximo en los próximos días."""
    out = []
    for ll in LLUVIAS:
        for anio in (desde.year - 1, desde.year, desde.year + 1):
            ini, mx, fin = rango_lluvia(ll, anio)
            activa = ini <= hasta and fin >= desde
            proxima = desde <= mx <= desde + timedelta(days=horizonte_dias)
            if activa or proxima:
                out.append({"nombre": ll.nombre, "maximo": mx, "maximo_txt": fecha_corta(mx),
                            "activa": activa, "thz": ll.thz, "nota": ll.nota,
                            "dias_al_max": (mx - desde).days})
    return sorted(out, key=lambda x: x["maximo"])


# --- Concursos ------------------------------------------------------------------------------

def fin_de_semana(p: Periodo) -> tuple[datetime, datetime]:
    """Del viernes 12 UTC al lunes 00 UTC de la semana siguiente al informe."""
    viernes = p.sig_inicio + timedelta(days=4)
    ini = datetime.combine(viernes, time(12), tzinfo=timezone.utc)
    return ini, ini + timedelta(hours=60)


def concursos_finde(eventos: list[contests.Concurso], p: Periodo) -> list[dict]:
    ini, fin = fin_de_semana(p)
    out = []
    for e in eventos:
        e_fin = e.fin or e.inicio + timedelta(hours=1)
        if e.inicio < fin and e_fin > ini:
            out.append({
                "nombre": e.nombre,
                "inicio": f"{fecha_corta(e.inicio.date())} {e.inicio:%H:%M}",
                "fin": f"{fecha_corta(e_fin.date())} {e_fin:%H:%M}",
                "horas": round((e_fin - e.inicio).total_seconds() / 3600),
                "url": e.url,
                "_t": e.inicio,
            })
    out.sort(key=lambda x: x["_t"])
    for x in out:
        del x["_t"]
    return out


# --- Satélites ---------------------------------------------------------------------------

def pases_satelites(tles: list[tuple[str, str, str]], inicio: date, dias: int = 7,
                    elev_min: float = 30.0, por_sat: int = 3) -> list[dict]:
    """Mejores pases (elevación máxima ≥ ``elev_min``) sobre Vigo, por satélite."""
    from skyfield.api import EarthSatellite, load, wgs84

    ts = load.timescale(builtin=True)
    lat, lon = geo.locator_to_latlon(config.STATION_LOCATOR)
    vigo = wgs84.latlon(lat, lon, elevation_m=50)
    t0 = ts.utc(inicio.year, inicio.month, inicio.day)
    t1 = ts.utc(inicio.year, inicio.month, inicio.day + dias)
    out = []
    for nombre, l1, l2 in tles:
        sat = EarthSatellite(l1, l2, nombre, ts)
        # Un TLE de hace semanas da horas de paso poco fiables: lo descartamos.
        if abs(t0 - sat.epoch) > 14:
            continue
        t, ev = sat.find_events(vigo, t0, t1, altitude_degrees=0.0)
        pases = []
        actual: dict = {}
        for ti, e in zip(t, ev):
            if e == 0:
                actual = {"aos": ti}
            elif e == 1 and actual:
                alt, az, _ = (sat - vigo).at(ti).altaz()
                actual.update(tca=ti, elev=alt.degrees)
            elif e == 2 and "tca" in actual:
                actual["los"] = ti
                pases.append(actual)
                actual = {}
        buenos = sorted((x for x in pases if x["elev"] >= elev_min), key=lambda x: -x["elev"])
        for x in sorted(buenos[:por_sat], key=lambda x: x["aos"].tt):
            aos = x["aos"].utc_datetime()
            los = x["los"].utc_datetime()
            out.append({
                "satelite": nombre,
                "dia": fecha_corta(aos.date()),
                "aos": f"{aos:%H:%M}",
                "los": f"{los:%H:%M}",
                "local": f"{aos.astimezone(TZ_LOCAL):%H:%M}",
                "elev": round(x["elev"]),
                "duracion": round((los - aos).total_seconds() / 60),
                "_t": aos,
            })
    out.sort(key=lambda x: x["_t"])
    for x in out:
        del x["_t"]
    return out


def construir(p: Periodo) -> dict:
    res: dict = {"ok": True, "fuentes": [], "avisos": []}
    try:
        res["concursos"] = concursos_finde(contests.descargar(p.sig_inicio), p)
        res["fuentes"].append(FUENTES["contests"])
    except FuenteNoDisponible as e:
        log.warning("Concursos: %s", e)
        res["concursos"] = None
    res["lluvias"] = lluvias_activas(p.sig_inicio, p.sig_fin)
    res["fuentes"].append(FUENTES["imo"])
    try:
        tles, fuente = celestrak.descargar()
        res["satelites"] = pases_satelites(celestrak.select(tles), p.sig_inicio)
        res["fuentes"].append(FUENTES[fuente])
    except FuenteNoDisponible as e:
        log.warning("CelesTrak: %s", e)
        res["satelites"] = None
    return res
