"""Reverse Beacon Network: archivos diarios de spots CW/RTTY.

Cada día hay un ZIP con un CSV:
``callsign,de_pfx,de_cont,freq,band,dx,dx_pfx,dx_cont,mode,db,date,speed,tx_mode``
donde ``callsign`` es el skimmer que escucha y ``dx`` la estación escuchada;
``freq`` va en kHz. El fichero no trae locators, así que filtramos por
indicativo (distrito EA1, que incluye Galicia) y agrupamos por continente.
"""
from __future__ import annotations

import csv
import io
import logging
import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .. import config, http
from ..http import FuenteNoDisponible

log = logging.getLogger(__name__)


@dataclass
class SpotRBN:
    time: datetime
    freq_mhz: float
    skimmer: str
    skimmer_cont: str
    dx: str
    dx_cont: str
    mode: str
    snr: int


def parse_csv(text: str, call_regex: str = config.RBN_CALL_REGEX) -> list[SpotRBN]:
    """Spots donde el skimmer o la estación escuchada casan con ``call_regex``."""
    rx = re.compile(call_regex, re.IGNORECASE)
    out = []
    reader = csv.DictReader(io.StringIO(text))
    for r in reader:
        try:
            skimmer = (r.get("callsign") or "").split("-")[0]
            dx = r.get("dx") or ""
            if not (rx.match(skimmer) or rx.match(dx)):
                continue
            out.append(SpotRBN(
                time=datetime.fromisoformat(r["date"]),
                freq_mhz=float(r["freq"]) / 1000.0,
                skimmer=skimmer, skimmer_cont=r.get("de_cont", ""),
                dx=dx, dx_cont=r.get("dx_cont", ""),
                mode=r.get("tx_mode") or r.get("mode", ""),
                snr=int(float(r.get("db") or 0)),
            ))
        except (KeyError, ValueError, TypeError):
            continue
    return out


def parse_zip(data: bytes, call_regex: str = config.RBN_CALL_REGEX) -> list[SpotRBN]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        spots = []
        for name in zf.namelist():
            if name.lower().endswith(".csv"):
                spots += parse_csv(zf.read(name).decode("utf-8", errors="replace"), call_regex)
        return spots


def descargar(inicio: date, dias: int = 7) -> list[SpotRBN]:
    spots: list[SpotRBN] = []
    fallos = 0
    for i in range(dias):
        d = inicio + timedelta(days=i)
        try:
            data = http.fetch_bytes(config.URL_RBN_DAY.format(fecha=d), max_age_h=24 * 30, timeout=300)
            spots += parse_zip(data)
        except (FuenteNoDisponible, zipfile.BadZipFile) as e:
            log.warning("RBN %s no disponible: %s", d, e)
            fallos += 1
    if fallos == dias:
        raise FuenteNoDisponible("RBN: ningún día disponible")
    return spots
