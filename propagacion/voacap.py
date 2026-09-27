"""Predicción punto a punto con VOACAP (voacapl, el port para Linux).

Genera la tarjeta de entrada (formato de columnas fijas del VOACAP original),
ejecuta ``voacapl <itshfbc> <entrada> <salida>`` y extrae la fila REL
(fiabilidad del circuito) por hora UTC y frecuencia.

Si ``voacapl`` no está instalado se lanza ``VoacapNoDisponible`` y la sección
queda marcada como «sin datos esta semana».
"""
from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from .config import ROOT
from .geo import bearing_deg

ANTENAS_DIR = ROOT / "voacap_antenas"


class VoacapNoDisponible(RuntimeError):
    pass


@dataclass(frozen=True)
class Parametros:
    potencia_kw: float = 0.1          # 100 W
    ruido_dbw: int = 145              # −145 dBW a 3 MHz: zona residencial
    angulo_min: float = 0.1           # grados
    rel_requerida: int = 90
    snr_requerida: float = 27.0       # dB·Hz ≈ CW legible (~0 dB en 500 Hz)
    antena_tx: str = "ea1rkv/dipolo.voa"   # dipolo λ/2 a λ/2 de altura
    antena_rx: str = "ea1rkv/dipolo.voa"


def _lat(v: float) -> str:
    return f"{abs(v):5.2f}{'N' if v >= 0 else 'S'}"


def _lon(v: float) -> str:
    return f"{abs(v):6.2f}{'E' if v >= 0 else 'W'}"


def build_deck(tx: tuple[float, float, str], rx: tuple[float, float, str],
               year: int, month: int, ssn: float, freqs_mhz: list[float],
               p: Parametros = Parametros()) -> str:
    if not 1 <= len(freqs_mhz) <= 11:
        raise ValueError("VOACAP admite entre 1 y 11 frecuencias")
    az_tx = bearing_deg(tx[0], tx[1], rx[0], rx[1])
    az_rx = bearing_deg(rx[0], rx[1], tx[0], tx[1])
    freqs = "".join(f"{f:5.2f}" for f in freqs_mhz) + " 0.00" * (11 - len(freqs_mhz))
    lines = [
        "LINEMAX      55       number of lines-per-page",
        "COEFFS    CCIR",
        f"TIME      {1:5d}{24:5d}{1:5d}{1:5d}",
        f"MONTH     {year:5d}{month:5.2f}",
        f"SUNSPOT   {max(0, round(ssn)):4d}.",
        f"LABEL     {tx[2][:20]:<20}{rx[2][:20]:<20}",
        f"CIRCUIT   {_lat(tx[0])}   {_lon(tx[1])}    {_lat(rx[0])}   {_lon(rx[1])}  S     0",
        f"SYSTEM    {p.potencia_kw:5.2f}{p.ruido_dbw:4d}.{p.angulo_min:5.2f}{p.rel_requerida:4d}."
        f"{p.snr_requerida:5.1f} 3.00 0.10",
        "FPROB      1.00 1.00 1.00 0.00",
        # Cada antena apunta su lóbulo principal hacia el otro extremo del circuito.
        f"ANTENNA       1    1    2   30     0.000[{p.antena_tx:<21}]{az_tx:5.1f}{p.potencia_kw:10.4f}",
        f"ANTENNA       2    2    2   30     0.000[{p.antena_rx:<21}]{az_rx:5.1f}    0.0000",
        f"FREQUENCY {freqs}",
        "METHOD       30    0",
        "EXECUTE",
        "QUIT",
    ]
    return "\n".join(lines) + "\n"


def parse_rel(output: str, n_freqs: int) -> dict[int, list[float]]:
    """{hora UTC (0-23): [REL por frecuencia]} a partir de la salida METHOD 30.

    Cada bloque empieza con una línea ``<hora> <MUF> f1 … f11 FREQ``; la
    columna tras la hora es la MUF, así que la REL de f_i es el token i+1.
    VOACAP numera las horas 1-24; la hora 24 es la 0 UTC.
    """
    rel: dict[int, list[float]] = {}
    hora: int | None = None
    for line in output.splitlines():
        toks = line.split()
        if not toks:
            continue
        if toks[-1] == "FREQ":
            try:
                hora = int(float(toks[0])) % 24
            except ValueError:
                hora = None
        elif toks[-1] == "REL" and hora is not None:
            vals = toks[1:1 + n_freqs]
            rel[hora] = [float(v) if v not in ("-", "--") else 0.0 for v in vals]
            hora = None
    return rel


def itshfbc_dir() -> Path:
    return Path(os.environ.get("ITSHFBC", Path.home() / "itshfbc"))


def disponible() -> bool:
    return shutil.which("voacapl") is not None and (itshfbc_dir() / "run").is_dir()


def _instalar_antenas(base: Path) -> None:
    """Copia nuestras antenas a ``itshfbc/antennas/ea1rkv`` (VOACAP las busca ahí)."""
    dest = base / "antennas" / "ea1rkv"
    dest.mkdir(parents=True, exist_ok=True)
    for f in ANTENAS_DIR.glob("*.voa"):
        shutil.copyfile(f, dest / f.name)


def run(deck: str, n_freqs: int, timeout: int = 120) -> dict[int, list[float]]:
    if not disponible():
        raise VoacapNoDisponible("voacapl no está instalado (o falta ~/itshfbc)")
    base = itshfbc_dir()
    _instalar_antenas(base)
    name = f"eakv{uuid.uuid4().hex[:6]}"
    inp, out = base / "run" / f"{name}.dat", base / "run" / f"{name}.out"
    inp.write_text(deck)
    try:
        subprocess.run(["voacapl", str(base), inp.name, out.name],
                       check=True, capture_output=True, timeout=timeout)
        text = out.read_text(errors="replace")
    except (subprocess.SubprocessError, OSError) as e:
        raise VoacapNoDisponible(f"voacapl falló: {e}") from e
    finally:
        for f in (inp, out):
            f.unlink(missing_ok=True)
    rel = parse_rel(text, n_freqs)
    if not rel:
        raise VoacapNoDisponible("voacapl no devolvió filas REL")
    return rel
