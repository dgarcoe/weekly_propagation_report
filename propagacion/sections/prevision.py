"""Sección 3 · Previsión para la semana siguiente.

- Fiabilidad VOACAP desde IN52PE hacia los destinos DX.
- NVIS/regional en 80 y 40 m a partir de foF2 de El Arenosillo.
- Línea gris: orto/ocaso en Vigo y en los destinos, ventanas comunes.
"""
from __future__ import annotations

import logging
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

from .. import charts, config, geo, solar, voacap
from ..http import FuenteNoDisponible
from ..periodo import Periodo, fecha_corta
from ..sources import giro, noaa

log = logging.getLogger(__name__)

FUENTES = {
    "voacap": "VOACAP (voacapl, port para Linux de J. Watson; https://github.com/jawatson/voacapl)",
    "giro": "GIRO / DIDBase, ionosonda de El Arenosillo EA036 (https://giro.uml.edu/)",
    "noaa_pred": "NOAA SWPC — predicción del ciclo solar",
}

FRANJAS = [(0, 4), (4, 8), (8, 12), (12, 16), (16, 20), (20, 24)]


# --- VOACAP -------------------------------------------------------------------------

def ssn_para_prevision(outlook_sfi: float | None, sfi_semana: float | None, p: Periodo
                       ) -> tuple[float, str]:
    """SSN para VOACAP: SSN efectivo del SFI previsto por NOAA para la semana;
    si falta, el de la semana pasada; y si no, el SSN suavizado previsto."""
    if outlook_sfi:
        return solar.ssn_from_sfi(outlook_sfi), f"SSN efectivo del SFI previsto ({outlook_sfi:.0f})"
    if sfi_semana:
        return solar.ssn_from_sfi(sfi_semana), f"SSN efectivo del SFI medio de la semana pasada ({sfi_semana:.0f})"
    try:
        pred = noaa.descargar_prediccion_ciclo()
        mid = p.sig_inicio + timedelta(days=3)
        if (mid.year, mid.month) in pred:
            return pred[(mid.year, mid.month)], "SSN suavizado previsto por NOAA"
    except FuenteNoDisponible as e:
        log.warning("NOAA predicción ciclo: %s", e)
    raise FuenteNoDisponible("sin SSN para VOACAP")


def resumen_franjas(rel: dict[int, list[float]], bandas: list[str], umbral: float = 0.5,
                    umbral_marginal: float = 0.2) -> list[str]:
    """Para cada franja de 4 h: bandas con fiabilidad media ≥ umbral (la mejor primero).

    Si ninguna llega, se indica la mejor banda en cursiva con su porcentaje cuando
    supera ``umbral_marginal`` (apertura posible pero poco fiable).
    """
    out = []
    for h0, h1 in FRANJAS:
        medias = [(statistics.fmean(rel[h][i] for h in range(h0, h1) if h in rel), b)
                  for i, b in enumerate(bandas)]
        medias.sort(reverse=True)
        buenas = [b for m, b in medias if m >= umbral]
        if buenas:
            out.append(", ".join(buenas[:3]))
        elif medias and medias[0][0] >= umbral_marginal:
            out.append(f"_{medias[0][1]} ({medias[0][0] * 100:.0f} %)_")
        else:
            out.append("—")
    return out


def construir_voacap(p: Periodo, outdir: Path, ssn: float, ssn_origen: str) -> dict:
    res: dict = {"ok": False}
    lat0, lon0 = geo.locator_to_latlon(config.STATION_LOCATOR)
    bandas = config.BANDAS_VOACAP
    freqs = [config.BANDAS[b][2] for b in bandas]
    mid = p.sig_inicio + timedelta(days=3)
    tablas: dict[str, np.ndarray] = {}
    filas = []
    for dst in config.DESTINOS:
        deck = voacap.build_deck((lat0, lon0, config.STATION_NAME.upper()),
                                 (dst.lat, dst.lon, dst.nombre), mid.year, mid.month, ssn, freqs)
        rel = voacap.run(deck, len(freqs))
        m = np.zeros((len(bandas), 24))
        for h, vals in rel.items():
            m[:, h] = vals
        tablas[dst.nombre] = m
        filas.append({
            "destino": dst.nombre,
            "distancia": round(geo.great_circle_km(lat0, lon0, dst.lat, dst.lon)),
            "rumbo": round(geo.bearing_deg(lat0, lon0, dst.lat, dst.lon)),
            "franjas": resumen_franjas(rel, bandas),
        })
    res.update(
        ok=True, ssn=ssn, ssn_origen=ssn_origen, filas=filas,
        franjas=[f"{a:02d}–{b:02d}" for a, b in FRANJAS],
        mes=mid.month,
        parametros=voacap.Parametros(),
        grafica=charts.voacap_multiples(
            tablas, bandas, outdir / "voacap_fiabilidad.png",
            "Fiabilidad prevista desde Vigo (VOACAP)",
            f"CW 100 W, dipolos λ/2 a λ/2 de altura, ruido residencial · SSN {ssn:.0f} · "
            f"mes {mid.month}/{mid.year}").name,
    )
    return res


# --- NVIS / foF2 ---------------------------------------------------------------------

DISTANCIAS_REGIONALES = [
    ("NVIS (Galicia, < 200 km)", 0),
    ("Vigo – Madrid (~460 km)", 460),
    ("Vigo – Barcelona (~900 km)", 900),
]


def perfil_horario(serie: list[tuple[datetime, float]]) -> dict[int, tuple[float, float, float]]:
    """{hora UTC: (p25, mediana, p75)} de foF2."""
    por_hora: dict[int, list[float]] = defaultdict(list)
    for t, f in serie:
        por_hora[t.hour].append(f)
    out = {}
    for h, vals in por_hora.items():
        q = np.percentile(vals, [25, 50, 75])
        out[h] = (float(q[0]), float(q[1]), float(q[2]))
    return out


def ventanas(horas_ok: list[int]) -> str:
    """[6,7,8,9,17,18] -> '06–10, 17–19 UTC'."""
    if not horas_ok:
        return "cerrada"
    horas = sorted(set(horas_ok))
    tramos = []
    ini = prev = horas[0]
    for h in horas[1:]:
        if h != prev + 1:
            tramos.append((ini, prev + 1))
            ini = h
        prev = h
    tramos.append((ini, prev + 1))
    # Unir el tramo que cruza medianoche
    if len(tramos) > 1 and tramos[0][0] == 0 and tramos[-1][1] == 24:
        tramos = [(tramos[-1][0], tramos[0][1])] + tramos[1:-1]
    if tramos == [(0, 24)]:
        return "todo el día"
    return ", ".join(f"{a:02d}–{b % 24:02d}" for a, b in tramos) + " UTC"


def construir_nvis(p: Periodo, outdir: Path) -> dict:
    serie = [(t, f) for t, f in giro.descargar_fof2(p.inicio, p.fin + timedelta(days=1))
             if p.inicio <= t.date() <= p.fin]
    if len(serie) < 24:
        raise FuenteNoDisponible(f"GIRO: solo {len(serie)} medidas de foF2 en la semana")
    perfil = perfil_horario(serie)
    horas = sorted(perfil)
    filas = []
    for nombre, dist in DISTANCIAS_REGIONALES:
        sec = solar.sec_incidence(dist)
        fila = {"trayecto": nombre, "factor": sec}
        for banda, f in (("80m", 3.6), ("40m", 7.1)):
            # Abierta si la MUF mediana supera la frecuencia con un 10 % de margen
            fila[banda] = ventanas([h for h in horas if perfil[h][1] * sec * 0.9 >= f])
        fila["muf_max"] = max(perfil[h][1] for h in horas) * sec
        fila["muf_min"] = min(perfil[h][1] for h in horas) * sec
        filas.append(fila)
    fof2_mediana = statistics.median(f for _, f in serie)
    return {
        "ok": True,
        "medidas": len(serie),
        "fof2_max": max(perfil[h][1] for h in horas),
        "fof2_min": min(perfil[h][1] for h in horas),
        "hora_max": max(horas, key=lambda h: perfil[h][1]),
        "fof2_mediana": fof2_mediana,
        "filas": filas,
        "grafica": charts.fof2_diario(
            horas, [perfil[h][1] for h in horas], [perfil[h][0] for h in horas],
            [perfil[h][2] for h in horas], outdir / "fof2_arenosillo.png",
            f"GIRO DIDBase · El Arenosillo (EA036) · {p.inicio:%d/%m}–{p.fin:%d/%m/%Y} · "
            f"{len(serie)} ionogramas").name,
    }


# --- Línea gris ------------------------------------------------------------------------

def ventanas_comunes(a: list[tuple[str, datetime]], b: list[tuple[str, datetime]],
                     margen_min: int = 45) -> list[dict]:
    """Solapes entre los terminadores de dos lugares (± ``margen_min`` en cada uno)."""
    out = []
    m = timedelta(minutes=margen_min)
    for ev_a, ta in a:
        for ev_b, tb in b:
            ini, fin = max(ta - m, tb - m), min(ta + m, tb + m)
            if fin - ini >= timedelta(minutes=10):
                out.append({"vigo": ev_a, "dx": ev_b, "inicio": ini, "fin": fin})
    return sorted(out, key=lambda w: w["inicio"])


def noches(lat: float, lon: float, dias: list[date]) -> list[tuple[datetime, datetime]]:
    """Intervalos ocaso → orto siguiente para los días dados."""
    out = []
    for d in dias:
        _, ocaso = solar.sun_events(lat, lon, d)
        orto_sig, _ = solar.sun_events(lat, lon, d + timedelta(days=1))
        if ocaso and orto_sig:
            if orto_sig < ocaso:          # en longitudes lejanas el orto «siguiente» cae el mismo día UTC
                orto_sig += timedelta(days=1)
            out.append((ocaso, orto_sig))
    return out


def noche_comun(a: list[tuple[datetime, datetime]], b: list[tuple[datetime, datetime]],
                minimo_min: int = 30) -> list[tuple[datetime, datetime]]:
    """Intersección de dos listas de intervalos (los dos extremos a oscuras)."""
    out = []
    for a0, a1 in a:
        for b0, b1 in b:
            ini, fin = max(a0, b0), min(a1, b1)
            if fin - ini >= timedelta(minutes=minimo_min):
                out.append((ini, fin))
    return sorted(out)


def _eventos(lat: float, lon: float, dias: list[date]) -> list[tuple[str, datetime]]:
    ev = []
    for d in dias:
        orto, ocaso = solar.sun_events(lat, lon, d)
        if orto:
            ev.append(("orto", orto))
        if ocaso:
            ev.append(("ocaso", ocaso))
    return ev


def construir_linea_gris(p: Periodo) -> dict:
    lat0, lon0 = geo.locator_to_latlon(config.STATION_LOCATOR)
    dia = p.sig_inicio + timedelta(days=3)              # jueves: día representativo
    orto, ocaso = solar.sun_events(lat0, lon0, dia)
    # Buscamos solapes en tres días seguidos para capturar los que cruzan medianoche UTC
    dias = [dia - timedelta(days=1), dia, dia + timedelta(days=1)]
    ev_vigo = _eventos(lat0, lon0, dias)
    noches_vigo = noches(lat0, lon0, dias)
    filas = []
    for dst in config.DESTINOS:
        o, c = solar.sun_events(dst.lat, dst.lon, dia)
        comunes = [w for w in ventanas_comunes(ev_vigo, _eventos(dst.lat, dst.lon, dias))
                   if w["inicio"].date() == dia or w["fin"].date() == dia]
        oscuro = [(i, f) for i, f in noche_comun(noches_vigo, noches(dst.lat, dst.lon, dias))
                  if i.date() <= dia <= f.date()]
        filas.append({
            "destino": dst.nombre,
            "noche": [f"{i:%H:%M}–{f:%H:%M}" for i, f in oscuro[:1]],
            "orto": f"{o:%H:%M}" if o else "—",
            "ocaso": f"{c:%H:%M}" if c else "—",
            "ventanas": [f"{w['inicio']:%H:%M}–{w['fin']:%H:%M} UTC "
                         f"({w['vigo']} Vigo / {w['dx']} DX)" for w in comunes],
        })
    return {"ok": True, "dia": fecha_corta(dia), "orto": f"{orto:%H:%M}", "ocaso": f"{ocaso:%H:%M}",
            "filas": filas}


def construir(p: Periodo, outdir: Path, sol: dict) -> dict:
    res: dict = {"fuentes": [], "avisos": []}
    outlook = (sol.get("outlook") or {}).get("sfi_medio")
    sfi_sem = (sol.get("sfi") or {}).get("media")
    try:
        ssn, origen = ssn_para_prevision(outlook, sfi_sem, p)
        res["voacap"] = construir_voacap(p, outdir, ssn, origen)
        res["fuentes"].append(FUENTES["voacap"])
    except (FuenteNoDisponible, voacap.VoacapNoDisponible) as e:
        log.warning("VOACAP: %s", e)
        res["voacap"] = {"ok": False, "motivo": str(e)}
    try:
        res["nvis"] = construir_nvis(p, outdir)
        res["fuentes"].append(FUENTES["giro"])
    except FuenteNoDisponible as e:
        log.warning("GIRO: %s", e)
        res["nvis"] = {"ok": False, "motivo": str(e)}
    res["linea_gris"] = construir_linea_gris(p)
    res["ok"] = True
    return res
