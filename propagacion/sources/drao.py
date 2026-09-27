"""DRAO Penticton (origen del índice F10.7): histórico diario de flujo.

Lo usamos para la gráfica de SFI de los últimos meses, porque los productos
de NOAA solo cubren 30 días (diario) o son mensuales.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from .. import config
from ..http import FuenteNoDisponible, fetch_text


def parse_fluxtable(text: str) -> list[tuple[date, float]]:
    """Columnas: fluxdate fluxtime fluxjulian fluxcarrington fluxobsflux fluxadjflux fluxursi.

    Hay tres medidas diarias (17, 20 y 23 UT). Nos quedamos con la de 20 UT
    (la «oficial») y, si falta, con la media de las disponibles. Se usa el
    flujo observado, que es el que publica NOAA como SFI.
    """
    por_dia: dict[date, dict[str, float]] = defaultdict(dict)
    for line in text.splitlines():
        toks = line.split()
        if len(toks) < 6 or not toks[0].isdigit() or len(toks[0]) != 8:
            continue
        try:
            d = date(int(toks[0][:4]), int(toks[0][4:6]), int(toks[0][6:8]))
            flux = float(toks[4])
        except ValueError:
            continue
        if flux <= 0 or flux > 1000:      # valores de relleno o ráfagas
            continue
        por_dia[d][toks[1][:2]] = flux
    out = []
    for d in sorted(por_dia):
        medidas = por_dia[d]
        out.append((d, medidas.get("20", sum(medidas.values()) / len(medidas))))
    return out


def descargar_historico() -> list[tuple[date, float]]:
    serie = parse_fluxtable(fetch_text(config.URL_DRAO_FLUX, max_age_h=24))
    if not serie:
        raise FuenteNoDisponible("DRAO fluxtable sin filas")
    return serie
