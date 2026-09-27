"""La ionosfera medida: digisondas de El Arenosillo, Roquetes y Dourbes (GIRO).

``medir`` descarga y prepara los datos (perfiles limpios de cada estación y su
interpolación a Vigo); ``construir`` redacta el bloque del informe: comparación
con lo normal junto al Kp, esporádica E, cruce MUF–WSPR y notas curiosas.
Los perfiles para Vigo también los usa la previsión NVIS (sección 3).
"""
from __future__ import annotations

import logging
import statistics
from collections import Counter
from datetime import timedelta
from pathlib import Path

from .. import charts, config, geo, ionosfera as io
from ..http import FuenteNoDisponible
from ..periodo import Periodo, fecha_corta
from ..sources import giro

log = logging.getLogger(__name__)

FUENTE = ("GIRO / DIDBase, Lowell GIRO Data Center (https://giro.uml.edu/), datos CC-BY-NC-SA 4.0 "
          "de las digisondas de {estaciones}")
PROVEEDORES = {"EA036": "El Arenosillo (INTA)", "EB040": "Roquetes (Observatori de l'Ebre)",
               "DB049": "Dourbes (RMI Bélgica)"}

# Magnitudes que llevamos a la latitud de Vigo (la Es es local y no se interpola).
INTERPOLADAS = ("foF2", "MUF(D)", "M(D)", "hmF2", "fmin")
DIAS_REFERENCIA = 30


def medir(p: Periodo) -> dict:
    lat0, lon0 = geo.locator_to_latlon(config.STATION_LOCATOR)
    medidas: dict[str, list[io.Medida]] = {}
    for est in config.IONOSONDAS:
        try:
            medidas[est.ursi] = giro.descargar(est.ursi, p.inicio, p.fin + timedelta(days=1))
        except FuenteNoDisponible as e:
            log.warning("GIRO %s: %s", est.ursi, e)
    if not medidas:
        raise FuenteNoDisponible("ninguna ionosonda con datos esta semana")
    # Solo la semana analizada (el servicio puede devolver algo del día siguiente)
    medidas = {u: [m for m in ms if p.inicio <= m.time.date() <= p.fin] for u, ms in medidas.items()}

    info = {e.ursi: e for e in config.IONOSONDAS}
    limpio = {u: {c: io.limpiar(ms, c) for c in giro.CARACTERISTICAS} for u, ms in medidas.items()}
    perfiles = {u: {c: io.perfil(s) for c, s in cs.items()} for u, cs in limpio.items()}

    def interp(car: str, idx: int) -> dict[int, float]:
        porest = {u: {h: q[idx] for h, q in perfiles[u][car].items()} for u in perfiles}
        coords = {u: (info[u].lat, info[u].lon) for u in porest}
        return io.perfil_interpolado(porest, coords, lat0, lon0)

    vigo = {c: interp(c, 1) for c in INTERPOLADAS}
    usadas = [u for u in medidas if perfiles[u]["foF2"]]
    if not usadas:
        raise FuenteNoDisponible("ninguna ionosonda con foF2 válida tras el control de calidad")

    # Referencia «normal»: mediana horaria de los 30 días anteriores en El Arenosillo
    referencia: dict[int, float] = {}
    try:
        previas = giro.descargar(config.GIRO_URSI_ARENOSILLO, p.inicio - timedelta(days=DIAS_REFERENCIA),
                                 p.inicio, ("foF2",))
        referencia = io.mediana_horaria(io.limpiar(previas, "foF2"), minimo=10)
    except FuenteNoDisponible as e:
        log.warning("GIRO referencia: %s", e)

    return {
        "ok": True,
        "medidas": medidas,
        "limpio": limpio,
        "perfiles": perfiles,
        "vigo": vigo,
        "vigo_p25": interp("foF2", 0),
        "vigo_p75": interp("foF2", 2),
        "usadas": usadas,
        "referencia": referencia,
        "descartadas": {u: 1 - len(limpio[u]["foF2"]) / max(1, sum(m.get("foF2") is not None for m in ms))
                        for u, ms in medidas.items()},
    }


def fuente(iono: dict) -> str:
    return FUENTE.format(estaciones=", ".join(PROVEEDORES.get(u, u) for u in iono.get("usadas", [])))


# --- Bloques del informe ---------------------------------------------------------------

def _anomalia(p: Periodo, iono: dict, sol: dict, outdir: Path) -> dict | None:
    ref = iono["referencia"]
    serie = iono["limpio"].get(config.GIRO_URSI_ARENOSILLO, {}).get("foF2", [])
    if not ref or not serie:
        return None
    desv = io.desviacion_relativa(serie, ref)
    horaria = io.desviacion_horaria(desv)
    diaria = io.desviacion_diaria(desv)
    if not diaria:
        return None
    kp_dia = {d["fecha_d"]: d["kp"] for d in sol.get("dias", []) if d.get("kp") is not None}
    dias = []
    for d, v in diaria.items():
        kp_ant = max((k for dd, k in kp_dia.items() if d - timedelta(days=2) <= dd <= d), default=None)
        dias.append({"fecha": fecha_corta(d), "desv": v, "kp_48h": kp_ant,
                     "negativa": v <= io.UMBRAL_TORMENTA_NEGATIVA})
    peor = min(dias, key=lambda x: x["desv"])
    grafica = charts.anomalia_fof2(horaria, sol.get("kp3h", []), outdir / "fof2_vs_normal.png",
                                   (p.inicio, p.fin + timedelta(days=1)),
                                   f"El Arenosillo · referencia: mediana de los {DIAS_REFERENCIA} días "
                                   f"anteriores a la misma hora")
    return {"dias": dias, "peor": peor, "media": statistics.fmean(diaria.values()),
            "tormenta": [d for d in dias if d["negativa"]], "grafica": grafica.name}


def _esporadica(p: Periodo, iono: dict, contactos) -> dict:
    """Episodios de Es por estación y spots de 6/10 m compatibles con un salto de Es."""
    info = {e.ursi: e for e in config.IONOSONDAS}
    episodios = []
    for u, cs in iono["limpio"].items():
        for umbral, banda in ((10.0, "6m"), (5.6, "10m")):
            for ep in io.episodios_es(cs.get("foEs", []), umbral):
                episodios.append({"estacion": info[u].nombre, "banda": banda, "ep": ep})
    # Nos quedamos con el umbral más alto por episodio: si hubo 6 m, no repetimos 10 m.
    seis = [e for e in episodios if e["banda"] == "6m"]
    diez = [e for e in episodios if e["banda"] == "10m"
            and not any(s["estacion"] == e["estacion"] and s["ep"].inicio <= e["ep"].fin
                        and e["ep"].inicio <= s["ep"].fin for s in seis)]
    maximos = {info[u].nombre: max((v for _, v in cs.get("foEs", [])), default=None)
               for u, cs in iono["limpio"].items()}

    def fila(e):
        ep = e["ep"]
        return {"estacion": e["estacion"], "dia": fecha_corta(ep.inicio.date()),
                "desde": f"{ep.inicio:%H:%M}", "hasta": f"{ep.fin:%H:%M}",
                "foes": ep.foes_max, "muf": ep.muf_max, "banda": e["banda"],
                "_i": ep.inicio - timedelta(minutes=15), "_f": ep.fin + timedelta(minutes=15)}

    filas = sorted((fila(e) for e in seis + diez), key=lambda f: (-f["foes"]))[:8]
    # Cruce con spots reales de 6 y 10 m a distancia de un salto de Es
    spots = [c for c in (contactos or []) if c.banda in ("6m", "10m")
             and c.distancia_km is not None and 800 <= c.distancia_km <= 2500]
    for f in filas:
        f["spots"] = sum(1 for c in spots if c.banda == f["banda"] and f["_i"] <= c.time <= f["_f"])
    for f in filas:
        del f["_i"], f["_f"]
    return {"episodios": sorted(filas, key=lambda f: (f["dia"], f["desde"])),
            "hubo_6m": bool(seis), "hubo_10m": bool(seis or diez),
            "maximos": {k: v for k, v in maximos.items() if v is not None},
            "spots_es": len(spots), "hay_contactos": contactos is not None}


BANDAS_CRUCE = ("20m", "17m", "15m", "12m", "10m")


def _cruce_muf(iono: dict, contactos) -> dict | None:
    """¿Coincide lo que dice la MUF(3000) medida con lo que se oyó a ~3000 km?

    Se compara hora a hora en las bandas altas, que es donde está la frontera:
    para cada casilla (hora, banda) la teoría dice «abre» si la MUF(3000) mediana
    de esa hora supera la banda, y la realidad dice «abrió» si hubo algún spot
    de esa banda a 2000-4000 km a esa hora algún día de la semana.
    """
    muf = iono["vigo"].get("MUF(D)") or {}
    if not muf or not contactos:
        return None
    oidas = {(c.time.hour, c.banda) for c in contactos
             if c.distancia_km is not None and 2000 <= c.distancia_km <= 4000 and c.banda in BANDAS_CRUCE}
    bandas = [b for b in BANDAS_CRUCE if any(bb == b for _, bb in oidas)]
    if not oidas or not bandas:
        return None
    acierto = abre_sin_spots = spots_sin_muf = 0
    sorpresas: Counter = Counter()
    for h in sorted(muf):
        for b in bandas:
            teoria = config.BANDAS[b][2] <= muf[h] * 1.1
            real = (h, b) in oidas
            if teoria == real:
                acierto += 1
            elif teoria:
                abre_sin_spots += 1
            else:
                spots_sin_muf += 1
                sorpresas[b] += 1
    total = acierto + abre_sin_spots + spots_sin_muf
    return {"casillas": total, "bandas": bandas, "pct_acierto": 100 * acierto / total,
            "abre_sin_spots": abre_sin_spots, "spots_sin_muf": spots_sin_muf,
            "sorpresas": [b for b, _ in sorpresas.most_common(2)]}


def _curiosidades(iono: dict) -> dict:
    ursi = config.GIRO_URSI_ARENOSILLO if config.GIRO_URSI_ARENOSILLO in iono["medidas"] else iono["usadas"][0]
    medidas = iono["medidas"][ursi]
    horas_sf = io.horas_spread_f(medidas)
    noches = sorted({(h - timedelta(hours=12)).date() for h in horas_sf})
    f1 = iono["limpio"][ursi].get("foF1", [])
    hm = iono["perfiles"][ursi].get("hmF2", {})
    dia_hm = [hm[h][1] for h in range(10, 15) if h in hm]
    noche_hm = [hm[h][1] for h in (22, 23, 0, 1, 2) if h in hm]
    nombre = next(e.nombre for e in config.IONOSONDAS if e.ursi == ursi)
    return {
        "estacion": nombre,
        "noches_spread_f": len(noches),
        "horas_spread_f": len(horas_sf),
        "fof1_max": max((v for _, v in f1), default=None),
        "fof1_hora": max(f1, key=lambda x: x[1])[0].strftime("%H:%M") if f1 else None,
        "hmf2_dia": statistics.median(dia_hm) if dia_hm else None,
        "hmf2_noche": statistics.median(noche_hm) if noche_hm else None,
    }


def construir(p: Periodo, outdir: Path, iono: dict, sol: dict, contactos) -> dict:
    if not iono.get("ok"):
        return {"ok": False, "fuentes": [], "avisos": []}
    info = {e.ursi: e for e in config.IONOSONDAS}
    return {
        "ok": True,
        "fuentes": [fuente(iono)],
        "avisos": [],
        "estaciones": [{"nombre": info[u].nombre, "lat": info[u].lat,
                        "descartadas": 100 * iono["descartadas"].get(u, 0)} for u in iono["usadas"]],
        "anomalia": _anomalia(p, iono, sol, outdir),
        "es": _esporadica(p, iono, contactos),
        "cruce": _cruce_muf(iono, contactos),
        "curiosidades": _curiosidades(iono),
        "cs_minimo": io.CS_MINIMO,
    }
