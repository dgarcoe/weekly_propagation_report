"""Calendario de concursos de WA7BNM (contestcalendar.com) en formato iCalendar."""
from __future__ import annotations

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


def parse_ics(text: str) -> list[Concurso]:
    out = []
    ev: dict[str, str] | None = None
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            ev = {}
        elif line == "END:VEVENT" and ev is not None:
            try:
                out.append(Concurso(
                    nombre=ev.get("SUMMARY", "?").replace("\\,", ",").replace("\\;", ";"),
                    inicio=_dt(ev["DTSTART"]),
                    fin=_dt(ev["DTEND"]) if "DTEND" in ev else None,
                    url=ev.get("URL", ""),
                ))
            except (KeyError, ValueError):
                pass
            ev = None
        elif ev is not None and ":" in line:
            key, val = line.split(":", 1)
            ev[key.split(";")[0].upper()] = val
    return out


def descargar() -> list[Concurso]:
    eventos = parse_ics(fetch_text(config.URL_CONTEST_ICS, max_age_h=24))
    if not eventos:
        raise FuenteNoDisponible("contestcalendar.com sin eventos")
    return eventos
