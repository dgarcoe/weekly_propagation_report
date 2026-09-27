"""WSPR vía wspr.live (ClickHouse por HTTP, sin API key).

Tabla ``wspr.rx``: time, band, rx_sign, rx_loc, tx_sign, tx_loc, distance,
frequency (Hz), power (dBm), snr… La columna ``band`` es un entero con los MHz
aproximados (7 = 40 m, 14 = 20 m…); para no depender de esa codificación
derivamos la banda de ``frequency``.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime

from .. import config
from ..http import FuenteNoDisponible, fetch_text

COLUMNAS = ("time", "frequency", "tx_sign", "tx_loc", "rx_sign", "rx_loc", "snr", "power")
LIMITE_FILAS = 300_000


@dataclass
class SpotWSPR:
    time: datetime
    freq_mhz: float
    tx_sign: str
    tx_loc: str
    rx_sign: str
    rx_loc: str
    snr: int
    power_dbm: int


def build_query(inicio: datetime, fin: datetime, cuadriculas=config.GALICIA_SQUARES) -> str:
    sq = ",".join(f"'{s.upper()}'" for s in cuadriculas)
    return (
        f"SELECT {', '.join(COLUMNAS)} FROM wspr.rx "
        f"WHERE time >= '{inicio:%Y-%m-%d %H:%M:%S}' AND time < '{fin:%Y-%m-%d %H:%M:%S}' "
        f"AND (upper(substring(tx_loc, 1, 4)) IN ({sq}) OR upper(substring(rx_loc, 1, 4)) IN ({sq})) "
        f"LIMIT {LIMITE_FILAS} FORMAT TabSeparatedWithNames"
    )


def parse_tsv(text: str) -> list[SpotWSPR]:
    reader = csv.DictReader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
    out = []
    for r in reader:
        try:
            out.append(SpotWSPR(
                time=datetime.fromisoformat(r["time"]),
                freq_mhz=int(r["frequency"]) / 1e6,
                tx_sign=r["tx_sign"], tx_loc=r["tx_loc"],
                rx_sign=r["rx_sign"], rx_loc=r["rx_loc"],
                snr=int(r["snr"]), power_dbm=int(r["power"]),
            ))
        except (KeyError, ValueError, TypeError):
            continue
    return out


def descargar(inicio: datetime, fin: datetime) -> list[SpotWSPR]:
    text = fetch_text(config.URL_WSPR_LIVE, params={"query": build_query(inicio, fin)},
                      max_age_h=12, timeout=180)
    if text.lstrip().startswith(("Code:", "<")):
        raise FuenteNoDisponible(f"wspr.live devolvió un error: {text[:200]}")
    return parse_tsv(text)
