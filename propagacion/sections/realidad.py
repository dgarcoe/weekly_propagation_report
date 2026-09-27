"""Sección 2 · Lo que pasó de verdad desde Galicia (WSPR + RBN)."""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

from .. import charts, config, geo
from ..http import FuenteNoDisponible
from ..periodo import Periodo, fecha_corta
from ..sources import rbn, wspr

log = logging.getLogger(__name__)

FUENTES = {
    "wspr": "WSPRnet vía wspr.live (https://wspr.live/)",
    "rbn": "Reverse Beacon Network (https://www.reversebeacon.net/)",
}
# Bandas que mostramos en el mapa de calor (de arriba abajo: más alta primero).
BANDAS_HEATMAP = ["2m", "6m", "10m", "12m", "15m", "17m", "20m", "30m", "40m", "60m", "80m", "160m"]


def banda_de(freq_mhz: float) -> str | None:
    for nombre, (lo, hi, _) in config.BANDAS.items():
        # Margen de 5 kHz para spots en el borde de banda.
        if lo - 0.005 <= freq_mhz <= hi + 0.005:
            return nombre
    return None


def es_galicia(loc: str) -> bool:
    return loc[:4].upper() in config.GALICIA_SQUARES


@dataclass
class Contacto:
    """Un spot normalizado: una estación de Galicia y un corresponsal remoto."""
    time: datetime
    banda: str
    fuente: str                 # "WSPR" | "RBN"
    sentido: str                # "tx" = Galicia fue oída; "rx" = Galicia oyó
    local: str
    remoto: str
    remoto_loc: str | None
    continente: str | None
    distancia_km: float | None
    azimut: float | None
    snr: int


def normalizar_wspr(spots: list[wspr.SpotWSPR]) -> list[Contacto]:
    lat0, lon0 = geo.locator_to_latlon(config.STATION_LOCATOR)
    out = []
    for s in spots:
        banda = banda_de(s.freq_mhz)
        if banda is None:
            continue
        if es_galicia(s.tx_loc):
            sentido, local, remoto, rloc = "tx", s.tx_sign, s.rx_sign, s.rx_loc
        elif es_galicia(s.rx_loc):
            sentido, local, remoto, rloc = "rx", s.rx_sign, s.tx_sign, s.tx_loc
        else:
            continue
        try:
            lat, lon = geo.locator_to_latlon(rloc)
        except ValueError:
            continue
        out.append(Contacto(
            time=s.time, banda=banda, fuente="WSPR", sentido=sentido, local=local,
            remoto=remoto, remoto_loc=rloc[:6], continente=geo.continent(lat, lon),
            distancia_km=geo.great_circle_km(lat0, lon0, lat, lon),
            azimut=geo.bearing_deg(lat0, lon0, lat, lon), snr=s.snr,
        ))
    return out


def normalizar_rbn(spots: list[rbn.SpotRBN]) -> list[Contacto]:
    import re

    rx = re.compile(config.RBN_CALL_REGEX, re.IGNORECASE)
    out = []
    for s in spots:
        banda = banda_de(s.freq_mhz)
        if banda is None:
            continue
        if rx.match(s.dx):
            sentido, local, remoto, cont = "tx", s.dx, s.skimmer, s.skimmer_cont
        else:
            sentido, local, remoto, cont = "rx", s.skimmer, s.dx, s.dx_cont
        out.append(Contacto(s.time, banda, "RBN", sentido, local, remoto, None,
                            cont or None, None, None, s.snr))
    return out


def matriz_hora_banda(contactos: list[Contacto], bandas: list[str]) -> np.ndarray:
    m = np.zeros((len(bandas), 24), dtype=int)
    idx = {b: i for i, b in enumerate(bandas)}
    for c in contactos:
        if c.banda in idx:
            m[idx[c.banda], c.time.hour] += 1
    return m


def dx_por_banda(contactos: list[Contacto]) -> list[dict]:
    mejor: dict[str, Contacto] = {}
    for c in contactos:
        if c.distancia_km is None:
            continue
        if c.banda not in mejor or c.distancia_km > mejor[c.banda].distancia_km:
            mejor[c.banda] = c
    orden = list(config.BANDAS)
    out = []
    for banda in sorted(mejor, key=orden.index):
        c = mejor[banda]
        out.append({
            "banda": banda,
            "distancia": round(c.distancia_km),
            "local": c.local,
            "remoto": c.remoto,
            "remoto_loc": c.remoto_loc,
            "continente": geo.CONTINENTES.get(c.continente or "", "?"),
            "sentido": "oído desde Galicia" if c.sentido == "rx" else "oyó a Galicia",
            "cuando": f"{fecha_corta(c.time.date())} {c.time:%H:%M} UTC",
            "snr": c.snr,
        })
    return out


def tabla_continentes(contactos: list[Contacto], bandas: list[str]) -> list[dict]:
    por: dict[str, Counter] = defaultdict(Counter)
    for c in contactos:
        if c.continente and c.continente in geo.CONTINENTES:
            por[c.continente][c.banda] += 1
    filas = []
    for cont, cnt in sorted(por.items(), key=lambda kv: -sum(kv[1].values())):
        filas.append({"continente": geo.CONTINENTES[cont], "total": sum(cnt.values()),
                      "bandas": [cnt.get(b, 0) for b in bandas],
                      "mejor_banda": cnt.most_common(1)[0][0]})
    return filas


def construir(p: Periodo, outdir: Path, usar_rbn: bool = True) -> dict:
    res: dict = {"ok": False, "fuentes": [], "avisos": []}
    contactos: list[Contacto] = []
    try:
        spots = wspr.descargar(p.inicio_dt.replace(tzinfo=None), p.fin_dt.replace(tzinfo=None))
        cw = normalizar_wspr(spots)
        contactos += cw
        res["wspr_spots"] = len(cw)
        res["wspr_estaciones"] = len({c.local for c in cw})
        res["fuentes"].append(FUENTES["wspr"])
    except FuenteNoDisponible as e:
        log.warning("WSPR: %s", e)
        res["avisos"].append("WSPR (wspr.live) no disponible.")
    if usar_rbn:
        try:
            cr = normalizar_rbn(rbn.descargar(p.inicio))
            contactos += cr
            res["rbn_spots"] = len(cr)
            res["fuentes"].append(FUENTES["rbn"])
        except FuenteNoDisponible as e:
            log.warning("RBN: %s", e)
            res["avisos"].append("RBN no disponible.")
    if not contactos:
        return res

    res["ok"] = True
    res["total"] = len(contactos)
    bandas_con_datos = [b for b in BANDAS_HEATMAP if any(c.banda == b for c in contactos)]
    # Siempre mostramos las bandas HF principales aunque estén vacías (un hueco también informa).
    bandas = [b for b in BANDAS_HEATMAP if b in bandas_con_datos or b in
              ("10m", "12m", "15m", "17m", "20m", "30m", "40m", "80m")]
    m = matriz_hora_banda(contactos, bandas)
    res["heatmap"] = charts.heatmap_hora_banda(
        m, bandas, outdir / "heatmap_hora_banda.png",
        "Spots desde/hacia Galicia por hora y banda",
        f"WSPR + RBN · {p.inicio:%d/%m}–{p.fin:%d/%m/%Y} · cuadrículas "
        f"{', '.join(config.GALICIA_SQUARES)} (WSPR) y distrito EA1 (RBN)").name
    # Bandas y horas más activas (texto automático)
    por_banda = Counter(c.banda for c in contactos)
    res["bandas_top"] = [{"banda": b, "spots": n} for b, n in por_banda.most_common(4)]
    col = m.sum(axis=0)
    res["hora_pico"] = int(col.argmax())

    res["dx"] = dx_por_banda(contactos)
    bandas_cont = [b for b in bandas[::-1] if por_banda.get(b)]
    res["continentes_bandas"] = bandas_cont
    res["continentes"] = tabla_continentes(contactos, bandas_cont)

    # Rosa de rutas: un punto por locator remoto único (WSPR).
    vistos: dict[str, tuple[float, float]] = {}
    for c in contactos:
        if c.remoto_loc and c.distancia_km is not None and c.distancia_km > 50:
            vistos.setdefault(c.remoto_loc, (c.azimut, c.distancia_km))
    if vistos:
        etiquetas = []
        por_cont: dict[str, list[tuple[float, float]]] = defaultdict(list)
        for c in contactos:
            if c.remoto_loc in vistos and c.continente:
                por_cont[c.continente].append((c.azimut, c.distancia_km))
        for cont, pts in por_cont.items():
            if cont == "EU":
                continue           # Europa queda en el centro; etiquetarla tapa los puntos
            # Etiqueta en el azimut/distancia medianos del continente.
            az = float(np.median([a for a, _ in pts]))
            d = float(np.median([d for _, d in pts]))
            etiquetas.append((az, min(d * 1.12, 19000), f"{cont} ({len(pts)})"))
        res["rosa"] = charts.rosa_rutas(
            list(vistos.values()), etiquetas, outdir / "rutas_continentes.png",
            "¿Hacia dónde hubo propagación?",
            f"Cada punto es un locator remoto (WSPR) · centro: {config.STATION_LOCATOR} · "
            "proyección azimutal equidistante").name
        res["locators_unicos"] = len(vistos)
    return res
