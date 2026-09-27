"""TLE de satélites de radioaficionado: CelesTrak y, como respaldo, AMSAT."""
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


def select(tles: list[tuple[str, str, str]], wanted: dict[str, tuple[str, ...]] = config.SATELITES):
    """Filtra por designación (p. ej. «SO-50» casa con «SAUDISAT 1C (SO-50)» pero no «SO-500»).

    ``wanted``: nombre mostrado -> alias posibles, probados en orden.
    """
    out = []
    for nombre, alias in wanted.items():
        encontrado = None
        for a in alias:
            rx = re.compile(r"(?<![\w-])" + re.escape(a.upper()) + r"(?![\w])")
            encontrado = next((t for t in tles if rx.search(t[0].upper())), None)
            if encontrado:
                break
        if encontrado:
            out.append((nombre, encontrado[1], encontrado[2]))
    return out


def descargar() -> tuple[list[tuple[str, str, str]], str]:
    """(TLE, fuente usada). CelesTrak a veces no responde desde los runners de GitHub."""
    errores = []
    for url, fuente in ((config.URL_CELESTRAK_AMATEUR, "celestrak"), (config.URL_AMSAT_TLE, "amsat")):
        try:
            tles = parse_tle(fetch_text(url, max_age_h=24))
        except FuenteNoDisponible as e:
            errores.append(str(e))
            continue
        if tles:
            return tles, fuente
        errores.append(f"{url}: sin TLE")
    raise FuenteNoDisponible("; ".join(errores))
