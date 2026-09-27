"""NOAA SWPC: flujo F10.7, índices geomagnéticos, fulguraciones y outlook de 27 días.

Todos los productos son públicos, sin API key. Los parsers aceptan el texto
ya descargado para poder testearlos con ficheros de ejemplo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from .. import config
from ..http import FuenteNoDisponible, fetch_json, fetch_text


@dataclass
class DiaSolar:
    fecha: date
    sfi: float | None
    ssn: int | None
    flares_c: int = 0
    flares_m: int = 0
    flares_x: int = 0


@dataclass
class DiaGeomag:
    fecha: date
    ap: int | None
    kp: list[float] = field(default_factory=list)   # 8 valores trihorarios

    @property
    def kp_max(self) -> float | None:
        vals = [k for k in self.kp if k is not None and k >= 0]
        return max(vals) if vals else None


@dataclass
class Fulguracion:
    inicio: datetime
    maximo: datetime | None
    clase: str


@dataclass
class DiaOutlook:
    fecha: date
    sfi: int
    ap: int
    kp_max: int


def _num(tok: str) -> float | None:
    try:
        v = float(tok)
    except ValueError:
        return None
    return None if v < 0 else v


# --- daily-solar-indices.txt (DSD) --------------------------------------------

_LINE_DATE = re.compile(r"^\s*(\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+(.*)$")


def parse_dsd(text: str) -> list[DiaSolar]:
    """Columnas: año mes día flujo SSN área regiones_nuevas campo fondo_rayosX C M X S 1 2 3."""
    out = []
    for line in text.splitlines():
        if line.startswith((":", "#")):
            continue
        m = _LINE_DATE.match(line)
        if not m:
            continue
        rest = m.group(4).split()
        if len(rest) < 2:
            continue
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        sfi = _num(rest[0])
        ssn = _num(rest[1])
        c = mm = x = 0
        # Las 7 últimas columnas son siempre C M X S 1 2 3 (recuentos de fulguraciones).
        if len(rest) >= 9:
            try:
                c, mm, x = (max(0, int(v)) for v in rest[-7:-4])
            except ValueError:
                pass
        out.append(DiaSolar(d, sfi, int(ssn) if ssn is not None else None, c, mm, x))
    return out


# --- daily-geomagnetic-indices.txt (DGD) --------------------------------------

def parse_dgd(text: str) -> list[DiaGeomag]:
    """Columnas: fecha, A+8K Fredericksburg, A+8K College, Ap+8Kp planetario."""
    out = []
    for line in text.splitlines():
        if line.startswith((":", "#")):
            continue
        m = _LINE_DATE.match(line)
        if not m:
            continue
        toks = m.group(4).split()
        if len(toks) < 27:
            continue
        plan = toks[-9:]
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        ap = _num(plan[0])
        kp = [_num(t) for t in plan[1:]]
        out.append(DiaGeomag(d, int(ap) if ap is not None else None,
                             [k for k in kp if k is not None]))
    return out


# --- noaa-planetary-k-index.json ----------------------------------------------

def parse_kp_json(data) -> list[tuple[datetime, float]]:
    """Acepta tanto la forma «lista de listas con cabecera» como «lista de objetos»."""
    rows: list[tuple[datetime, float]] = []
    if not data:
        return rows
    if isinstance(data[0], list):
        header = [h.lower() for h in data[0]]
        it = (dict(zip(header, r)) for r in data[1:])
    else:
        it = ({k.lower(): v for k, v in r.items()} for r in data)
    for r in it:
        t = r.get("time_tag")
        kp = r.get("kp", r.get("kp_index", r.get("estimated_kp")))
        if t is None or kp is None:
            continue
        try:
            rows.append((datetime.fromisoformat(str(t).replace("Z", "")), float(kp)))
        except ValueError:
            continue
    return rows


# --- xray-flares-7-day.json ---------------------------------------------------

def parse_flares_json(data) -> list[Fulguracion]:
    out = []
    for r in data or []:
        cls = r.get("max_class") or r.get("current_class") or ""
        begin = r.get("begin_time") or r.get("time_tag")
        if not cls or not begin:
            continue
        try:
            t0 = datetime.fromisoformat(begin.replace("Z", ""))
            tm = r.get("max_time")
            t1 = datetime.fromisoformat(tm.replace("Z", "")) if tm else None
        except ValueError:
            continue
        out.append(Fulguracion(t0, t1, cls.strip()))
    return out


# --- 27-day-outlook.txt --------------------------------------------------------

_27DO = re.compile(r"^\s*(\d{4})\s+([A-Za-z]{3})\s+(\d{1,2})\s+(\d+)\s+(\d+)\s+(\d+)")


def parse_27do(text: str) -> list[DiaOutlook]:
    out = []
    for line in text.splitlines():
        m = _27DO.match(line)
        if not m:
            continue
        d = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%Y %b %d").date()
        out.append(DiaOutlook(d, int(m.group(4)), int(m.group(5)), int(m.group(6))))
    return out


# --- ciclo solar (mensual) -------------------------------------------------------

def parse_cycle_json(data) -> list[tuple[date, float | None, float | None]]:
    """(mes, F10.7 mensual, SSN suavizado) del JSON observed-solar-cycle-indices."""
    out = []
    for r in data or []:
        tag = r.get("time-tag") or r.get("time_tag")
        if not tag:
            continue
        try:
            y, mo = (int(x) for x in str(tag)[:7].split("-"))
        except ValueError:
            continue
        f107 = r.get("f10.7")
        ssn = r.get("smoothed_ssn")
        out.append((date(y, mo, 15),
                    float(f107) if f107 not in (None, -1) else None,
                    float(ssn) if ssn not in (None, -1) else None))
    return out


def parse_predicted_json(data) -> dict[tuple[int, int], float]:
    """{(año, mes): SSN suavizado previsto} del JSON predicted-solar-cycle."""
    out = {}
    for r in data or []:
        tag = r.get("time-tag") or r.get("time_tag")
        ssn = r.get("predicted_ssn")
        if not tag or ssn is None:
            continue
        try:
            y, mo = (int(x) for x in str(tag)[:7].split("-"))
            out[(y, mo)] = float(ssn)
        except ValueError:
            continue
    return out


# --- descargas ----------------------------------------------------------------

def descargar_dsd() -> list[DiaSolar]:
    dias = parse_dsd(fetch_text(config.URL_NOAA_DSD))
    if not dias:
        raise FuenteNoDisponible("NOAA DSD sin filas")
    return dias


def descargar_dgd() -> list[DiaGeomag]:
    dias = parse_dgd(fetch_text(config.URL_NOAA_DGD))
    if not dias:
        raise FuenteNoDisponible("NOAA DGD sin filas")
    return dias


def descargar_kp() -> list[tuple[datetime, float]]:
    return parse_kp_json(fetch_json(config.URL_NOAA_KP))


def descargar_fulguraciones() -> list[Fulguracion]:
    return parse_flares_json(fetch_json(config.URL_NOAA_FLARES))


def descargar_27do() -> list[DiaOutlook]:
    dias = parse_27do(fetch_text(config.URL_NOAA_27DO))
    if not dias:
        raise FuenteNoDisponible("NOAA 27-day outlook sin filas")
    return dias


def descargar_ciclo():
    return parse_cycle_json(fetch_json(config.URL_NOAA_CYCLE, max_age_h=48))


def descargar_prediccion_ciclo():
    return parse_predicted_json(fetch_json(config.URL_NOAA_CYCLE_PRED, max_age_h=48))
