"""Tests de los parsers de cada fuente con ficheros de ejemplo."""
import json
from datetime import date, datetime, timezone

import pytest

from propagacion import voacap
from propagacion.sources import celestrak, contests, drao, giro, noaa, rbn, wspr

from .conftest import FIX, fake_fluxtable, fake_rbn_zip, fake_tle


def test_dsd():
    dias = noaa.parse_dsd((FIX / "daily-solar-indices.txt").read_text())
    assert len(dias) == 14
    d = next(x for x in dias if x.fecha == date(2026, 9, 23))
    assert (d.sfi, d.ssn, d.flares_c, d.flares_m, d.flares_x) == (142, 127, 9, 1, 1)


def test_dgd():
    dias = noaa.parse_dgd((FIX / "daily-geomagnetic-indices.txt").read_text())
    assert len(dias) == 7
    d24 = next(x for x in dias if x.fecha == date(2026, 9, 24))
    assert d24.ap == 32 and d24.kp_max == pytest.approx(5.33)
    d27 = dias[-1]
    assert d27.ap is None and d27.kp == [1.0, 1.0, 1.33, 1.0]


def test_kp_json_lista_con_cabecera_y_objetos():
    data = json.loads((FIX / "noaa-planetary-k-index.json").read_text())
    filas = noaa.parse_kp_json(data)
    assert filas[1] == (datetime(2026, 9, 24, 6), 5.33)
    objetos = [{"time_tag": "2026-09-24T06:00:00", "Kp": 5.33}]
    assert noaa.parse_kp_json(objetos) == [(datetime(2026, 9, 24, 6), 5.33)]


def test_fulguraciones():
    f = noaa.parse_flares_json(json.loads((FIX / "xray-flares-7-day.json").read_text()))
    assert [x.clase for x in f] == ["M1.4", "X1.1", "C4.2"]
    assert f[1].maximo == datetime(2026, 9, 23, 13, 52)


def test_27do():
    dias = noaa.parse_27do((FIX / "27-day-outlook.txt").read_text())
    assert dias[0] == noaa.DiaOutlook(date(2026, 9, 28), 130, 8, 3)
    assert dias[4].kp_max == 5 and dias[4].fecha == date(2026, 10, 2)


def test_ciclo_json():
    data = [{"time-tag": "2026-08", "ssn": 90.1, "smoothed_ssn": 95.0, "f10.7": 140.2},
            {"time-tag": "2026-09", "ssn": 80.0, "smoothed_ssn": -1, "f10.7": 135.0}]
    assert noaa.parse_cycle_json(data) == [(date(2026, 8, 15), 140.2, 95.0),
                                           (date(2026, 9, 15), 135.0, None)]
    pred = noaa.parse_predicted_json([{"time-tag": "2026-10", "predicted_ssn": 88.5}])
    assert pred == {(2026, 10): 88.5}


def test_drao_usa_medida_de_20ut():
    txt = fake_fluxtable()
    serie = drao.parse_fluxtable(txt)
    assert serie[0][0] == date(2025, 9, 1)
    assert serie[0][1] == pytest.approx(170.0)
    # Valores de relleno se ignoran
    assert drao.parse_fluxtable("20260101 200000 0 0 000000.0 0 0\n") == []


def test_wspr_query_y_tsv():
    q = wspr.build_query(datetime(2026, 9, 21), datetime(2026, 9, 28), ("IN52", "IN53"))
    assert "FROM wspr.rx" in q and "'IN52','IN53'" in q and "FORMAT TabSeparatedWithNames" in q
    assert "time >= '2026-09-21 00:00:00'" in q and "time < '2026-09-28 00:00:00'" in q
    tsv = ("time\tfrequency\ttx_sign\ttx_loc\trx_sign\trx_loc\tsnr\tpower\n"
           "2026-09-21 10:02:00\t14097100\tEA1RKV\tIN52pe\tW1AW\tFN31pr\t-21\t37\n"
           "basura\n")
    spots = wspr.parse_tsv(tsv)
    assert len(spots) == 1 and spots[0].freq_mhz == pytest.approx(14.0971)


def test_rbn_filtra_distrito_ea1():
    spots = rbn.parse_zip(fake_rbn_zip(date(2026, 9, 21)))
    assert len(spots) == 2                       # el spot F5XX por DK9IP se descarta
    assert spots[0].dx == "EA1RKV" and spots[0].freq_mhz == pytest.approx(14.0251)
    assert spots[1].skimmer == "EA1RKV"


def test_giro():
    # Formato real de lgdc.uml.edu/fastchar/getbest (sept. 2026); «---» = sin medida.
    serie = giro.parse_didb((FIX / "giro_ea036.txt").read_text())
    assert serie == [(datetime(2026, 9, 20, 0, 0, 1), 3.95), (datetime(2026, 9, 20, 0, 35, 1), 3.95)]


def test_giro_parametros(monkeypatch):
    visto = {}

    def fake(url, params=None, **kw):
        visto.update(url=url, **params)
        return (FIX / "giro_ea036.txt").read_text()

    monkeypatch.setattr(giro, "fetch_text", fake)
    giro.descargar_fof2(date(2026, 9, 14), date(2026, 9, 21))
    assert visto["url"].endswith("/fastchar/getbest")
    assert visto["fromDate"] == "2026/09/14 00:00:00" and visto["toDate"] == "2026/09/21 00:00:00"
    assert visto["ursiCode"] == "EA036" and visto["charName"] == "foF2"


def test_tle_y_seleccion():
    tles = celestrak.parse_tle(fake_tle())
    assert [t[0] for t in tles] == ["ISS (ZARYA)", "SAUDISAT 1C (SO-50)"]
    sel = celestrak.select(tles, {"SO-50": ("SO-50",), "ISS": ("ISS (ZARYA)", "ISS"),
                                  "SO-5": ("SO-5",), "AO-7": ("AO-7", "AO-07")})
    assert [s[0] for s in sel] == ["SO-50", "ISS"]


def test_tle_nombres_amsat():
    # AMSAT escribe «AO-07» e «ISS»; no debe confundir AO-7 con AO-73.
    l1, l2 = fake_tle().splitlines()[1:3]
    tles = [("AO-73", l1, l2), ("AO-07", l1, l2), ("ISS", l1, l2)]
    sel = celestrak.select(tles, {"AO-7": ("AO-7", "AO-07"), "ISS": ("ISS (ZARYA)", "ISS")})
    assert [(s[0]) for s in sel] == ["AO-7", "ISS"]
    assert sel[0][1] == l1


def test_tle_respaldo_amsat(monkeypatch):
    from propagacion import config, http

    def fake(url, params=None, **kw):
        if url == config.URL_CELESTRAK_AMATEUR:
            raise http.FuenteNoDisponible("timeout")
        return fake_tle().replace("ISS (ZARYA)", "ISS")

    monkeypatch.setattr(celestrak, "fetch_text", fake)
    tles, fuente = celestrak.descargar()
    assert fuente == "amsat" and tles[0][0] == "ISS"


def _utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


@pytest.mark.parametrize("texto, ini, fin", [
    ("0000Z, Sep 26 to 2400Z, Sep 27", _utc(2026, 9, 26), _utc(2026, 9, 28)),
    ("0700Z-1000Z, Sep 27", _utc(2026, 9, 27, 7), _utc(2026, 9, 27, 10)),
    ("0000Z to 2400Z, Oct 2", _utc(2026, 10, 2), _utc(2026, 10, 3)),
    ("0000Z-0100Z, Oct 1 and 0200Z-0300Z, Oct 2", _utc(2026, 10, 1), _utc(2026, 10, 2, 3)),
    ("1700Z-1800Z, Oct 1 (CW) and 1800Z-1900Z, Oct 1 (SSB)", _utc(2026, 10, 1, 17), _utc(2026, 10, 1, 19)),
    ("2300Z-0100Z, Oct 3", _utc(2026, 10, 3, 23), _utc(2026, 10, 4, 1)),      # cruza medianoche
    ("1500Z, Dec 31 to 1500Z, Jan 1", _utc(2026, 12, 31, 15), _utc(2027, 1, 1, 15)),  # cambio de año
])
def test_horario_concursos(texto, ini, fin):
    ref = date(2026, 12, 28) if "Dec" in texto else date(2026, 9, 28)
    assert contests.parse_horario(texto, ref) == (ini, fin)


def test_horario_ilegible():
    assert contests.parse_horario("TBD", date(2026, 9, 28)) is None


def test_rss_concursos():
    ev = contests.parse_rss((FIX / "calendar.rss").read_text(), date(2026, 9, 28))
    assert len(ev) == 7
    trc = next(e for e in ev if e.nombre == "TRC DX Contest")
    assert (trc.inicio, trc.fin) == (_utc(2026, 10, 3, 6), _utc(2026, 10, 4, 18))
    assert trc.url.endswith("ref=003fltbc")


# --- VOACAP -------------------------------------------------------------------------

FREQS = [3.6, 7.1, 10.13, 14.1, 18.1, 21.1, 24.93, 28.2]


def test_voacap_deck_columnas_fijas():
    deck = voacap.build_deck((42.19, -8.71, "VIGO"), (40.71, -74.01, "NUEVA YORK"),
                             2026, 10, 110, FREQS).splitlines()
    tarjeta = {l[:10].strip(): l for l in deck if not l.startswith("ANTENNA")}
    # Campos de ancho fijo (formato Fortran del VOACAP original: 10 columnas de etiqueta).
    assert tarjeta["MONTH"] == "MONTH      202610.00"
    assert tarjeta["SUNSPOT"] == "SUNSPOT    110."
    assert tarjeta["CIRCUIT"] == "CIRCUIT   42.19N     8.71W    40.71N    74.01W  S     0"
    assert tarjeta["FREQUENCY"] == "FREQUENCY  3.60 7.1010.1314.1018.1021.1024.9328.20 0.00 0.00 0.00"
    assert tarjeta["TIME"] == "TIME          1   24    1    1"
    # Cada antena apunta al otro extremo: Vigo→NY ~291°, NY→Vigo ~65°
    antenas = [l for l in deck if l.startswith("ANTENNA")]
    assert "]291." in antenas[0] and "] 65." in antenas[1]
    assert antenas[0].endswith("    0.1000")        # 100 W


def test_voacap_demasiadas_frecuencias():
    with pytest.raises(ValueError):
        voacap.build_deck((0, 0, "A"), (1, 1, "B"), 2026, 1, 50, [7.0] * 12)


def test_voacap_parse_rel_salida_real():
    rel = voacap.parse_rel((FIX / "voacapx_vigo_ny.out").read_text(), len(FREQS))
    assert sorted(rel) == list(range(24))
    assert all(len(v) == len(FREQS) and all(0 <= x <= 1 for x in v) for v in rel.values())
    # De día (18 UTC) 10 m abierto hacia NA; de noche (03 UTC) cerrado y 40 m abierto.
    assert rel[18][7] > 0.3 and rel[3][7] == 0.0 and rel[3][1] > 0.5


@pytest.mark.skipif(not voacap.disponible(), reason="voacapl no instalado")
def test_voacap_ejecucion_real():
    deck = voacap.build_deck((42.19, -8.71, "VIGO"), (-26.2, 28.05, "JOHANNESBURGO"),
                             2026, 10, 110, FREQS)
    rel = voacap.run(deck, len(FREQS))
    assert len(rel) == 24


def test_prevision_3_dias():
    p = noaa.parse_3day((FIX / "3-day-forecast.txt").read_text(), date(2026, 9, 28))
    assert p.dias == [date(2026, 9, 28), date(2026, 9, 29), date(2026, 9, 30)]
    assert p.kp[date(2026, 9, 28)] == [1.67, 2.0, 1.67, 1.67, 1.67, 0.67, 0.67, 1.67]
    assert p.r1_r2[date(2026, 9, 28)] == 10 and p.r3[date(2026, 9, 29)] == 1
    assert p.s1[date(2026, 9, 30)] == 1


def test_prevision_3_dias_cambio_de_anio():
    txt = ("NOAA Kp index breakdown Dec 31-Jan 02 2027\n\n             Dec 31       Jan 01       Jan 02\n"
           + "".join(f"{h:02d}-{h + 3:02d}UT   1.00  2.00  3.00\n" for h in range(0, 24, 3)))
    p = noaa.parse_3day(txt, date(2026, 12, 31))
    assert p.dias == [date(2026, 12, 31), date(2027, 1, 1), date(2027, 1, 2)]


def test_xrays_canal_largo():
    data = [{"time_tag": "2026-09-22T10:58:00Z", "flux": 1.4e-5, "energy": "0.1-0.8nm"},
            {"time_tag": "2026-09-22T10:58:00Z", "flux": 2e-6, "energy": "0.05-0.4nm"},
            {"time_tag": "2026-09-22T10:59:00Z", "flux": 0.0, "energy": "0.1-0.8nm"}]
    assert noaa.parse_xrays_json(data) == [(datetime(2026, 9, 22, 10, 58), 1.4e-5)]


def test_prediccion_ciclo_f107():
    pred = noaa.parse_predicted_f107(json.loads((FIX / "predicted-solar-cycle.json").read_text()))
    assert pred[1] == (date(2026, 10, 15), 129.7, 119.6, 137.2)


def test_prevision_3_dias_lee_la_tabla_de_kp_correcta():
    """Comprobación independiente: el máximo de cada día debe salir de las columnas de la
    tabla «NOAA Kp index breakdown» del fichero real, y de ninguna otra."""
    txt = (FIX / "3-day-forecast.txt").read_text()
    bloque = txt.split("NOAA Kp index breakdown", 1)[1].split("Rationale", 1)[0]
    filas = [l.split()[1:] for l in bloque.splitlines() if l.strip()[:2].isdigit() and "UT" in l]
    assert len(filas) == 8
    esperado = [max(float(f[i]) for f in filas) for i in range(3)]
    p = noaa.parse_3day(txt, date(2026, 9, 28))
    assert [max(p.kp[d]) for d in p.dias] == esperado == [2.0, 2.0, 1.67]
    assert p.emitida == datetime(2026, 9, 28, 0, 30)


def test_prevision_3_dias_ignora_otras_tablas():
    """Una tabla de Kp observado antes del bloque de previsión no debe colarse."""
    txt = (FIX / "3-day-forecast.txt").read_text()
    intruso = ("Observed Kp\n             Sep 21       Sep 22       Sep 23\n"
               + "".join(f"{h:02d}-{h + 3:02d}UT       9.00         9.00         9.00\n" for h in range(0, 24, 3)))
    p = noaa.parse_3day(intruso + txt, date(2026, 9, 28))
    assert p.dias[0] == date(2026, 9, 28) and max(p.kp[date(2026, 9, 28)]) == 2.0
    assert date(2026, 9, 21) not in p.kp


def test_voacap_supuestos_realistas():
    p = voacap.Parametros()
    assert p.angulo_min == 3.0                       # con 0,1° elegía saltos rasantes a ~1°
    assert voacap.MODOS["FT8"] < voacap.MODOS["CW"]
    deck = voacap.build_deck((42.19, -8.71, "VIGO"), (-34.6, -58.38, "BA"), 2026, 10, 52, FREQS, p)
    assert next(l for l in deck.splitlines() if l.startswith("SYSTEM")) == "SYSTEM     0.10 145. 3.00  90. 13.0 3.00 0.10"


@pytest.mark.skipif(not voacap.disponible(), reason="voacapl no instalado")
def test_voacap_40m_a_sudamerica_abre_en_ft8():
    """Regresión: con 207 spots reales Vigo–Sudamérica en 40 m, el modelo no puede dar 0 %."""
    deck = voacap.build_deck((42.19, -8.71, "VIGO"), (-34.6, -58.38, "BA"), 2026, 10, 52,
                             [3.6, 7.1, 14.1], voacap.Parametros(snr_requerida=voacap.MODOS["FT8"]))
    rel = voacap.run(deck, 3)
    assert max(v[1] for v in rel.values()) >= 0.5
