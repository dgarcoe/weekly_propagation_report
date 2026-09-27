"""CelesTrak: TLE de satélites de radioaficionado."""
from __future__ import annotations

import re

from .. import config
from ..http import FuenteNoDisponible, fetch_text


def parse_tle(text: str) -> list[tuple[str, str, str]]:
    """Lista de (nombre, línea 1, línea 2) de un fichero TLE de tres líneas."""
    lines = [l.rstrip() for l in text.splitlines() if l.strip()]
    out = []
    i = 0
    while i + 2 < len(lines):
        name, l1, l2 = lines[i], lines[i + 1], lines[i + 2]
        if l1.startswith("1 ") and l2.startswith("2 "):
            out.append((name.strip(), l1, l2))
            i += 3
        else:
            i += 1
    return out


def select(tles: list[tuple[str, str, str]], wanted=config.SATELITES):
    """Filtra por designación (p. ej. «SO-50» casa con «SAUDISAT 1C (SO-50)» pero no «SO-500»)."""
    out = []
    for w in wanted:
        rx = re.compile(r"(?<![\w-])" + re.escape(w.upper()) + r"(?![\w])")
        for tle in tles:
            if rx.search(tle[0].upper()):
                out.append((w, tle[1], tle[2]))
                break
    return out


def descargar() -> list[tuple[str, str, str]]:
    tles = parse_tle(fetch_text(config.URL_CELESTRAK_AMATEUR, max_age_h=24))
    if not tles:
        raise FuenteNoDisponible("CelesTrak sin TLE")
    return tles
