"""Sección 1 · El Sol y el campo geomagnético (semana pasada)."""
from __future__ import annotations

import logging
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path

from .. import charts, solar
from ..http import FuenteNoDisponible
from ..periodo import MESES, Periodo, fecha_corta
from ..sources import drao, noaa

log = logging.getLogger(__name__)

FUENTES = {
    "noaa": "NOAA SWPC — índices solares y geomagnéticos diarios, flujo de rayos X y "
            "fulguraciones de GOES, previsión a 3 y 27 días y previsión del ciclo solar "
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


def comparar_prevision(valor: float, minimo: float, maximo: float) -> str:
    if valor < minimo:
        return "por debajo"
    if valor > maximo:
        return "por encima"
    return "dentro"


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
    por_dia = {d: {"fecha": fecha_corta(d), "fecha_d": d, "sfi": None, "ssn": None, "ap": None, "kp": None}
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
    # Kp trihorario (para cruzarlo con la ionosfera): del DGD y, si falta, del JSON
    kp3h = {datetime(d.fecha.year, d.fecha.month, d.fecha.day) + timedelta(hours=3 * i): k
            for d in dgd for i, k in enumerate(d.kp)}
    for t, k in kp_json:
        kp3h.setdefault(t.replace(minute=0, second=0, microsecond=0), k)
    res["kp3h"] = sorted(kp3h.items())

    # --- Fulguraciones ----------------------------------------------------------------
    fl: dict = {"lista": [], "m": 0, "x": 0}
    fulg_semana: list = []
    try:
        lista = [f for f in noaa.descargar_fulguraciones()
                 if f.inicio.date() in semana and f.clase[:1] in "MX"]
        fulg_semana = lista
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

    # --- Outlook 27 días: próxima semana y gráfica completa ----------------------
    try:
        todo27 = [d for d in noaa.descargar_27do() if d.fecha >= p.sig_inicio]
        outlook = [d for d in todo27 if d.fecha <= p.sig_fin]
        if len(todo27) >= 7:
            res["prevision27"] = {
                "grafica": charts.prevision_solar(
                    [(d.fecha, d.sfi, d.kp_max) for d in todo27], (p.sig_inicio, p.sig_fin),
                    outdir / "prevision_27dias.png",
                    "NOAA SWPC · 27-day outlook (basado en la rotación solar de ~27 días)").name,
                "sfi_min": min(d.sfi for d in todo27), "sfi_max": max(d.sfi for d in todo27),
                "hasta": fecha_corta(todo27[-1].fecha),
                "dias_kp4": [fecha_corta(d.fecha) for d in todo27 if d.kp_max >= 4],
            }
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

    # --- Previsión a 3 días: Kp y probabilidad de apagones de radio -------------------
    try:
        p3 = noaa.descargar_3dias(p.publicacion)
        # Solo días que aún no han pasado respecto a la fecha del informe
        p3.dias = [d for d in p3.dias if d >= p.publicacion - timedelta(days=1)]
        res["prevision3_emitida"] = (f"{fecha_corta(p3.emitida.date())} {p3.emitida:%H:%M} UTC"
                                     if p3.emitida else None)
        res["prevision3"] = [{
            "dia": fecha_corta(d),
            "kp_max": max(p3.kp.get(d, [0])),
            "semaforo": solar.semaforo_kp(max(p3.kp.get(d, [0]))).emoji,
            "r12": p3.r1_r2.get(d), "r3": p3.r3.get(d),
        } for d in p3.dias]
    except FuenteNoDisponible as e:
        log.warning("NOAA 3 días: %s", e)

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
    # Previsión del ciclo: los próximos 6 meses (media mensual y rango de NOAA)
    prevision_ciclo = []
    try:
        todas = noaa.descargar_prediccion_f107()
        prevision_ciclo = [x for x in todas if p.fin < x[0] <= p.fin + timedelta(days=190)]
        if prevision_ciclo:
            ult = prevision_ciclo[-1]
            res["ciclo"] = {"mes": f"{MESES[ult[0].month - 1]} de {ult[0].year}", "sfi": ult[1],
                            "min": ult[2], "max": ult[3]}
            # ¿Va el Sol por encima o por debajo de lo previsto? Media de la última rotación
            # (27 días) frente al rango previsto para el mes en curso.
            mes = next((x for x in todas if (x[0].year, x[0].month) == (p.fin.year, p.fin.month)), None)
            ultimos = [v for d, v in historico if p.fin - timedelta(days=26) <= d <= p.fin]
            if mes and len(ultimos) >= 20:
                media = statistics.fmean(ultimos)
                res["ciclo"].update(actual=media, prev_mes=mes[1], comparacion=comparar_prevision(
                    media, mes[2], mes[3]))
    except FuenteNoDisponible as e:
        log.warning("NOAA predicción ciclo: %s", e)
    if len(serie) >= 6:
        res["grafica_sfi"] = charts.sfi_tendencia(serie, outdir / "sfi_12meses.png",
                                                  (p.inicio, p.fin), fuente_graf,
                                                  prevision=prevision_ciclo or None).name

    # --- La semana del Sol: rayos X, SFI diario y Kp ------------------------------------
    try:
        xrays = [(t, f) for t, f in noaa.descargar_xrays() if t.date() in semana]
    except FuenteNoDisponible as e:
        log.warning("GOES rayos X: %s", e)
        xrays = []
    sfi_dia = sorted({d.fecha: d.sfi for d in dsd if d.fecha in semana and d.sfi}.items())
    if not sfi_dia and historico:
        sfi_dia = [(d, v) for d, v in historico if d in semana]
    if xrays or sfi_dia or res["kp3h"]:
        marcas = [(f.maximo or f.inicio, f.clase, solar.flare_class_value(f.clase))
                  for f in fulg_semana]
        res["grafica_semana"] = charts.semana_solar(
            xrays, sfi_dia, res["kp3h"], marcas,
            (datetime.combine(p.inicio, datetime.min.time()),
             datetime.combine(p.fin + timedelta(days=1), datetime.min.time())),
            outdir / "semana_solar.png",
            "Rayos X: GOES (NOAA), canal 0,1–0,8 nm · SFI y Kp: NOAA SWPC").name

    res["ok"] = "sfi" in res or "geomag" in res
    if res["ok"] or "outlook" in res:
        res["fuentes"].insert(0, FUENTES["noaa"])
    return res
