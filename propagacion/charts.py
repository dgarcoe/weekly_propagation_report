"""Gráficas estáticas (matplotlib) pensadas para leerse bien en el móvil.

Todas usan el mismo sistema visual: fondo claro, tintas neutras, una sola
serie de acento azul y rampas secuenciales de un único tono.
"""
from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _mes_es(x, _pos=None) -> str:
    d = mdates.num2date(x)
    return f"{MESES_CORTOS[d.month - 1]}\n{d.year}"

# --- Tokens de diseño ---------------------------------------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES_1 = "#2a78d6"       # azul
SERIES_2 = "#eb6834"       # naranja
SEQ_BLUE = ["#f0efec", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
# Fiabilidad VOACAP: rampa secuencial azul con cortes fijos (0-10-30-50-70-90-100 %).
REL_EDGES = [0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0001]
REL_COLORS = ["#f0efec", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]

DPI = 160


def _style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "font.size": 12,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK_2,
        "ytick.labelcolor": INK_2,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "legend.frameon": False,
        "legend.labelcolor": INK_2,
    })


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def _nota(fig, texto: str):
    fig.text(0.01, -0.02, texto, color=MUTED, fontsize=9, ha="left", va="top")


# --- Sección 1: SFI ---------------------------------------------------------------

def sfi_tendencia(serie: list[tuple[date, float]], path: Path, semana: tuple[date, date],
                  fuente: str) -> Path:
    """Flujo diario, media móvil de 27 días (una rotación solar) y tendencia lineal."""
    _style()
    fechas = np.array([d for d, _ in serie], dtype="datetime64[D]")
    vals = np.array([v for _, v in serie], dtype=float)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(fechas, vals, color="#9ec5f4", lw=1.2, label="SFI diario")
    if len(vals) >= 27:
        kernel = np.ones(27) / 27
        media = np.convolve(vals, kernel, mode="valid")
        ax.plot(fechas[26:], media, color=SERIES_1, lw=2.4, label="Media 27 días")
    # Tendencia lineal (SFI/mes)
    x = (fechas - fechas[0]).astype(float)
    if len(x) > 30:
        a, b = np.polyfit(x, vals, 1)
        ax.plot(fechas[[0, -1]], a * x[[0, -1]] + b, color=SERIES_2, lw=2, ls=(0, (5, 3)),
                label=f"Tendencia ({a * 30:+.1f} SFI/mes)")
    ax.axvspan(np.datetime64(semana[0]), np.datetime64(semana[1]) + 1, color=GRID, alpha=0.9,
               lw=0, label="Semana analizada")
    ax.set_title("Flujo solar 10,7 cm (SFI)", pad=34)
    ax.set_ylabel("SFI (sfu)")
    ax.grid(axis="y")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(FuncFormatter(_mes_es))
    # Leyenda entre el título y el gráfico para no tapar datos
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4, fontsize=9, handlelength=1.6,
              borderaxespad=0.3, columnspacing=1.2)
    ax.set_ylim(bottom=max(0, math.floor(np.nanmin(vals) / 20) * 20 - 20))
    _nota(fig, f"Fuente: {fuente}")
    return _save(fig, path)


# --- Sección 2: mapa de calor y rutas ------------------------------------------------

def heatmap_edges(maxv: int) -> list[int]:
    """Cortes casi logarítmicos [0, 1, 5, 10, 25, …, máx+1] con como mucho 8 clases."""
    nice = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000]
    inner = [n for n in nice if n <= maxv]
    if len(inner) > 6:                     # quedarse con 1 y los 5 cortes más altos
        inner = [1] + inner[-5:]
    return [0] + inner + [maxv + 1]


def heatmap_hora_banda(matriz: np.ndarray, bandas: list[str], path: Path, titulo: str,
                       nota: str) -> Path:
    """Filas = bandas (de más alta a más baja), columnas = hora UTC."""
    _style()
    fig, ax = plt.subplots(figsize=(8, 0.42 * len(bandas) + 1.6))
    maxv = max(1, int(matriz.max()))
    edges = heatmap_edges(maxv)
    n_bins = len(edges) - 1
    # Gris para «0 spots»; el resto, los pasos más oscuros de la rampa azul.
    cmap = ListedColormap([SEQ_BLUE[0]] + SEQ_BLUE[len(SEQ_BLUE) - (n_bins - 1):])
    norm = BoundaryNorm(edges, cmap.N)
    im = ax.imshow(matriz, aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")
    ax.set_yticks(range(len(bandas)), bandas)
    ax.set_xticks(range(0, 24, 3), [f"{h:02d}" for h in range(0, 24, 3)])
    ax.set_xlabel("Hora UTC")
    ax.set_title(titulo)
    for s in ax.spines.values():
        s.set_visible(False)
    # Separación de 2 px entre celdas
    ax.set_xticks(np.arange(-0.5, 24, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(bandas), 1), minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=2)
    ax.tick_params(which="minor", length=0)
    ax.tick_params(which="major", length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("Spots", color=INK_2)
    cb.outline.set_visible(False)
    cb.set_ticks([(edges[i] + edges[i + 1] - 1) / 2 for i in range(len(edges) - 1)])
    cb.set_ticklabels(["0"] + [f"{edges[i]}–{edges[i + 1] - 1}" if edges[i + 1] - 1 > edges[i]
                               else f"{edges[i]}" for i in range(1, len(edges) - 1)])
    _nota(fig, nota)
    return _save(fig, path)


def rosa_rutas(puntos: list[tuple[float, float]], etiquetas: list[tuple[float, float, str]],
               path: Path, titulo: str, nota: str) -> Path:
    """Proyección azimutal equidistante centrada en Vigo: azimut × distancia.

    ``puntos``: (azimut°, distancia km); ``etiquetas``: (azimut°, distancia km, texto).
    """
    _style()
    fig = plt.figure(figsize=(7, 7.4))
    ax = fig.add_subplot(projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    if puntos:
        az = np.radians([p[0] for p in puntos])
        dist = np.array([p[1] for p in puntos])
        ax.scatter(az, dist, s=22, color=SERIES_1, alpha=0.55, edgecolors=SURFACE, linewidths=0.8,
                   zorder=3)
    for a, d, t in etiquetas:
        ax.annotate(t, (math.radians(a), d), color=INK, fontsize=10, fontweight="bold",
                    ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.25", fc=SURFACE, ec=AXIS, lw=0.8), zorder=4)
    ax.set_rmax(20000)
    ax.set_rticks([5000, 10000, 15000, 20000])
    ax.set_yticklabels(["5000", "10 000", "15 000", "20 000 km"], color=MUTED, fontsize=8)
    ax.set_rlabel_position(100)
    ax.set_xticks(np.radians(range(0, 360, 45)), ["N", "NE", "E", "SE", "S", "SO", "O", "NO"])
    ax.grid(color=GRID)
    ax.spines["polar"].set_color(AXIS)
    ax.set_title(titulo, pad=18)
    _nota(fig, nota)
    return _save(fig, path)


# --- Sección 3: VOACAP y foF2 -------------------------------------------------------

REL_CMAP = ListedColormap(REL_COLORS)
REL_NORM = BoundaryNorm(REL_EDGES, REL_CMAP.N)


def voacap_multiples(tablas: dict[str, np.ndarray], bandas: list[str], path: Path,
                     titulo: str, nota: str) -> Path:
    """Pequeños múltiplos: un panel por destino, filas = bandas, columnas = hora UTC."""
    _style()
    n = len(tablas)
    cols = 2
    rows = math.ceil(n / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(8.4, 2.5 * rows + 0.9), squeeze=False,
                             sharex=True, sharey=True)
    im = None
    for ax, (nombre, m) in zip(axes.flat, tablas.items()):
        im = ax.imshow(m[::-1], aspect="auto", cmap=REL_CMAP, norm=REL_NORM, interpolation="nearest")
        ax.set_title(nombre, fontsize=11)
        ax.set_yticks(range(len(bandas)), bandas[::-1], fontsize=9)
        ax.set_xticks(range(0, 24, 6), [f"{h:02d}" for h in range(0, 24, 6)], fontsize=9)
        ax.set_xticks(np.arange(-0.5, 24, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(bandas), 1), minor=True)
        ax.grid(which="minor", color=SURFACE, linewidth=1.5)
        ax.tick_params(which="both", length=0)
        for s in ax.spines.values():
            s.set_visible(False)
    for ax in list(axes.flat)[n:]:
        ax.set_visible(False)
    for ax in axes[-1]:
        ax.set_xlabel("Hora UTC", fontsize=10)
    fig.suptitle(titulo, x=0.01, ha="left", fontsize=14, fontweight="bold", color=INK)
    # Leyenda arriba, bajo el título: se lee antes que los paneles y no choca con los ejes.
    fig.tight_layout(rect=(0, 0, 1, 0.915))
    cax = fig.add_axes([0.42, 0.93, 0.56, 0.014])
    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    cb.set_ticks([0.05, 0.2, 0.4, 0.6, 0.8, 0.95], labels=["<10", "10–30", "30–50", "50–70", "70–90", ">90"])
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=0, labelsize=9, labelcolor=INK_2)
    fig.text(0.41, 0.937, "Fiabilidad (%)", color=INK_2, fontsize=10, ha="right", va="center")
    _nota(fig, nota)
    return _save(fig, path)


def fof2_diario(horas: list[int], mediana: list[float], p25: list[float], p75: list[float],
                path: Path, nota: str) -> Path:
    _style()
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.fill_between(horas, p25, p75, color="#cde2fb", lw=0, label="Rango intercuartil")
    ax.plot(horas, mediana, color=SERIES_1, lw=2.4, marker="o", ms=5, label="Mediana foF2")
    for f, nombre in ((3.6, "80 m"), (7.1, "40 m")):
        ax.axhline(f, color=INK_2, lw=1, ls=(0, (4, 3)))
        ax.text(23.4, f, f" {nombre}", color=INK_2, va="center", fontsize=10)
    ax.set_xlim(0, 23.3)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xlabel("Hora UTC")
    ax.set_ylabel("MHz")
    ax.set_ylim(0, max(9, math.ceil(max(p75) + 1)))
    ax.grid(axis="y")
    ax.set_title("Frecuencia crítica foF2 · El Arenosillo")
    ax.legend(loc="upper left", fontsize=10)
    _nota(fig, nota)
    return _save(fig, path)
