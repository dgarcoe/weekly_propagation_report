"""Calendario de concursos de WA7BNM (contestcalendar.com), vía su feed RSS.

El RSS cubre la semana en curso y el fin de semana siguiente. Cada ``<item>``
trae el nombre, el enlace y el horario en texto, con formatos como:

    0000Z, Sep 26 to 2400Z, Sep 27
    0700Z-1000Z, Sep 27
    0000Z to 2400Z, Oct 2
    0000Z-0100Z, Oct 1 and 0200Z-0300Z, Oct 2
    1700Z-1800Z, Oct 1 (CW) and 1800Z-1900Z, Oct 1 (SSB)

(El calendario de Google que enlaza la web está sin actualizar desde hace años.)
"""
from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from .. import config
from ..http import FuenteNoDisponible, fetch_text

MESES_EN = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


@dataclass
class Concurso:
    nombre: str
    inicio: datetime
    fin: datetime | None
    url: str


# «HHMMZ, Mon DD to HHMMZ, Mon DD»
_RANGO_LARGO = re.compile(
    r"(\d{4})Z,\s*([A-Z][a-z]{2})\s+(\d{1,2})\s+to\s+(\d{4})Z,\s*([A-Z][a-z]{2})\s+(\d{1,2})")
# «HHMMZ-HHMMZ, Mon DD» y «HHMMZ to HHMMZ, Mon DD»
_RANGO_DIA = re.compile(r"(\d{4})Z\s*(?:-|to)\s*(\d{4})Z,\s*([A-Z][a-z]{2})\s+(\d{1,2})")


def _fecha(mes: str, dia: str, ref: date) -> date:
    """Fecha sin año: elige el año que la deja más cerca de ``ref`` (cambio de año)."""
    candidatas = [date(ref.year + k, MESES_EN[mes], int(dia)) for k in (-1, 0, 1)]
    return min(candidatas, key=lambda d: abs((d - ref).days))


def _instante(d: date, hhmm: str) -> datetime:
    """``2400`` es la medianoche del día siguiente."""
    h, m = int(hhmm[:2]), int(hhmm[2:])
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc) + timedelta(hours=h, minutes=m)


def parse_horario(texto: str, ref: date) -> tuple[datetime, datetime] | None:
    """Inicio del primer tramo y fin del último de una descripción de horario."""
    tramos: list[tuple[datetime, datetime]] = []
    for m in _RANGO_LARGO.finditer(texto):
        ini = _instante(_fecha(m.group(2), m.group(3), ref), m.group(1))
        fin = _instante(_fecha(m.group(5), m.group(6), ref), m.group(4))
        tramos.append((ini, fin))
    resto = _RANGO_LARGO.sub(" ", texto)
    for m in _RANGO_DIA.finditer(resto):
        d = _fecha(m.group(3), m.group(4), ref)
        ini, fin = _instante(d, m.group(1)), _instante(d, m.group(2))
        if fin <= ini:                         # p. ej. 2300Z-0100Z: cruza medianoche
            fin += timedelta(days=1)
        tramos.append((ini, fin))
    if not tramos:
        return None
    return min(t[0] for t in tramos), max(t[1] for t in tramos)


def parse_rss(text: str, ref: date) -> list[Concurso]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise FuenteNoDisponible(f"RSS de concursos no válido: {e}") from e
    out = []
    for item in root.iter("item"):
        nombre = html.unescape((item.findtext("title") or "").strip())
        horario = parse_horario(html.unescape(item.findtext("description") or ""), ref)
        if not nombre or horario is None:
            continue
        out.append(Concurso(nombre, horario[0], horario[1], (item.findtext("link") or "").strip()))
    return out


def descargar(ref: date) -> list[Concurso]:
    eventos = parse_rss(fetch_text(config.URL_CONTEST_RSS, max_age_h=12), ref)
    if not eventos:
        raise FuenteNoDisponible("contestcalendar.com: RSS sin concursos")
    return eventos
