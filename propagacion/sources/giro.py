"""GIRO / DIDBase (lgdc.uml.edu): foF2 de la ionosonda de El Arenosillo (EA036).

El servicio ``DIDBGetValues`` devuelve texto plano: cabeceras con ``#`` y
filas ``<ISO-8601> <confianza> <foF2> <QD>``; los valores ausentes llegan
como ``---``.
"""
from __future__ import annotations

from datetime import date, datetime

from .. import config
from ..http import FuenteNoDisponible, fetch_text


def parse_didb(text: str) -> list[tuple[datetime, float]]:
    out = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        toks = line.split()
        if len(toks) < 3:
            continue
        try:
            t = datetime.fromisoformat(toks[0].replace("Z", "").split(".")[0])
            fof2 = float(toks[2])
        except ValueError:
            continue
        if 0.5 < fof2 < 30:
            out.append((t, fof2))
    return out


def descargar_fof2(inicio: date, fin: date, ursi: str = config.GIRO_URSI_ARENOSILLO
                   ) -> list[tuple[datetime, float]]:
    params = {
        "ursiCode": ursi,
        "charName": "foF2",
        "DMUF": "3000",
        "fromDate": f"{inicio:%Y.%m.%d}",
        "toDate": f"{fin:%Y.%m.%d}",
    }
    serie = parse_didb(fetch_text(config.URL_GIRO, params=params, max_age_h=12, timeout=120))
    if not serie:
        raise FuenteNoDisponible(f"GIRO {ursi}: sin medidas de foF2")
    return serie
