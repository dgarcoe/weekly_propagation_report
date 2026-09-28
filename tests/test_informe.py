"""Test de extremo a extremo: genera el informe completo con la «internet falsa»."""
import pytest

from propagacion import http, report, voacap
from propagacion.__main__ import main

from .conftest import FECHA_INFORME


def test_informe_completo(internet_falsa, tmp_path):
    out = tmp_path / "informe"
    md_path = report.generar(FECHA_INFORME, out)
    md = md_path.read_text()

    # Cabecera y periodo
    assert "semana 2026-W40" in md
    assert "21 de septiembre de 2026 – 27 de septiembre de 2026" in md

    # Sección 1
    assert "media **137**" in md                       # SFI medio 21-27/9 del fixture: 136,7
    assert "Kp máximo **5,33**" in md and "🔴" in md
    assert "**X1.1**" in md
    assert (out / "sfi_12meses.png").stat().st_size > 10_000
    assert "Kp máximo 5" in md                           # outlook: 2/10 con Kp 5
    # La semana del Sol y la previsión
    for png in ("semana_solar.png", "prevision_27dias.png"):
        assert (out / png).stat().st_size > 10_000
    assert "| lun 28/9 | 2,00 | 🟢 | 10 % | 1 % |" in md             # previsión a 3 días
    assert "**Hasta el lun 5/10:**" in md                           # 27 días
    assert "emitida el lun 28/9 00:30 UTC" in md
    # RBN es del distrito EA1, no solo de Galicia; la rosa cuenta locators (solo WSPR)
    assert "del **distrito EA1**" in md and "Solo WSPR, porque el RBN no da locator" in md
    # VOACAP: FT8 como previsión principal y tabla adicional en CW
    if voacap.disponible():
        assert "**En FT8**" in md and "**En CW**" in md
    assert "NOAA prevé para marzo de 2027 un SFI medio mensual de" in md
    assert "va según lo previsto" in md or "**Ojo:**" in md             # media 27 d vs rango del mes

    # Sección 2
    assert "Spots desde/hacia Galicia" not in md        # el título va en la imagen, no en el texto
    assert (out / "heatmap_hora_banda.png").exists()
    assert (out / "rutas_continentes.png").exists()
    assert "### DX de la semana por banda" in md
    assert "VK2XX" in md or "JA1ABC" in md               # el DX más lejano sale en la tabla

    # Sección 3
    if voacap.disponible():
        assert (out / "voacap_fiabilidad.png").exists()
        assert "SSN usado" in md
    assert (out / "fof2_arenosillo.png").exists()
    assert "Vigo – Madrid" in md

    # La ionosfera medida (varias ionosondas, datos sintéticos de conftest)
    assert "Roquetes (Ebro)" in md and "Dourbes" in md and "estimada en Vigo" in md
    assert "**Tormenta ionosférica negativa:** el vie 25/9" in md        # tras el Kp 5,33 del 24
    assert (out / "fof2_vs_normal.png").exists()
    assert "**Sí, y fuerte:**" in md                                     # Es de 12 MHz en Roquetes
    assert "#### Teoría frente a realidad" in md and "casillas hora × banda" in md
    assert "MUF(3000)F2 medida" in md and "_absorción:" in md
    assert "se vio en 2 noche(s)" in md                                  # spread-F 22 y 26
    assert "amanece a las" in md

    # Sección 4
    assert "TRC DX Contest" in md and "URC DX RTTY Contest" in md
    assert "RSGB FT4 Contest" not in md                 # lunes: fuera del fin de semana
    assert "Oriónidas" in md
    assert "| ISS |" in md

    # Hueco del comentario y fuentes
    assert report.MARCA_INICIO in md and report.MARCA_FIN in md
    assert report.comentario_pendiente(md) is not None
    assert "wspr.live" in md and "NOAA SWPC" in md
    # Con todas las fuentes respondiendo, solo VOACAP puede faltar (si voacapl no está instalado).
    assert md.count("_Sin datos esta semana._") == (0 if voacap.disponible() else 1)

    html = (out / "informe.html").read_text()
    assert "<table>" in html and 'src="heatmap_hora_banda.png"' in html


def test_informe_sin_red(monkeypatch, tmp_path):
    """Si todas las fuentes fallan, el informe se genera igualmente con «sin datos»."""
    from propagacion import config

    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")

    def sin_red(url, params=None, **kw):
        raise http.FuenteNoDisponible("sin red")

    monkeypatch.setattr(http, "fetch_bytes", sin_red)
    md = report.generar(FECHA_INFORME, tmp_path / "x", usar_rbn=False).read_text()
    assert md.count("_Sin datos esta semana._") >= 5
    assert "amanece a las" in md                         # la línea gris no necesita red


def test_comentario():
    base = f"texto\n{report.MARCA_INICIO}\n{{}}\n{report.MARCA_FIN}\n"
    assert report.comentario_pendiente("sin marcas") is not None
    assert report.comentario_pendiente(base.format("> PENDIENTE: escribir")) is not None
    assert report.comentario_pendiente(base.format("> corto")) is not None
    assert report.comentario_pendiente(base.format(
        "Esta semana EA1ABC trabajó Japón en 17 m al amanecer; la línea gris funcionó.")) is None


def test_cli_comprobar(tmp_path, capsys):
    f = tmp_path / "informe.md"
    f.write_text(f"{report.MARCA_INICIO}\n> PENDIENTE: x\n{report.MARCA_FIN}\n")
    assert main(["comprobar", str(f)]) == 1
    f.write_text(f"{report.MARCA_INICIO}\nUn comentario largo y útil de un socio del radioclub."
                 f"\n{report.MARCA_FIN}\n")
    assert main(["comprobar", str(f)]) == 0


@pytest.mark.parametrize("valor, dec, txt", [(1234.5, 0, "1 234"), (5.33, 2, "5,33"),
                                             (None, 0, "—")])
def test_formato_es(valor, dec, txt):
    assert report.formato_es(valor, dec) == txt
