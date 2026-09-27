"""Tests de los cálculos: SSN, semáforo, distancias, MUF y línea gris."""
from datetime import date, datetime, timedelta, timezone

import pytest

from propagacion import charts, geo, solar
from propagacion.periodo import Periodo
from propagacion.sections import agenda, prevision, realidad


# --- SSN y semáforo ----------------------------------------------------------------

@pytest.mark.parametrize("sfi, ssn", [(100, 40.8), (150, 97.8), (200, 154.8), (70, 6.6)])
def test_ssn_desde_sfi(sfi, ssn):
    assert solar.ssn_from_sfi(sfi) == pytest.approx(ssn, abs=0.01)


def test_ssn_nunca_negativo():
    assert solar.ssn_from_sfi(60) == 0.0


def test_rango_validez_formula_ssn():
    assert solar.ssn_formula_valida(70) and solar.ssn_formula_valida(250)
    assert not solar.ssn_formula_valida(65) and not solar.ssn_formula_valida(260)


@pytest.mark.parametrize("kp, nivel", [(0, "tranquilo"), (3, "tranquilo"), (3.67, "tranquilo"),
                                       (4, "inquieto"), (4.67, "inquieto"), (5, "tormenta"),
                                       (9, "tormenta")])
def test_semaforo_kp(kp, nivel):
    assert solar.semaforo_kp(kp).nivel == nivel


def test_semaforo_escala_g():
    assert "G1" in solar.semaforo_kp(5).texto
    assert "G3" in solar.semaforo_kp(7.33).texto
    assert "G5" in solar.semaforo_kp(9).texto


def test_tendencia():
    assert solar.tendencia(110, 100).startswith("al alza")
    assert solar.tendencia(90, 100).startswith("a la baja")
    assert solar.tendencia(101, 100).startswith("estable")
    assert solar.tendencia(100, None) == "sin referencia"


def test_clase_fulguracion():
    assert solar.flare_class_value("X1.1") > solar.flare_class_value("M9.9")
    assert solar.flare_class_value("M2.5") == pytest.approx(2.5e-5)


# --- Locators y distancias ------------------------------------------------------------

def test_locator_vigo():
    lat, lon = geo.locator_to_latlon("IN52PE")
    assert lat == pytest.approx(42.1875, abs=1e-4)
    assert lon == pytest.approx(-8.7083, abs=1e-4)
    assert geo.latlon_to_locator(lat, lon) == "IN52pe"


def test_locator_minusculas_y_4_caracteres():
    assert geo.locator_to_latlon("in52pe") == geo.locator_to_latlon("IN52PE")
    assert geo.locator_to_latlon("IN52") == pytest.approx((42.5, -9.0))


@pytest.mark.parametrize("loc", ["", "I", "ZZ00", "IN52ZZ", "IN52PE1"])
def test_locator_invalido(loc):
    with pytest.raises(ValueError):
        geo.locator_to_latlon(loc)


def test_distancia_vigo_madrid():
    # Vigo (42.24N 8.72W) – Madrid (40.42N 3.70W): ~460 km
    assert geo.great_circle_km(42.24, -8.72, 40.42, -3.70) == pytest.approx(460, abs=10)


def test_distancia_vigo_nueva_york():
    assert geo.great_circle_km(42.24, -8.72, 40.71, -74.01) == pytest.approx(5300, abs=30)


def test_distancia_antipodas():
    assert geo.great_circle_km(0, 0, 0, 180) == pytest.approx(20015, abs=5)


def test_rumbo():
    assert geo.bearing_deg(0, 0, 10, 0) == pytest.approx(0)
    assert geo.bearing_deg(0, 0, 0, 10) == pytest.approx(90)
    # Desde Vigo, Nueva York queda al oeste-noroeste (~291°)
    assert geo.bearing_deg(42.24, -8.72, 40.71, -74.01) == pytest.approx(291.4, abs=0.5)


@pytest.mark.parametrize("lat, lon, cont", [
    (40.7, -74.0, "NA"), (-34.6, -58.4, "SA"), (35.7, 139.7, "AS"), (-33.9, 151.2, "OC"),
    (-26.2, 28.0, "AF"), (40.4, -3.7, "EU"), (55.7, 37.6, "EU"), (28.1, -15.4, "AF"),
    (37.7, -25.6, "EU"), (64.1, -21.9, "EU"), (64.2, -51.7, "NA"), (30.0, 31.2, "AF"),
    (24.7, 46.7, "AS"), (21.3, -157.8, "OC"), (9.0, -79.5, "NA"), (4.7, -74.1, "SA"),
    (36.5, -6.3, "EU"), (35.8, -5.8, "AF"), (36.8, 10.2, "AF"), (35.9, 14.5, "EU"),
    (-75.0, 0.0, "AN"), (28.6, 77.2, "AS"),
])
def test_continente(lat, lon, cont):
    assert geo.continent(lat, lon) == cont


# --- MUF -----------------------------------------------------------------------------

def test_muf_vertical_es_fof2():
    assert solar.muf_one_hop(6.0, 0) == pytest.approx(6.0)


def test_muf_crece_con_la_distancia():
    m = [solar.muf_one_hop(6.0, d) for d in (0, 200, 500, 1000, 2000, 3500)]
    assert m == sorted(m)
    # A ~3500 km el factor de la secante ronda 3-3,5 para h = 300 km
    assert 2.8 < m[-1] / 6.0 < 3.8


def test_sec_incidencia_plana_para_distancias_cortas():
    # Para 100 km la tierra es prácticamente plana: sec φ ≈ √(1+(d/2h)²)
    assert solar.sec_incidence(100) == pytest.approx((1 + (50 / 300) ** 2) ** 0.5, rel=0.01)


# --- Línea gris ------------------------------------------------------------------------

def _hm(dt):
    return dt.hour * 60 + dt.minute + dt.second / 60


@pytest.mark.parametrize("d, orto, ocaso", [
    # Vigo (42.24N, 8.72W). Referencia: tablas del IGN/USNO, ±3 min.
    (date(2026, 6, 21), 4 * 60 + 58, 20 * 60 + 15),
    (date(2026, 12, 21), 8 * 60 + 0, 17 * 60 + 6),
    (date(2026, 3, 20), 6 * 60 + 38, 18 * 60 + 47),
])
def test_orto_ocaso_vigo(d, orto, ocaso):
    o, c = solar.sun_events(42.24, -8.72, d)
    assert abs(_hm(o) - orto) < 3
    assert abs(_hm(c) - ocaso) < 3


def test_orto_ocaso_nueva_york_equinoccio():
    o, c = solar.sun_events(40.71, -74.01, date(2026, 3, 20))
    assert abs(_hm(o) - (10 * 60 + 59)) < 3        # 06:59 EDT
    assert abs(_hm(c) - (23 * 60 + 8)) < 3         # 19:08 EDT


def test_dia_polar():
    assert solar.sun_events(78.2, 15.6, date(2026, 6, 21)) == (None, None)


def test_ventanas_comunes():
    t = datetime(2026, 10, 1, 18, 0, tzinfo=timezone.utc)
    a = [("ocaso", t)]
    b = [("orto", t + timedelta(minutes=30)), ("ocaso", t + timedelta(hours=5))]
    w = prevision.ventanas_comunes(a, b, margen_min=45)
    assert len(w) == 1
    assert w[0]["inicio"] == t - timedelta(minutes=15)
    assert w[0]["fin"] == t + timedelta(minutes=45)


def test_ventanas_texto():
    assert prevision.ventanas([]) == "cerrada"
    assert prevision.ventanas(list(range(24))) == "todo el día"
    assert prevision.ventanas([6, 7, 8, 9, 17, 18]) == "06–10, 17–19 UTC"
    assert prevision.ventanas([22, 23, 0, 1]) == "22–02 UTC"


# --- Varios ----------------------------------------------------------------------------

@pytest.mark.parametrize("f, banda", [(7.0401, "40m"), (14.0971, "20m"), (28.1261, "10m"),
                                      (50.294, "6m"), (144.489, "2m"), (13.0, None)])
def test_banda_de(f, banda):
    assert realidad.banda_de(f) == banda


def test_heatmap_edges():
    assert charts.heatmap_edges(1) == [0, 1, 2]
    e = charts.heatmap_edges(3000)
    assert e[0] == 0 and e[1] == 1 and e[-1] == 3001
    assert len(e) - 1 <= 7 and e == sorted(e)


def test_lluvia_que_cruza_el_anio():
    ini, mx, fin = agenda.rango_lluvia(agenda.LLUVIAS[0], 2027)     # Cuadrántidas
    assert ini == date(2026, 12, 28) and mx == date(2027, 1, 3) and fin == date(2027, 1, 12)


def test_lluvias_activas_en_agosto():
    nombres = [l["nombre"] for l in agenda.lluvias_activas(date(2026, 8, 10), date(2026, 8, 16))]
    assert "Perseidas" in nombres
    assert "Gemínidas" not in nombres


@pytest.mark.parametrize("hoy, publicacion", [
    (date(2026, 9, 28), date(2026, 9, 28)),     # lunes: el propio lunes
    (date(2026, 9, 30), date(2026, 9, 28)),     # miércoles: el lunes de esa semana
    (date(2026, 9, 27), date(2026, 9, 28)),     # domingo: ya cuenta como el lunes siguiente
])
def test_periodo(hoy, publicacion):
    p = Periodo.para(hoy)
    assert p.publicacion == publicacion
    assert (p.inicio, p.fin) == (publicacion - timedelta(days=7), publicacion - timedelta(days=1))
    assert p.sig_inicio == publicacion and p.etiqueta == "2026-W40"
