"""Fixtures: una «internet falsa» con datos sintéticos en el formato real de cada fuente.

Así el informe completo se puede generar en CI sin red y sin depender de que
las fuentes respondan.
"""
from __future__ import annotations

import io
import math
import random
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from propagacion import config, http

FIX = Path(__file__).parent / "fixtures"
FECHA_INFORME = date(2026, 9, 28)          # lunes → semana analizada 21-27/9/2026


def tle_checksum(line: str) -> str:
    s = sum(int(c) if c.isdigit() else (1 if c == "-" else 0) for c in line[:68])
    return line[:68] + str(s % 10)


def fake_tle() -> str:
    # ISS con época 27/9/2026 (elementos orbitales plausibles).
    l1 = tle_checksum("1 25544U 98067A   26270.50000000  .00016717  00000-0  30375-3 0  9990")
    l2 = tle_checksum("2 25544  51.6400 208.9163 0006317  69.9862  25.2906 15.49560000 12340")
    l1b = tle_checksum("1 27607U 02058C   26270.25000000  .00000400  00000-0  60000-4 0  9990")
    l2b = tle_checksum("2 27607  64.5500 150.0000 0080000 250.0000 110.0000 14.80000000 12340")
    return f"ISS (ZARYA)\n{l1}\n{l2}\nSAUDISAT 1C (SO-50)\n{l1b}\n{l2b}\n"


def fake_fluxtable() -> str:
    lines = ["fluxdate    fluxtime    fluxjulian    fluxcarrington  fluxobsflux  fluxadjflux  fluxursi",
             "----------  ----------  ------------  --------------  -----------  -----------  ---------"]
    d = date(2025, 9, 1)
    i = 0
    while d <= date(2026, 9, 27):
        v = 170 - i * 0.1 + 20 * math.sin(2 * math.pi * i / 27)
        for hh in ("170000", "200000", "230000"):
            lines.append(f"{d:%Y%m%d}    {hh}      02460000.000  002300.000      {v:08.1f}     "
                         f"{v:08.1f}     {v * 0.9:08.1f}")
        d += timedelta(days=1)
        i += 1
    return "\n".join(lines) + "\n"


def fake_xrays() -> str:
    """GOES 1 min, dos canales; fondo clase B con la M1.4 del 22/9 y la X1.1 del 23/9."""
    import json

    filas = []
    t = datetime(2026, 9, 21, 8)
    while t < datetime(2026, 9, 28, 8):
        flux = 3e-7 * (1 + 0.3 * math.sin(t.hour / 3))
        for pico, clase in ((datetime(2026, 9, 22, 10, 58), 1.4e-5), (datetime(2026, 9, 23, 13, 52), 1.1e-4)):
            flux += clase * math.exp(-abs((t - pico).total_seconds()) / 900)
        for energia, f in (("0.05-0.4nm", flux / 10), ("0.1-0.8nm", flux)):
            filas.append({"time_tag": f"{t:%Y-%m-%dT%H:%M:%S}Z", "satellite": 18, "flux": f,
                          "energy": energia})
        t += timedelta(minutes=5)
    filas.append({"time_tag": "2026-09-24T00:00:00Z", "flux": 0.0, "energy": "0.1-0.8nm"})
    return json.dumps(filas)


def fake_wspr_tsv() -> str:
    rnd = random.Random(40)
    remotos = [("W1AW", "FN31pr"), ("K3LR", "EN91"), ("PY2ZX", "GG66"), ("VK2XX", "QF56"),
               ("JA1ABC", "PM95"), ("ZS6AA", "KG33"), ("G4ABC", "IO91"), ("DL1XX", "JO62"),
               ("EA4ZZ", "IN80"), ("EA1ABC", "IN73"), ("SM5XX", "JO89")]
    locales = [("EA1RKV", "IN52pe"), ("EA1XYZ", "IN53ud")]
    freqs = {"40m": 7040100, "30m": 10140200, "20m": 14097100, "15m": 21096100, "10m": 28126100}
    rows = ["time\tfrequency\ttx_sign\ttx_loc\trx_sign\trx_loc\tsnr\tpower"]
    t0 = datetime(2026, 9, 21)
    for _ in range(600):
        t = t0 + timedelta(minutes=2 * rnd.randrange(7 * 720))
        banda = rnd.choice(list(freqs))
        r = rnd.choice(remotos)
        l = rnd.choice(locales)
        tx, rx = (l, r) if rnd.random() < 0.5 else (r, l)
        rows.append(f"{t:%Y-%m-%d %H:%M:%S}\t{freqs[banda]}\t{tx[0]}\t{tx[1]}\t{rx[0]}\t{rx[1]}"
                    f"\t{rnd.randint(-28, 5)}\t{rnd.choice([23, 30, 37])}")
    return "\n".join(rows) + "\n"


def fake_rbn_zip(d: date) -> bytes:
    rows = ["callsign,de_pfx,de_cont,freq,band,dx,dx_pfx,dx_cont,mode,db,date,speed,tx_mode",
            f"W3LPL-#,K,NA,14025.1,20m,EA1RKV,EA,EU,CW,18,{d} 18:01:00,25,CQ",
            f"EA1RKV-#,EA,EU,7010.0,40m,JA1ZZZ,JA,AS,CW,7,{d} 21:10:00,28,CQ",
            f"DK9IP-#,DL,EU,14030.0,20m,F5XX,F,EU,CW,20,{d} 12:00:00,22,CQ"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{d:%Y%m%d}.csv", "\n".join(rows) + "\n")
    return buf.getvalue()


LAT_IONOSONDA = {"EA036": 37.1, "EB040": 40.8, "DB049": 50.1}


def valor_giro(ursi: str, car: str, t: datetime) -> float | None:
    """Ionosfera sintética: más foF2 cuanto más al sur, tormenta negativa el 25/9,
    Es fuerte en Roquetes el 23/9, spread-F de madrugada el 22 y el 26."""
    h = t.hour + t.minute / 60
    dia = 6 <= h <= 19
    lat = LAT_IONOSONDA[ursi]
    fof2 = (4.0 + 5.0 * max(0.0, math.sin(math.pi * (h - 6) / 13)) if dia else 4.0) * (1 + (42 - lat) * 0.01)
    if t.date() == date(2026, 9, 25):
        fof2 *= 0.65                                  # −35 %: tormenta ionosférica negativa
    if car == "foF2":
        return round(fof2, 3)
    if car == "MUF(D)":
        return round(fof2 * 3.2, 3)
    if car == "M(D)":
        return 3.2
    if car == "hmF2":
        return 250.0 if dia else 300.0
    if car == "foF1":
        return 5.0 if 9 <= h <= 15 else None
    if car == "fmin":
        return round(1.5 + 2.5 * max(0.0, math.sin(math.pi * (h - 8) / 8)), 2) if 8 <= h <= 16 else 1.5
    if car == "foEs":
        if ursi == "EB040" and t.date() == date(2026, 9, 23) and 14 <= h < 16:
            return 12.0
        return 3.0 if dia else None
    if car == "FF":
        return 0.9 if t.date() in (date(2026, 9, 22), date(2026, 9, 26)) and 1 <= h < 4 else 0.1
    return None


def fake_giro(params: dict) -> str:
    ursi = params["ursiCode"]
    cars = params["charName"].split(",")
    t = datetime.strptime(params["fromDate"], "%Y/%m/%d %H:%M:%S")
    fin = datetime.strptime(params["toDate"], "%Y/%m/%d %H:%M:%S")
    lines = ["# Global Ionospheric Radio Observatory (GIRO)", f"# URSI-Code {ursi}"]
    while t < fin:
        cols = []
        for c in cars:
            v = valor_giro(ursi, c, t)
            cols.append("  --- __" if v is None else f"{v:7.3f} //")
        lines.append(f"{t:%Y-%m-%dT%H:%M:%S}.000Z  90 " + " ".join(cols))
        t += timedelta(minutes=15)
    # Errores típicos del autoescalado: uno con CS baja y un pico con CS alta
    lines.append("2026-09-22T12:07:00.000Z  45  15.000 //" + "  --- __" * (len(cars) - 1))
    lines.append("2026-09-23T12:07:00.000Z  95  16.000 //" + "  --- __" * (len(cars) - 1))
    return "\n".join(lines) + "\n"


@pytest.fixture
def internet_falsa(monkeypatch, tmp_path):
    """Sustituye ``http.fetch_bytes`` por respuestas locales según la URL."""
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")

    def fake(url: str, params=None, **kw) -> bytes:
        rutas = {
            config.URL_NOAA_DSD: (FIX / "daily-solar-indices.txt").read_bytes,
            config.URL_NOAA_DGD: (FIX / "daily-geomagnetic-indices.txt").read_bytes,
            config.URL_NOAA_KP: (FIX / "noaa-planetary-k-index.json").read_bytes,
            config.URL_NOAA_FLARES: (FIX / "xray-flares-7-day.json").read_bytes,
            config.URL_NOAA_27DO: (FIX / "27-day-outlook.txt").read_bytes,
            config.URL_NOAA_3DAY: (FIX / "3-day-forecast.txt").read_bytes,
            config.URL_NOAA_CYCLE_PRED: (FIX / "predicted-solar-cycle.json").read_bytes,
            config.URL_NOAA_XRAYS: lambda: fake_xrays().encode(),
            config.URL_DRAO_FLUX: lambda: fake_fluxtable().encode(),
            config.URL_WSPR_LIVE: lambda: fake_wspr_tsv().encode(),
            config.URL_CELESTRAK_AMATEUR: lambda: fake_tle().encode(),
            config.URL_CONTEST_RSS: (FIX / "calendar.rss").read_bytes,
        }
        if url in rutas:
            return rutas[url]()
        if url == config.URL_GIRO:
            return fake_giro(params).encode()
        if "reversebeacon" in url:
            d = datetime.strptime(url.rsplit("/", 1)[1][:8], "%Y%m%d").date()
            return fake_rbn_zip(d)
        raise http.FuenteNoDisponible(f"sin red en tests: {url}")

    monkeypatch.setattr(http, "fetch_bytes", fake)
    return fake
