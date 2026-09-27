"""Tests de los parsers de cada fuente con ficheros de ejemplo."""
import json
from datetime import date, datetime

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
    serie = giro.parse_didb((FIX / "giro_ea036.txt").read_text())
    assert serie == [(datetime(2026, 9, 21, 0, 0), 4.525), (datetime(2026, 9, 21, 12, 0), 9.875)]


def test_tle_y_seleccion():
    tles = celestrak.parse_tle(fake_tle())
    assert [t[0] for t in tles] == ["ISS (ZARYA)", "SAUDISAT 1C (SO-50)"]
    sel = celestrak.select(tles, ("SO-50", "ISS (ZARYA)", "SO-5", "AO-7"))
    assert [s[0] for s in sel] == ["SO-50", "ISS (ZARYA)"]


def test_ics():
    ev = contests.parse_ics((FIX / "calendar.ics").read_text())
    assert ev[0].nombre == "CQ World Wide DX Contest, RTTY"
    assert ev[1].url.endswith("contestdetails.php?ref=2")      # línea plegada
    assert ev[0].inicio.isoformat() == "2026-10-03T00:00:00+00:00"


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
