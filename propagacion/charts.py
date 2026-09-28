"""Gráficas estáticas (matplotlib) pensadas para leerse bien en el móvil.

Todas usan el mismo sistema visual: fondo claro, tintas neutras, una sola
serie de acento azul y rampas secuenciales de un único tono.
"""
from __future__ import annotations

import math
from datetime import date, datetime
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
SERIES_7 = "#4a3aa7"       # violeta (previsiones)
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
                  fuente: str, prevision: list[tuple[date, float, float, float]] | None = None) -> Path:
    """Flujo diario, media móvil de 27 días (una rotación solar) y tendencia lineal.

    ``prevision``: (mes, SFI previsto, mínimo, máximo) de NOAA para los próximos meses,
    dibujada a la derecha como línea discontinua con su rango sombreado.
    """
    _style()
    fechas = np.array([d for d, _ in serie], dtype="datetime64[D]")
    vals = np.array([v for _, v in serie], dtype=float)
    fig, ax = plt.subplots(figsize=(8.4 if prevision else 8, 4.2))
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
    minimos = [np.nanmin(vals)]
    if prevision:
        fp = np.array([d for d, *_ in prevision], dtype="datetime64[D]")
        ax.fill_between(fp, [lo for *_, lo, _ in prevision], [hi for *_, hi in prevision],
                        color="#dcd8f3", lw=0)
        ax.plot(fp, [v for _, v, _, _ in prevision], color=SERIES_7, lw=2, marker="o", ms=4,
                label="Previsión NOAA (y su rango)")
        ax.axvline(fechas[-1], color=AXIS, lw=1)
        ax.text(fechas[-1], ax.get_ylim()[1], " previsión →", color=INK_2, fontsize=9, va="top")
        minimos.append(min(lo for *_, lo, _ in prevision))
    ax.set_title("Flujo solar 10,7 cm (SFI)", pad=34)
    ax.set_ylabel("SFI (sfu)")
    ax.grid(axis="y")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(FuncFormatter(_mes_es))
    # Leyenda entre el título y el gráfico para no tapar datos
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4, fontsize=9, handlelength=1.6,
              borderaxespad=0.3, columnspacing=1.2)
    ax.set_ylim(bottom=max(0, math.floor(min(minimos) / 20) * 20 - 20))
    _nota(fig, f"Fuente: {fuente}" + (" · previsión: NOAA SWPC (ciclo solar, media mensual)"
                                       if prevision else ""))
    return _save(fig, path)


# --- Sección 2: mapa de calor y rutas ------------------------------------------------

def heatmap_edges(maxv: int) -> list[int]:
    """Cortes casi logarítmicos [0, 1, 5, 10, 25, …, máx+1] con como mucho 8 clases."""
    nice = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000]
    inner = [n for n in nice if n <= maxv]
    if len(inner) > 6:                     # quedarse con 1 y los 5 cortes más altos
        inner = [1] + inner[-5:]
    return [0] + inner + [maxv + 1]


def techo_muf(bandas: list[str], frecuencias: dict[str, float], muf: dict[int, float]
              ) -> list[tuple[int, float]]:
    """(hora, y) de la frontera entre bandas por debajo y por encima de la MUF.

    Las filas van de la banda más alta (y = 0) a la más baja; y es el borde superior
    de la banda más alta que la MUF deja pasar.
    """
    out = []
    for h in range(24):
        if h not in muf:
            continue
        abiertas = [i for i, b in enumerate(bandas) if frecuencias[b] <= muf[h]]
        out.append((h, (min(abiertas) if abiertas else len(bandas)) - 0.5))
    return out


def heatmap_hora_banda(matriz: np.ndarray, bandas: list[str], path: Path, titulo: str,
                       nota: str, techo: list[tuple[int, float]] | None = None) -> Path:
    """Filas = bandas (de más alta a más baja), columnas = hora UTC.

    ``techo``: (hora, y) de la MUF medida, dibujada como una línea escalonada.
    """
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
    if techo:
        xs, ys = [], []
        for h, y in techo:
            xs += [h - 0.5, h + 0.5]
            ys += [y, y]
        ax.plot(xs, ys, color=SERIES_2, lw=2.4, solid_joinstyle="miter", zorder=5)
        h_lab, y_lab = min(techo, key=lambda t: t[1])
        ax.annotate("MUF(3000) medida", (h_lab, y_lab), xytext=(0, 6), textcoords="offset points",
                    color=INK, fontsize=9, fontweight="bold", ha="center", va="bottom",
                    bbox=dict(boxstyle="round,pad=0.2", fc=SURFACE, ec=SERIES_2, lw=1), zorder=6)
        ax.set_ylim(len(bandas) - 0.5, -1.4)
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
                path: Path, nota: str, estaciones: dict[str, dict[int, float]] | None = None,
                fmin: dict[int, float] | None = None, titulo: str = "Frecuencia crítica foF2 · El Arenosillo"
                ) -> Path:
    """Perfil diario de foF2 (mediana e intercuartil) con referencias de 80/40 m.

    ``estaciones``: perfiles de cada ionosonda (líneas finas grises, etiquetadas);
    ``fmin``: suelo de absorción (línea discontinua).
    """
    _style()
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.fill_between(horas, p25, p75, color="#cde2fb", lw=0, label="Rango intercuartil")
    etiquetas = []
    for nombre, perf in (estaciones or {}).items():
        hs = sorted(perf)
        ax.plot(hs, [perf[h] for h in hs], color=MUTED, lw=1, alpha=0.9)
        if hs:
            etiquetas.append([perf[hs[-1]], hs[-1], nombre])
    # Etiquetas directas al final de cada línea, separadas para que no se pisen
    etiquetas.sort()
    for i in range(1, len(etiquetas)):
        etiquetas[i][0] = max(etiquetas[i][0], etiquetas[i - 1][0] + 0.45)
    for y, x, nombre in etiquetas:
        ax.text(x + 0.25, y, nombre, color=INK_2, fontsize=8, va="center")
    ax.plot(horas, mediana, color=SERIES_1, lw=2.4, marker="o", ms=5,
            label="Mediana foF2" + (" (estimada en Vigo)" if estaciones else ""))
    if fmin:
        hs = sorted(fmin)
        ax.plot(hs, [fmin[h] for h in hs], color=SERIES_2, lw=2, ls=(0, (5, 3)),
                label="fmin (absorción)")
    for f, nombre in ((3.6, "80 m"), (7.1, "40 m")):
        ax.axhline(f, color=INK_2, lw=1, ls=(0, (4, 3)))
        # 80 m por debajo de su línea: de noche la foF2 suele rondar esa zona
        ax.text(0.15, f + (0.08 if f > 5 else -0.08), nombre, color=INK_2,
                va="bottom" if f > 5 else "top", fontsize=10)
    ax.set_xlim(0, 23.3)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xlabel("Hora UTC")
    ax.set_ylabel("MHz")
    ax.set_ylim(0, max(9, math.ceil(max(p75) + 1)))
    ax.grid(axis="y")
    ax.set_title(titulo)
    ax.legend(loc="upper left", fontsize=10)
    ax.set_xlim(0, 23.3 if not etiquetas else 25.6)
    ax.set_xticks(range(0, 24, 3))
    _nota(fig, nota)
    return _save(fig, path)


STATUS_GOOD, STATUS_WARN, STATUS_CRIT = "#0ca30c", "#fab219", "#d03b3b"
DIV_NEG, DIV_POS = "#e34948", "#2a78d6"


def anomalia_fof2(desv: list[tuple], kp3h: list[tuple], path: Path, rango: tuple, nota: str) -> Path:
    """Dos paneles con el mismo eje de tiempo (nunca doble eje Y):
    arriba, % de foF2 respecto a lo normal; abajo, Kp trihorario con semáforo."""
    _style()
    fig, (ax, ak) = plt.subplots(2, 1, figsize=(8, 5.4), sharex=True,
                                 gridspec_kw={"height_ratios": [2.2, 1], "hspace": 0.12})
    t = np.array([d for d, _ in desv], dtype="datetime64[m]")
    v = np.array([x for _, x in desv], dtype=float)
    if len(t):
        ax.fill_between(t, 0, v, where=v >= 0, color=DIV_POS, alpha=0.35, lw=0, step="mid")
        ax.fill_between(t, 0, v, where=v < 0, color=DIV_NEG, alpha=0.35, lw=0, step="mid")
        ax.plot(t, v, color=INK_2, lw=1, drawstyle="steps-mid")
    ax.axhline(0, color=AXIS, lw=1)
    ax.axhline(-20, color=INK_2, lw=1, ls=(0, (4, 3)))
    ax.text(np.datetime64(rango[0]), -20, " −20 %: tormenta ionosférica negativa", color=INK_2,
            fontsize=9, va="bottom")
    lim = max(30, float(np.nanmax(np.abs(v))) * 1.1 if len(v) else 30)
    ax.set_ylim(-lim, lim)
    ax.set_ylabel("foF2 vs normal (%)")
    ax.grid(axis="y")
    ax.set_title("¿Ionosfera mejor o peor de lo normal?")

    if kp3h:
        tk = np.array([d for d, _ in kp3h], dtype="datetime64[m]") + np.timedelta64(90, "m")
        kv = np.array([k for _, k in kp3h], dtype=float)
        col = [STATUS_CRIT if k >= 5 else STATUS_WARN if k >= 4 else STATUS_GOOD for k in kv]
        ak.bar(tk, kv, width=np.timedelta64(170, "m"), color=col, edgecolor=SURFACE, lw=0.5)
    ak.axhline(5, color=STATUS_CRIT, lw=1, ls=(0, (4, 3)))
    ak.text(np.datetime64(rango[1]), 5, "tormenta (Kp 5) ", color=INK_2, fontsize=8, ha="right",
            va="bottom")
    ak.set_ylim(0, 9)
    ak.set_yticks([0, 3, 5, 9])
    ak.set_ylabel("Kp")
    ak.grid(axis="y")
    ak.set_xlim(np.datetime64(rango[0]), np.datetime64(rango[1]))
    ak.xaxis.set_major_locator(mdates.DayLocator())
    ak.xaxis.set_major_formatter(FuncFormatter(_dia_es))
    _nota(fig, nota)
    return _save(fig, path)


DIAS_CORTOS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def _dia_es(x, _pos=None) -> str:
    d = mdates.num2date(x)
    return f"{DIAS_CORTOS[d.weekday()]} {d.day}"


# --- Sección 1: la semana del Sol y la previsión -------------------------------------

CLASES_RX = (("A", 1e-8), ("B", 1e-7), ("C", 1e-6), ("M", 1e-5), ("X", 1e-4))


def _kp_barras(ak, kp3h: list[tuple], ancho_h: float = 3.0, desfase_h: float = 1.5):
    if kp3h:
        tk = np.array([d for d, _ in kp3h], dtype="datetime64[m]") + np.timedelta64(int(desfase_h * 60), "m")
        kv = np.array([k for _, k in kp3h], dtype=float)
        col = [STATUS_CRIT if k >= 5 else STATUS_WARN if k >= 4 else STATUS_GOOD for k in kv]
        ak.bar(tk, kv, width=np.timedelta64(int(ancho_h * 60 * 0.95), "m"), color=col,
               edgecolor=SURFACE, lw=0.5)
    ak.axhline(5, color=STATUS_CRIT, lw=1, ls=(0, (4, 3)))
    ak.set_ylim(0, 9)
    ak.set_yticks([0, 3, 5, 9])
    ak.set_ylabel("Kp")
    ak.grid(axis="y")


def semana_solar(xrays: list[tuple], sfi: list[tuple], kp3h: list[tuple],
                 fulguraciones: list[tuple], rango: tuple, path: Path, nota: str) -> Path:
    """Tres paneles con el mismo eje de días: rayos X (GOES), SFI diario y Kp."""
    _style()
    fig, (ax, asf, ak) = plt.subplots(3, 1, figsize=(8, 7.2), sharex=True,
                                      gridspec_kw={"height_ratios": [2.2, 1.2, 1], "hspace": 0.18})
    # Rayos X, escala logarítmica con las clases de fulguración
    if xrays:
        t = np.array([d for d, _ in xrays], dtype="datetime64[m]")
        ax.plot(t, [f for _, f in xrays], color=SERIES_1, lw=1)
    ax.set_yscale("log")
    ax.set_ylim(1e-8, 1e-3)
    for clase, nivel in CLASES_RX:
        ax.axhline(nivel, color=GRID, lw=0.8)
        ax.text(1.005, math.sqrt(nivel * nivel * 10), clase, transform=ax.get_yaxis_transform(),
                color=INK_2, fontsize=10, fontweight="bold", va="center")
    ax.axhspan(1e-5, 1e-3, color="#fde2e1", lw=0, zorder=0)
    ax.text(np.datetime64(rango[0]), 8e-4, " M y X: apagones de radio en HF (lado diurno)",
            color=INK_2, fontsize=8.5, va="top")
    for cuando, clase, flujo in fulguraciones:
        ax.annotate(clase, (np.datetime64(cuando, "m"), flujo), xytext=(0, 5),
                    textcoords="offset points", ha="center", va="bottom", fontsize=9,
                    fontweight="bold", color=INK,
                    bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec="none", alpha=0.8))
    ax.set_ylabel("Rayos X (W/m²)")
    ax.set_title("La semana del Sol")
    ax.set_yticks([1e-8, 1e-6, 1e-4])
    ax.grid(False)

    # SFI diario
    if sfi:
        fd = np.array([d for d, _ in sfi], dtype="datetime64[D]") + np.timedelta64(12, "h")
        vs = [v for _, v in sfi]
        asf.bar(fd, vs, width=np.timedelta64(19, "h"), color="#9ec5f4", edgecolor=SURFACE)
        for x, v in zip(fd, vs):
            asf.text(x, v, f"{v:.0f}", ha="center", va="bottom", fontsize=9, color=INK_2)
        asf.set_ylim(min(vs) * 0.85, max(vs) * 1.12)
    asf.set_ylabel("SFI")
    asf.grid(axis="y")

    _kp_barras(ak, kp3h)
    ak.set_xlim(np.datetime64(rango[0]), np.datetime64(rango[1]))
    ak.xaxis.set_major_locator(mdates.DayLocator())
    ak.xaxis.set_major_formatter(FuncFormatter(_dia_es))
    _nota(fig, nota)
    return _save(fig, path)


def prevision_solar(dias: list[tuple], semana: tuple, path: Path, nota: str) -> Path:
    """Previsión a 27 días de NOAA: SFI arriba, Kp máximo diario abajo (dos paneles)."""
    _style()
    fig, (asf, ak) = plt.subplots(2, 1, figsize=(8, 4.8), sharex=True,
                                  gridspec_kw={"height_ratios": [1.6, 1], "hspace": 0.12})
    fd = np.array([d for d, _, _ in dias], dtype="datetime64[D]") + np.timedelta64(12, "h")
    sfi = [s for _, s, _ in dias]
    for a in (asf, ak):
        a.axvspan(np.datetime64(semana[0]), np.datetime64(semana[1]) + 1, color=GRID, alpha=0.55,
                  lw=0, zorder=0)
    asf.plot(fd, sfi, color=SERIES_1, lw=2.2, marker="o", ms=4)
    asf.text(np.datetime64(semana[0]) + np.timedelta64(3, "h"), max(sfi), " esta semana",
             color=INK_2, fontsize=9, va="top")
    asf.set_ylabel("SFI previsto")
    asf.set_ylim(min(sfi) - 8, max(sfi) + 8)
    asf.grid(axis="y")
    asf.set_title("Lo que espera NOAA: próximos 27 días")
    kp = [(datetime(d.year, d.month, d.day), k) for d, _, k in dias]
    _kp_barras(ak, kp, ancho_h=24, desfase_h=12)
    ak.set_ylabel("Kp máx.")
    ak.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    ak.xaxis.set_major_formatter(FuncFormatter(_dia_es))
    ak.set_xlim(fd[0] - np.timedelta64(12, "h"), fd[-1] + np.timedelta64(12, "h"))
    _nota(fig, nota)
    return _save(fig, path)

