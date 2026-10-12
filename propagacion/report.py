"""Orquestación: ejecuta cada sección, renderiza la plantilla y escribe la salida."""
from __future__ import annotations

import logging
import re
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import jinja2

from . import config
from .periodo import Periodo, fecha_corta, fecha_larga
from .sections import agenda, ionosfera, prevision, realidad, sol

log = logging.getLogger(__name__)

MARCA_INICIO = "<!-- COMENTARIO -->"
MARCA_FIN = "<!-- /COMENTARIO -->"
PENDIENTE = "PENDIENTE:"


def _seguro(nombre: str, fn, *args, **kw) -> dict:
    """Ejecuta una sección; si revienta, el informe sigue con ella marcada «sin datos»."""
    try:
        return fn(*args, **kw)
    except Exception as e:  # noqa: BLE001 - queremos el informe pase lo que pase
        log.error("Sección %s falló: %s\n%s", nombre, e, traceback.format_exc())
        return {"ok": False, "motivo": str(e), "fuentes": [], "avisos": []}


def muf_de_respaldo(p: Periodo, sol: dict) -> dict[int, float] | None:
    """MUF(3000) modelada con VOACAP para la semana analizada, si las ionosondas fallan.

    Usa el SSN efectivo del SFI medio que midió NOAA esa semana; es el promedio que
    predice el modelo, no una medida, y el informe lo dice así.
    """
    from . import geo, solar, voacap

    sfi = (sol.get("sfi") or {}).get("media")
    if not sfi or not voacap.disponible():
        return None
    lat, lon = geo.locator_to_latlon(config.STATION_LOCATOR)
    medio = p.inicio + timedelta(days=3)
    try:
        return voacap.muf_modelada(lat, lon, medio.year, medio.month, solar.ssn_from_sfi(sfi))
    except voacap.VoacapNoDisponible as e:
        log.warning("MUF de respaldo: %s", e)
        return None


def _env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(config.TEMPLATES_DIR),
        undefined=jinja2.ChainableUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["es"] = formato_es
    env.filters["fecha_corta"] = fecha_corta
    return env


def formato_es(valor, decimales: int = 0) -> str:
    """Número con coma decimal y separador de miles español (espacio fino)."""
    if valor is None:
        return "—"
    s = f"{valor:,.{decimales}f}"
    return s.replace(",", " ").replace(".", ",")


def generar(hoy: date, salida: Path | None = None, usar_rbn: bool = True,
            html: bool = True) -> Path:
    p = Periodo.para(hoy)
    outdir = salida or (config.OUTPUT_DIR / p.etiqueta)
    outdir.mkdir(parents=True, exist_ok=True)
    log.info("Generando informe %s en %s", p.etiqueta, outdir)

    s1 = _seguro("sol", sol.construir, p, outdir)
    iono = _seguro("ionosondas", ionosfera.medir, p)
    muf3000, muf_origen = (iono.get("vigo") or {}).get("MUF(D)"), "medida"
    if not muf3000:
        muf3000, muf_origen = muf_de_respaldo(p, s1), "modelada"
    s2 = _seguro("realidad", realidad.construir, p, outdir, usar_rbn=usar_rbn,
                 muf3000=muf3000, muf_origen=muf_origen)
    si = _seguro("ionosfera", ionosfera.construir, p, outdir, iono, s1, s2.get("_contactos"))
    s3 = _seguro("prevision", prevision.construir, p, outdir, s1, iono)
    s4 = _seguro("agenda", agenda.construir, p)

    fuentes: list[str] = []
    for s in (s1, s2, si, s3, s4):
        for f in s.get("fuentes", []):
            if f not in fuentes:
                fuentes.append(f)

    ctx = {
        "p": p,
        "titulo_semana": f"{fecha_larga(p.inicio)} – {fecha_larga(p.fin)}",
        "sig_semana": f"{fecha_corta(p.sig_inicio)} – {fecha_corta(p.sig_fin)}",
        "cfg": config,
        "sol": s1,
        "realidad": s2,
        "ionosfera": si,
        "prevision": s3,
        "agenda": s4,
        "fuentes": fuentes,
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "marca_inicio": MARCA_INICIO,
        "marca_fin": MARCA_FIN,
        "pendiente": PENDIENTE,
    }
    md = _env().get_template("informe.md.j2").render(**ctx)
    md = re.sub(r"\n{3,}", "\n\n", md)
    md_path = outdir / "informe.md"
    md_path.write_text(md, encoding="utf-8")
    if html:
        (outdir / "informe.html").write_text(a_html(md, p.etiqueta), encoding="utf-8")
    return md_path


def a_html(md: str, titulo: str) -> str:
    import markdown

    cuerpo = markdown.markdown(md, extensions=["tables", "sane_lists"])
    css = """
    body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;max-width:860px;margin:0 auto;
         padding:16px;line-height:1.55;color:#0b0b0b;background:#fcfcfb}
    img{max-width:100%;height:auto}
    table{border-collapse:collapse;display:block;overflow-x:auto;font-variant-numeric:tabular-nums}
    th,td{border-bottom:1px solid #e1e0d9;padding:4px 8px;text-align:left;white-space:nowrap}
    blockquote{border-left:3px solid #2a78d6;margin:0;padding:0 12px;color:#52514e}
    """
    return (f"<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>Propagación {titulo}</title><style>{css}</style></head>"
            f"<body>{cuerpo}</body></html>")


def comentario_pendiente(md: str) -> str | None:
    """Devuelve el motivo si el hueco del comentario humano no está relleno."""
    if MARCA_INICIO not in md or MARCA_FIN not in md:
        return "faltan las marcas <!-- COMENTARIO --> / <!-- /COMENTARIO -->"
    bloque = md.split(MARCA_INICIO, 1)[1].split(MARCA_FIN, 1)[0]
    if PENDIENTE in bloque:
        return "el comentario del socio sigue pendiente"
    if len(re.sub(r"[\s>*_]", "", bloque)) < 40:
        return "el comentario del socio está vacío o es demasiado corto"
    return None
