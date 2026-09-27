"""CLI.

    python -m propagacion                    # informe de esta semana
    python -m propagacion --fecha 2026-09-28 # informe como si hoy fuera esa fecha
    python -m propagacion comprobar informes/2026-W40/informe.md
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from . import report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="propagacion", description="Informe semanal de propagación EA1RKV")
    sub = ap.add_subparsers(dest="cmd")

    gen = sub.add_parser("generar", help="genera el borrador (por defecto)")
    chk = sub.add_parser("comprobar", help="falla si falta el comentario humano")
    chk.add_argument("ficheros", nargs="+", type=Path)
    for p in (ap, gen):
        p.add_argument("--fecha", type=date.fromisoformat, default=None,
                       help="fecha de referencia AAAA-MM-DD (por defecto, hoy)")
        p.add_argument("--salida", type=Path, default=None, help="directorio de salida")
        p.add_argument("--sin-rbn", action="store_true", help="no descargar RBN (~100 MB/semana)")
        p.add_argument("--sin-html", action="store_true", help="solo Markdown")
        p.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")

    if args.cmd == "comprobar":
        errores = 0
        for f in args.ficheros:
            motivo = report.comentario_pendiente(f.read_text(encoding="utf-8"))
            if motivo:
                print(f"✗ {f}: {motivo}")
                errores += 1
            else:
                print(f"✓ {f}: comentario presente")
        return 1 if errores else 0

    path = report.generar(args.fecha or date.today(), args.salida,
                          usar_rbn=not args.sin_rbn, html=not args.sin_html)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
