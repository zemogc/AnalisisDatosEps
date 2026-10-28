"""Gráficos estáticos (PNG) del reporte."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from eps_analytics import formatting as fmt  # noqa: E402
from eps_analytics.analysis import GRUPOS_ETARIOS, ResultadoAnalisis  # noqa: E402

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
AZUL = "#2a78d6"
NARANJA = "#eb6834"
SECUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
COLOR_SEXO = {"F": AZUL, "M": NARANJA}
ETIQUETA_SEXO = {"F": "Mujeres", "M": "Hombres"}

_COP_EJE = FuncFormatter(lambda v, _: fmt.cop_compacto(v))


def _estilo() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "text.color": TEXT,
            "axes.labelcolor": TEXT_2,
            "axes.edgecolor": GRID,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.titlepad": 14,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "xtick.color": TEXT_2,
            "ytick.color": TEXT_2,
            "legend.frameon": False,
        }
    )


def _guardar(fig: plt.Figure, ruta: Path) -> Path:
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return ruta


def grafico_costo_eps(res: ResultadoAnalisis, ruta: Path) -> Path:
    datos = res.por_eps.sort_values("Costo_Total")
    fig, ax = plt.subplots(figsize=(10, 5.2))
    barras = ax.barh(datos.index, datos["Costo_Total"], color=AZUL, height=0.62)
    ax.bar_label(
        barras,
        labels=[
            f"{fmt.cop_compacto(v)}  ·  {fmt.porcentaje(p)}"
            for v, p in zip(datos["Costo_Total"], datos["Participacion"], strict=True)
        ],
        padding=6,
        color=TEXT_2,
        fontsize=9,
    )
    ax.set_title("Costo total de atención por EPS")
    ax.xaxis.set_major_formatter(_COP_EJE)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, datos["Costo_Total"].max() * 1.28)
    ax.tick_params(axis="y", length=0)
    return _guardar(fig, ruta)


def grafico_costo_diagnostico(res: ResultadoAnalisis, ruta: Path) -> Path:
    datos = res.por_diagnostico.reset_index().iloc[::-1]
    etiquetas = [f"{d} ({c})" for d, c in zip(datos["Diagnostico"], datos["Codigo_CIE10"], strict=True)]
    fig, ax = plt.subplots(figsize=(10, 6))
    barras = ax.barh(etiquetas, datos["Costo_Total"], color=AZUL, height=0.62)
    ax.bar_label(
        barras,
        labels=[
            f"{fmt.porcentaje(p)} · acum. {fmt.porcentaje(a, 0)}"
            for p, a in zip(datos["Participacion"], datos["Participacion_Acumulada"], strict=True)
        ],
        padding=6,
        color=TEXT_2,
        fontsize=9,
    )
    ax.set_title("Costo total por diagnóstico (CIE-10) — análisis de Pareto")
    ax.xaxis.set_major_formatter(_COP_EJE)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, datos["Costo_Total"].max() * 1.32)
    ax.tick_params(axis="y", length=0)
    return _guardar(fig, ruta)


def grafico_tendencia(res: ResultadoAnalisis, ruta: Path) -> Path:
    m = res.mensual
    # Dos paneles con eje X compartido en lugar de un gráfico de doble eje
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11, 6.4), sharex=True, gridspec_kw={"height_ratios": [1, 1.3]}
    )
    ax1.plot(m.index, m["Consultas"], color=AZUL, linewidth=2, marker="o", markersize=4)
    ax1.set_title("Consultas por mes")
    ax1.set_ylim(0, m["Consultas"].max() * 1.15)
    ax1.grid(axis="x", visible=False)

    ax2.plot(
        m.index,
        m["Costo_Total"],
        color=AZUL,
        linewidth=1.4,
        alpha=0.45,
        marker="o",
        markersize=3,
        label="Costo mensual",
    )
    ax2.plot(m.index, m["Media_Movil_3M"], color=AZUL, linewidth=2.4, label="Media móvil 3 meses")
    ax2.set_title("Costo total por mes")
    ax2.yaxis.set_major_formatter(_COP_EJE)
    ax2.set_ylim(0, m["Costo_Total"].max() * 1.15)
    ax2.grid(axis="x", visible=False)
    ax2.legend(loc="lower right")
    fig.autofmt_xdate(rotation=0, ha="center")
    return _guardar(fig, ruta)


def grafico_grupo_etario(res: ResultadoAnalisis, ruta: Path) -> Path:
    tabla = res.por_grupo_etario["Costo_Por_Paciente"].unstack("Sexo").reindex(GRUPOS_ETARIOS)
    x = np.arange(len(tabla))
    ancho = 0.38
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, sexo in enumerate(["F", "M"]):
        if sexo in tabla:
            ax.bar(
                x + (i - 0.5) * (ancho + 0.02),
                tabla[sexo],
                width=ancho,
                color=COLOR_SEXO[sexo],
                label=ETIQUETA_SEXO[sexo],
            )
    ax.set_xticks(x, [f"{g} años" for g in tabla.index])
    ax.set_title("Costo promedio por paciente según grupo etario y sexo")
    ax.yaxis.set_major_formatter(_COP_EJE)
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="x", length=0)
    ax.legend(loc="upper left")
    return _guardar(fig, ruta)


def grafico_heatmap(res: ResultadoAnalisis, ruta: Path) -> Path:
    mat = res.matriz_eps_dx.loc[res.por_diagnostico.index.get_level_values("Diagnostico"), res.por_eps.index]
    cmap = LinearSegmentedColormap.from_list("azul", SECUENCIAL)
    fig, ax = plt.subplots(figsize=(11, 6.4))
    log_mat = np.log10(mat.to_numpy(dtype=float))
    im = ax.imshow(log_mat, cmap=cmap, aspect="auto")
    ax.set_xticks(range(mat.shape[1]), mat.columns, rotation=30, ha="right")
    ax.set_yticks(range(mat.shape[0]), mat.index)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    for (i, j), v in np.ndenumerate(log_mat):
        if not np.isnan(v):
            ax.text(
                j,
                i,
                fmt.cop_compacto(10**v).replace("$ ", ""),
                ha="center",
                va="center",
                fontsize=7.5,
                color="white" if im.norm(v) > 0.5 else TEXT,
            )
    ax.set_title("Costo promedio por consulta: diagnóstico × EPS (escala logarítmica)")
    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.outline.set_visible(False)
    marcas = [
        v
        for v in (5e4, 1e5, 2.5e5, 5e5, 1e6, 2.5e6, 5e6, 1e7)
        if np.nanmin(log_mat) <= np.log10(v) <= np.nanmax(log_mat)
    ]
    cbar.set_ticks(np.log10(marcas))
    cbar.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: fmt.cop_compacto(10**v)))
    return _guardar(fig, ruta)


def grafico_distribucion(res: ResultadoAnalisis, ruta: Path) -> Path:
    costos = res.datos["Costo_Total"]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    bins = np.logspace(np.log10(costos.min()), np.log10(costos.max()), 60)
    ax.hist(costos, bins=bins, color=AZUL, edgecolor=SURFACE, linewidth=0.6)
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(_COP_EJE)
    lineas = [(costos.median(), "Mediana", "-", -6, "right"), (costos.mean(), "Media", "--", 6, "left")]
    for valor, nombre, estilo, dx, ha in lineas:
        ax.axvline(valor, color=TEXT, linewidth=1.2, linestyle=estilo)
        ax.annotate(
            f"{nombre}: {fmt.cop_compacto(valor)}",
            (valor, ax.get_ylim()[1] * 0.92),
            xytext=(dx, 0),
            textcoords="offset points",
            ha=ha,
            fontsize=9,
            color=TEXT,
            bbox={"boxstyle": "round,pad=0.25", "fc": SURFACE, "ec": "none"},
        )
    ax.set_title("Distribución del costo total por consulta (escala logarítmica)")
    ax.set_ylabel("Consultas")
    ax.grid(axis="x", visible=False)
    return _guardar(fig, ruta)


def grafico_pronostico(res: ResultadoAnalisis, ruta: Path) -> Path:
    fig, ejes = plt.subplots(2, 1, figsize=(11, 6.8), sharex=True)
    paneles = [
        ("Consultas", "Consultas por mes: histórico y pronóstico", None),
        ("Costo_Total", "Costo total por mes: histórico y pronóstico", _COP_EJE),
    ]
    for ax, (clave, titulo, formato) in zip(ejes, paneles, strict=True):
        p = res.pronostico[clave]
        tabla = p.tabla
        ax.plot(
            p.historico.index,
            p.historico,
            color=AZUL,
            linewidth=2,
            marker="o",
            markersize=3.5,
            label="Histórico",
        )
        # El pronóstico arranca en el último dato observado para que la línea sea continua
        x = [p.historico.index[-1], *tabla.index]
        ax.plot(
            x,
            [p.historico.iloc[-1], *tabla["Pronostico"]],
            color=NARANJA,
            linewidth=2,
            linestyle="--",
            marker="o",
            markersize=3.5,
            markevery=list(range(1, len(x))),
            label="Pronóstico",
        )
        ax.fill_between(
            tabla.index,
            tabla["Limite_Inferior"],
            tabla["Limite_Superior"],
            color=NARANJA,
            alpha=0.18,
            linewidth=0,
            label="Intervalo 90 %",
        )
        ax.axvline(p.historico.index[-1], color=TEXT_2, linewidth=0.8, linestyle=":")
        if p.mape_modelo is not None:
            ax.text(
                0.01,
                0.06,
                f"Backtest 6 meses · MAPE {fmt.porcentaje(p.mape_modelo)} "
                f"(ingenuo estacional {fmt.porcentaje(p.mape_ingenuo)})",
                transform=ax.transAxes,
                fontsize=8.5,
                color=TEXT_2,
            )
        ax.set_title(titulo)
        ax.set_ylim(0, max(p.historico.max(), tabla["Limite_Superior"].max()) * 1.12)
        ax.grid(axis="x", visible=False)
        if formato:
            ax.yaxis.set_major_formatter(formato)
    ejes[0].legend(loc="upper left", ncols=3)
    return _guardar(fig, ruta)


GRAFICOS = {
    "costo_por_eps.png": grafico_costo_eps,
    "costo_por_diagnostico.png": grafico_costo_diagnostico,
    "tendencia_mensual.png": grafico_tendencia,
    "costo_grupo_etario_sexo.png": grafico_grupo_etario,
    "heatmap_eps_diagnostico.png": grafico_heatmap,
    "distribucion_costos.png": grafico_distribucion,
    "pronostico_mensual.png": grafico_pronostico,
}


def generar_graficos(res: ResultadoAnalisis, carpeta: Path) -> list[Path]:
    _estilo()
    carpeta.mkdir(parents=True, exist_ok=True)
    return [
        funcion(res, carpeta / nombre)
        for nombre, funcion in GRAFICOS.items()
        if funcion is not grafico_pronostico or res.pronostico
    ]
