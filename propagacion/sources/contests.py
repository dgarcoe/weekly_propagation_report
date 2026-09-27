"""Calendario de concursos de WA7BNM (contestcalendar.com) en formato iCalendar.

WA7BNM publica un calendario público de Google con una entrada por cada
concurso y edición (unos 5 MB); se guarda en caché 24 h.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from .. import config
from ..http import FuenteNoDisponible, fetch_text


@dataclass
class Concurso:
    nombre: str
    inicio: datetime
    fin: datetime | None
    url: str


def _unfold(text: str) -> list[str]:
    """RFC 5545: una línea que empieza por espacio continúa la anterior."""
    out: list[str] = []
    for line in text.splitlines():
        if line[:1] in (" ", "\t") and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def _dt(value: str) -> datetime:
    value = value.strip()
    if len(value) == 8:
        return datetime.strptime(value, "%Y%m%d").replace(tzinfo=timezone.utc)
    return datetime.strptime(value.rstrip("Z")[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)


def _texto(v: str) -> str:
    """Deshace los escapes de iCalendar (\\, \\; \\n) y las entidades HTML."""
    v = v.replace("\\n", " ").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")
    return html.unescape(v).strip()


_HREF = re.compile(r'href="([^"]+)"|(https?://\S+)')


def _url(ev: dict[str, str]) -> str:
    if ev.get("URL"):
        return ev["URL"].strip()
    # El calendario de Google de WA7BNM pone el enlace dentro de DESCRIPTION.
    m = _HREF.search(_texto(ev.get("DESCRIPTION", "")))
    return (m.group(1) or m.group(2)) if m else ""


def parse_ics(text: str) -> list[Concurso]:
    out = []
    ev: dict[str, str] | None = None
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            ev = {}
        elif line == "END:VEVENT" and ev is not None:
            try:
                out.append(Concurso(
                    nombre=_texto(ev.get("SUMMARY", "?")),
                    inicio=_dt(ev["DTSTART"]),
                    fin=_dt(ev["DTEND"]) if "DTEND" in ev else None,
                    url=_url(ev),
                ))
            except (KeyError, ValueError):
                pass
            ev = None
        elif ev is not None and ":" in line:
            key, val = line.split(":", 1)
            ev[key.split(";")[0].upper()] = val
    return out


def descargar() -> list[Concurso]:
    eventos = parse_ics(fetch_text(config.URL_CONTEST_ICS, max_age_h=24, timeout=120))
    if not eventos:
        raise FuenteNoDisponible("contestcalendar.com sin eventos")
    return eventos
