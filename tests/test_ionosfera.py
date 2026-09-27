"""Tests del análisis de ionosondas: calidad, interpolación, LUF, Es y anomalías."""
from datetime import date, datetime, timedelta

import pytest

from propagacion import charts, ionosfera as io
from propagacion.sections import prevision
from propagacion.sources import giro

from .conftest import FIX


def _serie(valores, inicio=datetime(2026, 9, 21, 10), paso=5, car="foF2", cs=90):
    return [io.Medida(inicio + timedelta(minutes=paso * i), cs, {car: v}) for i, v in enumerate(valores)]


# --- Formato real de fastchar/getbest -------------------------------------------------------

def test_parse_getbest_varias_magnitudes():
    ms = giro.parse_getbest((FIX / "giro_multi.txt").read_text(),
                            ("foF2", "foF1", "foEs", "MUF(D)", "M(D)", "hmF2", "FF", "QF", "fmin", "foF2p"))
    assert len(ms) == 12
    m = ms[0]
    assert m.cs == 95 and m.get("foF2") == 7.175 and m.get("MUF(D)") == 22.473
    assert m.get("M(D)") == 3.14 and m.get("hmF2") == 260.7 and m.get("fmin") == 1.95
    assert m.get("QF") is None                      # «--- __» = sin valor
    assert ms[1].get("foF1") is None


def test_error_de_autoescalado_real_se_descarta():
    """10:50 en El Arenosillo (20/9/2026): foF2 = 11,8 con CS 50 entre valores de ~7,9."""
    ms = giro.parse_getbest((FIX / "giro_multi.txt").read_text(), ("foF2",))
    limpio = dict(io.limpiar(ms, "foF2", cs_min=45))   # aunque dejemos pasar CS 50…
    assert datetime(2026, 9, 20, 10, 50, 1) not in limpio   # …el filtro de vecinos lo quita
    assert len(limpio) == 11


# --- Control de calidad ------------------------------------------------------------------------

def test_filtro_confianza():
    ms = _serie([7.0, 7.1], cs=90) + _serie([7.2], cs=50, inicio=datetime(2026, 9, 21, 11))
    ms.append(io.Medida(datetime(2026, 9, 21, 12), 999, {"foF2": 7.3}))      # escalado manual
    assert [m.cs for m in io.filtrar_confianza(ms)] == [90, 90, 999]


def test_atipico_y_valor_aislado():
    vals = [7.0, 7.1, 7.2, 12.5, 7.3, 7.2, 7.1]
    limpio = [v for _, v in io.quitar_atipicos(_serie(vals), "foF2")]
    assert 12.5 not in limpio and len(limpio) == 6
    aislado = _serie([7.0]) + _serie([7.1], inicio=datetime(2026, 9, 21, 20))
    assert io.quitar_atipicos(aislado, "foF2") == []


def test_perfil_horario():
    serie = [(datetime(2026, 9, 21, 12, m), v) for m, v in ((0, 8.0), (15, 9.0), (30, 10.0))]
    assert io.perfil(serie)[12] == (8.5, 9.0, 9.5)
    assert io.perfil(serie[:2]) == {}                # menos de 3 datos: fuera


# --- Interpolación a Vigo ------------------------------------------------------------------------

def test_valor_en_hora_circular():
    perf = {23: 4.0, 0: 6.0, 12: 9.0}
    assert io.valor_en_hora(perf, 23.5) == pytest.approx(5.0)
    assert io.valor_en_hora(perf, 12.2) == 9.0
    assert io.valor_en_hora(perf, 6.0) is None


def test_hora_local():
    # Una estación 15° al este llega a la misma hora solar 1 h antes (en UTC): lo que vive
    # Vigo a las 12 UTC es lo que midió esa estación a las 11 UTC.
    perf = {h: float(h) for h in range(24)}
    local = io.a_hora_local_de(perf, lon_estacion=6.3, lon_destino=-8.7)
    assert local[12] == pytest.approx(11.0)


def test_interpolar_latitud():
    assert io.interpolar_latitud([(37.1, 9.0), (50.1, 7.7)], 42.2) == pytest.approx(8.49, abs=0.01)
    assert io.interpolar_latitud([(37.1, 9.0)], 42.2) == 9.0
    # Con tres estaciones, ajuste lineal por mínimos cuadrados
    assert io.interpolar_latitud([(37.1, 9.0), (40.8, 8.6), (50.1, 7.7)], 42.2) == pytest.approx(8.48, abs=0.03)
    # Demasiado lejos del rango cubierto: la más próxima
    assert io.interpolar_latitud([(37.1, 9.0), (38.0, 8.9)], 45.0) == 8.9
    assert io.interpolar_latitud([], 42.2) is None


def test_perfil_interpolado():
    perfiles = {"S": {h: 9.0 for h in range(24)}, "N": {h: 7.0 for h in range(24)}}
    coords = {"S": (38.0, -8.7), "N": (46.0, -8.7)}
    vigo = io.perfil_interpolado(perfiles, coords, 42.0, -8.7)
    assert vigo[12] == pytest.approx(8.0)


# --- MUF, LUF y estado de las bandas ------------------------------------------------------------------

def test_luf_absorcion():
    assert io.luf_absorcion(2.0, 0) == pytest.approx(2.0)
    assert io.luf_absorcion(2.0, 900) > io.luf_absorcion(2.0, 460) > 2.0


def test_estado_banda():
    assert io.estado_banda(3.6, muf=6.0, luf=2.0) == "abierta"
    assert io.estado_banda(3.6, muf=6.0, luf=3.9) == "absorcion"
    assert io.estado_banda(7.1, muf=7.5, luf=2.0) == "muf"        # 7,5·0,9 < 7,1
    assert io.estado_banda(7.1, muf=None, luf=None) == "muf"


def test_estado_regional_usa_hmf2_y_fmin():
    fof2 = {h: 6.0 for h in range(24)}
    fmin = {h: (4.0 if 10 <= h < 14 else 1.5) for h in range(24)}
    abiertas, absorcion = prevision.estado_regional(fof2, {h: 250.0 for h in range(24)}, fmin, 460, 3.6)
    assert absorcion == [10, 11, 12, 13]
    assert len(abiertas) == 20
    # Con la capa más alta la secante es menor y la MUF baja
    muf_baja = 6.0 * prevision.solar.sec_incidence(460, 350)
    muf_alta = 6.0 * prevision.solar.sec_incidence(460, 250)
    assert muf_baja < muf_alta


def test_techo_muf_en_el_mapa_de_calor():
    bandas = ["10m", "15m", "20m", "40m"]
    freqs = {"10m": 28.2, "15m": 21.1, "20m": 14.1, "40m": 7.1}
    techo = dict(charts.techo_muf(bandas, freqs, {0: 10.0, 12: 30.0, 18: 22.0}))
    assert techo == {0: 2.5, 12: -0.5, 18: 0.5}


# --- Esporádica E ---------------------------------------------------------------------------

def test_episodios_es():
    t0 = datetime(2026, 6, 20, 14)
    serie = [(t0 + timedelta(minutes=15 * i), v) for i, v in enumerate([4, 11, 12.5, 10.5, 4, 4, 4, 10.2])]
    eps = io.episodios_es(serie, 10.0)
    assert len(eps) == 2
    assert eps[0].inicio == t0 + timedelta(minutes=15) and eps[0].fin == t0 + timedelta(minutes=45)
    assert eps[0].foes_max == 12.5 and eps[0].muf_max == pytest.approx(62.5)


# --- Comparación con lo normal y spread-F ------------------------------------------------------------

def test_desviacion():
    ref = {12: 8.0, 13: 10.0}
    serie = [(datetime(2026, 9, 25, 12), 6.0), (datetime(2026, 9, 25, 13), 7.0),
             (datetime(2026, 9, 25, 14), 9.0)]
    desv = io.desviacion_relativa(serie, ref)
    assert [round(d) for _, d in desv] == [-25, -30]
    assert io.desviacion_diaria(desv) == {date(2026, 9, 25): pytest.approx(-27.5)}


def test_spread_f():
    base = datetime(2026, 9, 22, 2)
    ms = [io.Medida(base, 90, {"FF": 0.9}), io.Medida(base + timedelta(minutes=10), 90, {"QF": 40.0}),
          io.Medida(base + timedelta(hours=10), 90, {"FF": 0.1}),
          io.Medida(base + timedelta(hours=1), 40, {"FF": 1.2})]          # CS baja: no cuenta
    assert io.horas_spread_f(ms) == [base]


def test_fof1_imposible_se_descarta():
    """ARTIST a veces etiqueta como F1 una traza por encima de la F2: imposible."""
    t0 = datetime(2026, 9, 21, 10)
    ms = [io.Medida(t0 + timedelta(minutes=5 * i), 90, {"foF2": 7.5, "foF1": 5.0}) for i in range(5)]
    ms.append(io.Medida(t0 + timedelta(minutes=27), 90, {"foF2": 7.6, "foF1": 8.1}))   # F1 > F2
    ms.append(io.Medida(t0 + timedelta(minutes=33), 90, {"foF2": 11.9, "foF1": 8.0}))  # todo disparado
    assert max(v for _, v in io.limpiar(ms, "foF1")) == 5.0


def test_cruce_teoria_realidad():
    from types import SimpleNamespace as NS

    from propagacion.sections import ionosfera as sec

    iono = {"vigo": {"MUF(D)": {10: 15.0, 14: 25.0}}}
    c = [NS(time=datetime(2026, 9, 21, 14), banda="15m", distancia_km=3000),     # MUF 25: acierto
         NS(time=datetime(2026, 9, 22, 10), banda="15m", distancia_km=3000),     # MUF 15: sorpresa
         NS(time=datetime(2026, 9, 22, 14), banda="20m", distancia_km=500)]       # demasiado cerca
    r = sec._cruce_muf(iono, c)
    assert r["bandas"] == ["15m"] and r["casillas"] == 2
    assert r["pct_acierto"] == 50 and r["spots_sin_muf"] == 1 and r["sorpresas"] == ["15m"]
