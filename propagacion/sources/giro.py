"""GIRO / DIDBase (lgdc.uml.edu): magnitudes escaladas de las digisondas.

El servicio ``fastchar/getbest`` devuelve texto plano: cabeceras con ``#`` y una
fila por ionograma::

    2026-09-20T10:00:01.000Z  95  7.175 //  5.75 // 22.473 // ...
    <instante ISO>           <CS> <valor> <QD> <valor> <QD> ...

con un par (valor, calificador) por cada magnitud pedida, en el mismo orden que
``charName``; los valores ausentes llegan como ``---``. CS es la confianza del
autoescalado ARTIST (0-100; 999 = escalado manual). Fechas de la consulta en
formato ``AAAA/MM/DD hh:mm:ss``.
"""
from __future__ import annotations

from datetime import date, datetime

from .. import config
from ..http import FuenteNoDisponible, fetch_text
from ..ionosfera import Medida

# foF2/foF1/foEs: frecuencias críticas; MUF(D)/M(D): MUF(3000)F2 y factor M(3000)F2;
# hmF2: altura real del pico F2; fmin: frecuencia mínima (absorción);
# FF/QF: dispersión en frecuencia y en altura (spread-F).
CARACTERISTICAS = ("foF2", "foF1", "foEs", "MUF(D)", "M(D)", "hmF2", "fmin", "FF", "QF")


def parse_getbest(text: str, caracteristicas: tuple[str, ...] = ("foF2",)) -> list[Medida]:
    out = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        toks = line.split()
        if len(toks) < 2 + 2 * len(caracteristicas) - 1:
            continue
        try:
            t = datetime.fromisoformat(toks[0].replace("Z", "").split(".")[0])
            cs = int(toks[1])
        except ValueError:
            continue
        valores: dict[str, float | None] = {}
        for i, car in enumerate(caracteristicas):
            tok = toks[2 + 2 * i] if 2 + 2 * i < len(toks) else "---"
            try:
                valores[car] = float(tok)
            except ValueError:
                valores[car] = None
        out.append(Medida(t, cs, valores))
    return out


def parse_didb(text: str) -> list[tuple[datetime, float]]:
    """Solo foF2, sin filtrar: [(t, foF2)] (compatibilidad y pruebas rápidas)."""
    return [(m.time, v) for m in parse_getbest(text, ("foF2",))
            if (v := m.get("foF2")) is not None and 0.5 < v < 30]


def descargar(ursi: str, inicio: date, fin: date,
              caracteristicas: tuple[str, ...] = CARACTERISTICAS) -> list[Medida]:
    """Medidas de ``ursi`` entre ``inicio`` y ``fin`` (fechas a las 00 UTC)."""
    params = {
        "ursiCode": ursi,
        "charName": ",".join(caracteristicas),
        "DMUF": "3000",
        "fromDate": f"{inicio:%Y/%m/%d} 00:00:00",
        "toDate": f"{fin:%Y/%m/%d} 00:00:00",
    }
    text = fetch_text(config.URL_GIRO, params=params, max_age_h=12, timeout=180)
    medidas = parse_getbest(text, caracteristicas)
    if not medidas:
        raise FuenteNoDisponible(f"GIRO {ursi}: sin medidas ({text[-120:].strip()})")
    return medidas


def descargar_fof2(inicio: date, fin: date, ursi: str = config.GIRO_URSI_ARENOSILLO
                   ) -> list[tuple[datetime, float]]:
    return [(m.time, v) for m in descargar(ursi, inicio, fin, ("foF2",))
            if (v := m.get("foF2")) is not None]
