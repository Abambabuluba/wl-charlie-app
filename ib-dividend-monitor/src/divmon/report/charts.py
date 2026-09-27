"""Gráficos del informe (PNG en base64 para que el HTML sea un único archivo)."""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

SERIES = ["#2a78d6", "#eb6834"]
TEXT = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"
LIMIT = "#8a8984"

plt.rcParams.update({
    "font.size": 9,
    "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED,
    "axes.titlecolor": TEXT,
    "axes.titlesize": 10,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
})


def _eur(x: float, _=None) -> str:
    return f"{x:,.0f} €".replace(",", ".")


def _pct(x: float, _=None) -> str:
    return f"{x * 100:.0f} %"


DPI = 150
CSS_DPI = 96   # se muestra a tamaño real en pantalla y la imagen conserva nitidez


@dataclass
class Chart:
    src: str
    width: int   # ancho de visualización en píxeles CSS


def _encode(fig) -> Chart:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    png = buf.getvalue()
    return Chart("data:image/png;base64," + base64.b64encode(png).decode(), round(_png_width(png) * CSS_DPI / DPI))


def _png_width(png: bytes) -> int:
    return int.from_bytes(png[16:20], "big")


def weights_bar(title: str, items: list[tuple[str, float]], limit: float | None = None, max_items: int = 15) -> Chart:
    """Barras horizontales de pesos, con la línea del límite de concentración."""
    items = items[:max_items]
    labels = [n for n, _ in items][::-1]
    values = [w for _, w in items][::-1]
    fig, ax = plt.subplots(figsize=(4.4, 0.26 * len(items) + 0.8))
    ax.barh(labels, values, color=SERIES[0], height=0.62)
    for y, v in enumerate(values):
        ax.text(v, y, f" {v * 100:.1f} %".replace(".", ","), va="center", fontsize=8, color=MUTED)
    if limit is not None:
        ax.axvline(limit, color=LIMIT, linestyle=(0, (3, 3)), linewidth=1)
        title += f"  ·  límite {limit * 100:.0f} %".replace(".", ",")
    ax.xaxis.set_major_formatter(FuncFormatter(_pct))
    ax.set_xlim(0, max([*values, limit or 0]) * 1.22)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_title(title)
    return _encode(fig)


def monthly_bar(title: str, months: list[str], values: list[float]) -> Chart:
    fig, ax = plt.subplots(figsize=(9.2, 2.8))
    labels = [_short_month(m) for m in months]
    ax.bar(labels, values, color=SERIES[0], width=0.62)
    ax.yaxis.set_major_formatter(FuncFormatter(_eur))
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_title(title)
    ax.tick_params(axis="x", labelsize=8)
    return _encode(fig)


def lines(title: str, x: list, series: list[tuple[str, list[float]]], money: bool = True) -> Chart:
    """Hasta dos series en la misma unidad, con leyenda y etiqueta directa al final."""
    fig, ax = plt.subplots(figsize=(9.2, 3.0))
    for i, (label, values) in enumerate(series):
        xs = x[: len(values)]
        ax.plot(xs, values, color=SERIES[i % 2], linewidth=2, label=label)
        if values:
            ax.annotate(_eur(values[-1]) if money else f"{values[-1]:.0f}", (xs[-1], values[-1]),
                        textcoords="offset points", xytext=(4, 0), fontsize=8, color=MUTED, va="center")
    if money:
        ax.yaxis.set_major_formatter(FuncFormatter(_eur))
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_title(title)
    if len(series) > 1:
        ax.legend(frameon=False, fontsize=8, loc="upper right")
    if x and isinstance(x[0], date):
        fig.autofmt_xdate()
    return _encode(fig)


MONTHS_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _short_month(key: str) -> str:
    year, month = key.split("-")
    return f"{MONTHS_ES[int(month) - 1]} {year[2:]}"
