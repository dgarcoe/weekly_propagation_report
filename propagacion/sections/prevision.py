"""Sección 3 · Previsión para la semana siguiente.

- Fiabilidad VOACAP desde IN52PE hacia los destinos DX.
- NVIS/regional en 80 y 40 m a partir de foF2 de El Arenosillo.
- Línea gris: orto/ocaso en Vigo y en los destinos, ventanas comunes.
"""
from __future__ import annotations

import logging
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

from .. import charts, config, geo, ionosfera as io, solar, voacap
from ..http import FuenteNoDisponible
from ..periodo import Periodo, fecha_corta
from ..sources import noaa

log = logging.getLogger(__name__)

FUENTES = {
    "voacap": "VOACAP (voacapl, port para Linux de J. Watson; https://github.com/jawatson/voacapl)",
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


MODO_GRAFICA = "FT8"


def construir_voacap(p: Periodo, outdir: Path, ssn: float, ssn_origen: str) -> dict:
    res: dict = {"ok": False}
    lat0, lon0 = geo.locator_to_latlon(config.STATION_LOCATOR)
    bandas = config.BANDAS_VOACAP
    freqs = [config.BANDAS[b][2] for b in bandas]
    mid = p.sig_inicio + timedelta(days=3)
    tablas: dict[str, np.ndarray] = {}
    filas: dict[str, list[dict]] = {modo: [] for modo in voacap.MODOS}
    for modo, snr in voacap.MODOS.items():
        params = voacap.Parametros(snr_requerida=snr)
        for dst in config.DESTINOS:
            deck = voacap.build_deck((lat0, lon0, config.STATION_NAME.upper()),
                                     (dst.lat, dst.lon, dst.nombre), mid.year, mid.month, ssn, freqs,
                                     params)
            rel = voacap.run(deck, len(freqs))
            if modo == MODO_GRAFICA:
                m = np.zeros((len(bandas), 24))
                for h, vals in rel.items():
                    m[:, h] = vals
                tablas[dst.nombre] = m
            filas[modo].append({
                "destino": dst.nombre,
                "distancia": round(geo.great_circle_km(lat0, lon0, dst.lat, dst.lon)),
                "rumbo": round(geo.bearing_deg(lat0, lon0, dst.lat, dst.lon)),
                "franjas": resumen_franjas(rel, bandas),
            })
    res.update(
        ok=True, ssn=ssn, ssn_origen=ssn_origen, filas=filas[MODO_GRAFICA], filas_cw=filas["CW"],
        franjas=[f"{a:02d}–{b:02d}" for a, b in FRANJAS],
        mes=mid.month,
        parametros=voacap.Parametros(),
        grafica=charts.voacap_multiples(
            tablas, bandas, outdir / "voacap_fiabilidad.png",
            f"Fiabilidad prevista desde Vigo en {MODO_GRAFICA} (VOACAP)",
            f"{MODO_GRAFICA} 100 W, dipolos λ/2 a λ/2 de altura, ángulo mínimo 3°, ruido residencial · "
            f"SSN {ssn:.0f} · mes {mid.month}/{mid.year}").name,
    )
    return res


# --- NVIS / foF2 ---------------------------------------------------------------------

DISTANCIAS_REGIONALES = [
    ("NVIS (Galicia, < 200 km)", 0),
    ("Vigo – Madrid (~460 km)", 460),
    ("Vigo – Barcelona (~900 km)", 900),
]


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


BANDAS_3000 = ("20m", "17m", "15m", "12m", "10m")
ALTURA_POR_DEFECTO_KM = 300.0


def estado_regional(fof2: dict[int, float], hmf2: dict[int, float], fmin: dict[int, float],
                    dist: float, f: float) -> tuple[list[int], list[int]]:
    """(horas abiertas, horas en que la MUF llega pero la absorción cierra la banda).

    MUF = foF2 · sec φ con la hmF2 medida de cada hora (300 km si falta);
    LUF ≈ fmin · √sec φ_D (absorción en la capa D).
    """
    abiertas, absorcion = [], []
    for h in sorted(fof2):
        muf = fof2[h] * solar.sec_incidence(dist, hmf2.get(h, ALTURA_POR_DEFECTO_KM))
        luf = io.luf_absorcion(fmin[h], dist) if h in fmin else None
        estado = io.estado_banda(f, muf, luf)
        if estado == "abierta":
            abiertas.append(h)
        elif estado == "absorcion":
            absorcion.append(h)
    return abiertas, absorcion


def construir_nvis(p: Periodo, outdir: Path, iono: dict) -> dict:
    if not iono.get("ok"):
        raise FuenteNoDisponible("sin datos de ionosondas")
    vigo = iono["vigo"]
    fof2, hmf2, fmin, mufd = vigo["foF2"], vigo["hmF2"], vigo["fmin"], vigo["MUF(D)"]
    if len(fof2) < 12:
        raise FuenteNoDisponible(f"perfil de foF2 incompleto ({len(fof2)} h)")
    horas = sorted(fof2)
    hm_med = statistics.median(hmf2.values()) if hmf2 else ALTURA_POR_DEFECTO_KM
    filas = []
    for nombre, dist in DISTANCIAS_REGIONALES:
        fila = {"trayecto": nombre, "factor": solar.sec_incidence(dist, hm_med)}
        for banda, f in (("80m", 3.6), ("40m", 7.1)):
            abiertas, absorcion = estado_regional(fof2, hmf2, fmin, dist, f)
            fila[banda] = ventanas(abiertas)
            fila[banda + "_absorcion"] = ventanas(absorcion) if absorcion else None
        mufs = [fof2[h] * solar.sec_incidence(dist, hmf2.get(h, ALTURA_POR_DEFECTO_KM)) for h in horas]
        fila["muf_min"], fila["muf_max"] = min(mufs), max(mufs)
        filas.append(fila)
    dx3000 = None
    if mufd:
        dx3000 = {
            "muf_min": min(mufd.values()), "muf_max": max(mufd.values()),
            "hora_max": max(mufd, key=mufd.get),
            "bandas": [{"banda": b, "ventana": ventanas([h for h, m in mufd.items()
                                                         if m * 0.9 >= config.BANDAS[b][2]])}
                       for b in BANDAS_3000],
        }
    info = {e.ursi: e for e in config.IONOSONDAS}
    estaciones = {info[u].nombre: {h: q[1] for h, q in iono["perfiles"][u]["foF2"].items()}
                  for u in iono["usadas"]} if len(iono["usadas"]) > 1 else None
    n_iono = sum(len(iono["medidas"][u]) for u in iono["usadas"])
    p25, p75 = iono["vigo_p25"], iono["vigo_p75"]
    return {
        "ok": True,
        "estaciones": [info[u].nombre for u in iono["usadas"]],
        "interpolado": len(iono["usadas"]) > 1,
        "fof2_max": max(fof2.values()),
        "fof2_min": min(fof2.values()),
        "hora_max": max(horas, key=lambda h: fof2[h]),
        "fof2_mediana": statistics.median(fof2.values()),
        "hmf2_mediana": hm_med if hmf2 else None,
        "fmin_max": max(fmin.values()) if fmin else None,
        "filas": filas,
        "dx3000": dx3000,
        "grafica": charts.fof2_diario(
            horas, [fof2[h] for h in horas], [p25.get(h, fof2[h]) for h in horas],
            [p75.get(h, fof2[h]) for h in horas], outdir / "fof2_arenosillo.png",
            f"GIRO DIDBase · {', '.join(info[u].nombre for u in iono['usadas'])} · "
            f"{p.inicio:%d/%m}–{p.fin:%d/%m/%Y} · {n_iono} ionogramas · CS ≥ {io.CS_MINIMO}",
            estaciones=estaciones, fmin=fmin or None,
            titulo="Frecuencia crítica foF2" + (" · estimada en Vigo" if estaciones else " · El Arenosillo"),
        ).name,
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


def construir(p: Periodo, outdir: Path, sol: dict, iono: dict | None = None) -> dict:
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
        res["nvis"] = construir_nvis(p, outdir, iono or {})
    except FuenteNoDisponible as e:
        log.warning("GIRO: %s", e)
        res["nvis"] = {"ok": False, "motivo": str(e)}
    res["linea_gris"] = construir_linea_gris(p)
    res["ok"] = True
    return res
