"""Sección 1 · El Sol y el campo geomagnético (semana pasada)."""
from __future__ import annotations

import logging
import statistics
from datetime import date, timedelta
from pathlib import Path

from .. import charts, solar
from ..http import FuenteNoDisponible
from ..periodo import Periodo, fecha_corta
from ..sources import drao, noaa

log = logging.getLogger(__name__)

FUENTES = {
    "noaa": "NOAA SWPC — daily solar/geomagnetic indices, GOES X-ray flares, 27-day outlook "
            "(https://www.swpc.noaa.gov/)",
    "drao": "NRC Canada / DRAO Penticton — histórico diario del flujo F10.7 "
            "(https://www.spaceweather.gc.ca/)",
}


def _resumen_sfi(valores: list[float]) -> dict:
    return {
        "media": statistics.fmean(valores),
        "max": max(valores),
        "min": min(valores),
    }


def construir(p: Periodo, outdir: Path) -> dict:
    res: dict = {"ok": False, "fuentes": [], "avisos": []}
    semana = set(p.dias())
    anterior = {p.prev_inicio + timedelta(days=i) for i in range(7)}

    # --- Flujo solar y manchas (NOAA DSD) ----------------------------------------
    dsd: list[noaa.DiaSolar] = []
    try:
        dsd = noaa.descargar_dsd()
    except FuenteNoDisponible as e:
        log.warning("NOAA DSD: %s", e)
        res["avisos"].append("Flujo solar diario de NOAA no disponible.")
    sfi_sem = [d.sfi for d in dsd if d.fecha in semana and d.sfi]
    sfi_ant = [d.sfi for d in dsd if d.fecha in anterior and d.sfi]

    # Si NOAA falla, el histórico de DRAO también da el SFI de la semana.
    historico: list[tuple[date, float]] = []
    try:
        historico = drao.descargar_historico()
        res["fuentes"].append(FUENTES["drao"])
    except FuenteNoDisponible as e:
        log.warning("DRAO: %s", e)
    if not sfi_sem and historico:
        sfi_sem = [v for d, v in historico if d in semana]
        sfi_ant = [v for d, v in historico if d in anterior]

    if sfi_sem:
        r = _resumen_sfi(sfi_sem)
        r["tendencia"] = solar.tendencia(r["media"], statistics.fmean(sfi_ant) if sfi_ant else None)
        r["media_anterior"] = statistics.fmean(sfi_ant) if sfi_ant else None
        r["ssn_efectivo"] = solar.ssn_from_sfi(r["media"])
        r["ssn_formula_valida"] = solar.ssn_formula_valida(r["media"])
        ssn_obs = [d.ssn for d in dsd if d.fecha in semana and d.ssn is not None]
        r["ssn_observado"] = statistics.fmean(ssn_obs) if ssn_obs else None
        res["sfi"] = r

    # --- Geomagnetismo (NOAA DGD + Kp JSON) --------------------------------------
    dgd: list[noaa.DiaGeomag] = []
    try:
        dgd = [d for d in noaa.descargar_dgd() if d.fecha in semana]
    except FuenteNoDisponible as e:
        log.warning("NOAA DGD: %s", e)
    kp_json: list = []
    try:
        kp_json = [(t, k) for t, k in noaa.descargar_kp() if t.date() in semana]
    except FuenteNoDisponible as e:
        log.warning("NOAA Kp: %s", e)
    aps = [d.ap for d in dgd if d.ap is not None]
    kps = [d.kp_max for d in dgd if d.kp_max is not None] + [k for _, k in kp_json]
    if aps or kps:
        g: dict = {}
        if aps:
            g["ap_medio"] = statistics.fmean(aps)
            g["ap_max"] = max(aps)
        if kps:
            g["kp_max"] = max(kps)
            g["semaforo"] = solar.semaforo_kp(g["kp_max"])
            g["dias_inquietos"] = sum(1 for d in dgd if (d.kp_max or 0) >= 4)
        res["geomag"] = g
    else:
        res["avisos"].append("Índices geomagnéticos no disponibles.")

    # --- Tabla diaria -------------------------------------------------------------
    por_dia = {d: {"fecha": fecha_corta(d), "sfi": None, "ssn": None, "ap": None, "kp": None}
               for d in p.dias()}
    for d in dsd:
        if d.fecha in por_dia:
            por_dia[d.fecha].update(sfi=d.sfi, ssn=d.ssn)
    for d in dgd:
        por_dia[d.fecha].update(ap=d.ap, kp=d.kp_max)
    for t, k in kp_json:
        cur = por_dia[t.date()]["kp"]
        por_dia[t.date()]["kp"] = k if cur is None else max(cur, k)
    for fila in por_dia.values():
        fila["semaforo"] = solar.semaforo_kp(fila["kp"]).emoji if fila["kp"] is not None else "—"
    res["dias"] = list(por_dia.values())

    # --- Fulguraciones ----------------------------------------------------------------
    fl: dict = {"lista": [], "m": 0, "x": 0}
    try:
        lista = [f for f in noaa.descargar_fulguraciones()
                 if f.inicio.date() in semana and f.clase[:1] in "MX"]
        lista.sort(key=lambda f: solar.flare_class_value(f.clase), reverse=True)
        fl["lista"] = [{"clase": f.clase, "cuando": f"{fecha_corta(f.inicio.date())} "
                        f"{(f.maximo or f.inicio):%H:%M} UTC"} for f in lista]
        fl["m"] = sum(1 for f in lista if f.clase.startswith("M"))
        fl["x"] = sum(1 for f in lista if f.clase.startswith("X"))
    except FuenteNoDisponible as e:
        log.warning("NOAA flares: %s", e)
    # El JSON solo cubre 7 días: completar con los recuentos del DSD si hace falta.
    if not fl["lista"] and dsd:
        fl["m"] = sum(d.flares_m for d in dsd if d.fecha in semana)
        fl["x"] = sum(d.flares_x for d in dsd if d.fecha in semana)
    res["fulguraciones"] = fl

    # --- Outlook 27 días: próxima semana -----------------------------------------
    try:
        outlook = [d for d in noaa.descargar_27do() if p.sig_inicio <= d.fecha <= p.sig_fin]
        if outlook:
            res["outlook"] = {
                "sfi_min": min(d.sfi for d in outlook),
                "sfi_max": max(d.sfi for d in outlook),
                "sfi_medio": statistics.fmean(d.sfi for d in outlook),
                "ap_max": max(d.ap for d in outlook),
                "kp_max": max(d.kp_max for d in outlook),
                "semaforo": solar.semaforo_kp(max(d.kp_max for d in outlook)),
                "dias_kp4": [fecha_corta(d.fecha) for d in outlook if d.kp_max >= 4],
            }
    except FuenteNoDisponible as e:
        log.warning("NOAA 27DO: %s", e)

    # --- Gráfica del SFI (12 meses) --------------------------------------------------
    desde = p.fin - timedelta(days=365)
    serie = [(d, v) for d, v in historico if desde <= d <= p.fin]
    fuente_graf = "DRAO Penticton (flujo observado, 20 UT)"
    if len(serie) < 60:
        try:
            ciclo = noaa.descargar_ciclo()
            serie = [(d, f) for d, f, _ in ciclo if f and desde <= d <= p.fin]
            fuente_graf = "NOAA SWPC (media mensual)"
        except FuenteNoDisponible as e:
            log.warning("NOAA ciclo: %s", e)
    if len(serie) >= 6:
        res["grafica_sfi"] = charts.sfi_tendencia(serie, outdir / "sfi_12meses.png",
                                                  (p.inicio, p.fin), fuente_graf).name

    res["ok"] = "sfi" in res or "geomag" in res
    if res["ok"] or "outlook" in res:
        res["fuentes"].insert(0, FUENTES["noaa"])
    return res
