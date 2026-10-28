"""Dashboard interactivo de costos de atención en salud por EPS.

Ejecutar con:  eps-analytics dashboard   (o)   streamlit run dashboard/app.py
"""

from __future__ import annotations

import io

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from eps_analytics import analysis as an
from eps_analytics import database, synthetic
from eps_analytics import formatting as fmt
from eps_analytics.config import load_settings

AZUL = "#2a78d6"
NARANJA = "#eb6834"
TEXTO_2 = "#52514e"
GRID = "#e4e3df"
SECUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
COLOR_SEXO = {"Mujeres": AZUL, "Hombres": NARANJA}

st.set_page_config(page_title="EPS Analytics", page_icon="🏥", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; padding-bottom: 2rem;}
      [data-testid="stMetric"] {
        background: #f6f8fb; border: 1px solid #e4e8ef; border-radius: 10px;
        padding: 14px 16px;
      }
      [data-testid="stMetricValue"] {font-size: 1.55rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Cargando datos…")
def cargar() -> tuple[pd.DataFrame, pd.DataFrame]:
    engine = database.get_engine(load_settings().db_url)
    try:
        if not database.esquema_existe(engine):
            # Primer arranque sin base: se crea la demo para que el dashboard funcione de inmediato
            database.crear_esquema(engine)
            database.cargar_tablas(engine, synthetic.generar_datos())
        return an.preparar(database.cargar_dataset(engine)), database.cargar_medicamentos(engine)
    finally:
        engine.dispose()


def estilo(fig: go.Figure, alto: int = 380) -> go.Figure:
    fig.update_layout(
        height=alto,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, Segoe UI, sans-serif", "size": 13},
        title={"x": 0, "xanchor": "left", "font": {"size": 16}},
        legend={"orientation": "h", "y": 1.08, "x": 1, "xanchor": "right", "title": None},
        hoverlabel={"bgcolor": "white"},
        bargap=0.25,
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def a_excel(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, sheet_name="Consultas")
    return buffer.getvalue()


datos, meds = cargar()

# ----------------------------------------------------------------- filtros
with st.sidebar:
    st.header("Filtros")
    fecha_min, fecha_max = datos["Fecha_Consulta"].min().date(), datos["Fecha_Consulta"].max().date()
    rango = st.date_input("Periodo", (fecha_min, fecha_max), min_value=fecha_min, max_value=fecha_max)
    eps_sel = st.multiselect("EPS", sorted(datos["EPS"].unique()), placeholder="Todas")
    regimen_sel = st.multiselect("Régimen", sorted(datos["Regimen"].unique()), placeholder="Todos")
    tipo_sel = st.multiselect(
        "Tipo de atención", sorted(datos["Tipo_Atencion"].unique()), placeholder="Todos"
    )
    sexo_sel = st.radio("Sexo", ["Todos", "Mujeres", "Hombres"], horizontal=True)
    edad_sel = st.slider("Edad", 0, int(datos["Edad"].max()), (0, int(datos["Edad"].max())))
    st.divider()
    st.caption(
        "Datos sintéticos generados con `eps-analytics seed`. Ninguna fila corresponde a una persona real."
    )

df = datos
if isinstance(rango, tuple) and len(rango) == 2:
    df = df[df["Fecha_Consulta"].dt.date.between(*rango)]
if eps_sel:
    df = df[df["EPS"].isin(eps_sel)]
if regimen_sel:
    df = df[df["Regimen"].isin(regimen_sel)]
if tipo_sel:
    df = df[df["Tipo_Atencion"].isin(tipo_sel)]
if sexo_sel != "Todos":
    df = df[df["Sexo"] == ("F" if sexo_sel == "Mujeres" else "M")]
df = df[df["Edad"].between(*edad_sel)]
meds_f = meds[meds["ID_Consulta"].isin(df["ID_Consulta"])]

# ----------------------------------------------------------------- encabezado
st.title("🏥 Costos de atención en salud por EPS")
st.caption(
    f"{fmt.numero(len(df))} consultas de {fmt.numero(len(datos))} · "
    f"periodo {df['Fecha_Consulta'].min():%d/%m/%Y} – {df['Fecha_Consulta'].max():%d/%m/%Y}"
    if not df.empty
    else "Sin datos para los filtros seleccionados"
)

if df.empty:
    st.warning("Ningún registro cumple los filtros. Ajusta la selección en la barra lateral.")
    st.stop()

k = an.calcular_kpis(df)
mensual = an.tendencia_mensual(df).reset_index()
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(
    "Costo total",
    fmt.cop_compacto(k["costo_total"]),
    chart_data=mensual["Costo_Total"].tolist(),
    chart_type="area",
)
c2.metric("Pacientes", fmt.numero(k["pacientes"]))
c3.metric(
    "Consultas",
    fmt.numero(k["consultas"]),
    f"{fmt.numero(k['consultas_por_paciente'], 1)} por paciente",
    delta_color="off",
    delta_arrow="off",
)
c4.metric(
    "Costo por consulta",
    fmt.cop_compacto(k["costo_promedio_consulta"]),
    f"mediana {fmt.cop_compacto(k['costo_mediano_consulta'])}",
    delta_color="off",
    delta_arrow="off",
)
c5.metric(
    "Top 5 % pacientes",
    fmt.porcentaje(an.concentracion_gasto(df, 0.05)),
    "del gasto total",
    delta_color="off",
    delta_arrow="off",
)

tab_res, tab_eps, tab_dx, tab_pac, tab_med, tab_datos = st.tabs(
    ["📈 Resumen", "🏢 EPS", "🩺 Diagnósticos", "👥 Pacientes", "💊 Medicamentos", "📄 Datos"]
)

# ----------------------------------------------------------------- resumen
with tab_res:
    izq, der = st.columns(2)
    fig = px.line(
        mensual,
        x="Mes",
        y="Costo_Total",
        markers=True,
        title="Costo total por mes",
        color_discrete_sequence=[AZUL],
    )
    fig.add_scatter(
        x=mensual["Mes"],
        y=mensual["Media_Movil_3M"],
        mode="lines",
        name="Media móvil 3M",
        line={"color": "#184f95", "width": 3, "dash": "dot"},
    )
    fig.update_traces(hovertemplate="%{x|%b %Y}<br>$ %{y:,.0f}<extra></extra>")
    fig.data[0].update(name="Costo mensual", showlegend=True)
    fig.update_yaxes(title=None, tickprefix="$ ", rangemode="tozero")
    fig.update_xaxes(title=None)
    izq.plotly_chart(estilo(fig), width="stretch")

    fig = px.bar(mensual, x="Mes", y="Consultas", title="Consultas por mes", color_discrete_sequence=[AZUL])
    fig.update_traces(hovertemplate="%{x|%b %Y}<br>%{y:,} consultas<extra></extra>")
    fig.update_yaxes(title=None)
    fig.update_xaxes(title=None)
    der.plotly_chart(estilo(fig), width="stretch")

    izq, der = st.columns(2)
    tipo = an.costos_por_tipo_atencion(df).reset_index()
    fig = px.bar(
        tipo,
        x="Costo_Total",
        y="Tipo_Atencion",
        orientation="h",
        title="Costo por tipo de atención",
        color_discrete_sequence=[AZUL],
        custom_data=["Consultas", "Costo_Promedio"],
    )
    fig.update_traces(
        hovertemplate="%{y}<br>Total: $ %{x:,.0f}<br>Consultas: %{customdata[0]:,}"
        "<br>Promedio: $ %{customdata[1]:,.0f}<extra></extra>"
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending", "title": None}, xaxis={"title": None, "tickprefix": "$ "}
    )
    izq.plotly_chart(estilo(fig, 320), width="stretch")

    # Histograma sobre log10(costo): los costos en salud tienen cola larga
    fig = px.histogram(
        x=np.log10(df["Costo_Total"]),
        nbins=60,
        title="Distribución del costo por consulta (escala log)",
        color_discrete_sequence=[AZUL],
    )
    marcas = [1e4, 3e4, 1e5, 3e5, 1e6, 3e6, 1e7, 3e7]
    fig.update_xaxes(title=None, tickvals=np.log10(marcas), ticktext=[fmt.cop_compacto(m) for m in marcas])
    fig.update_traces(
        hovertemplate="%{y:,} consultas<extra></extra>", marker_line={"width": 1, "color": "white"}
    )
    fig.update_yaxes(title="Consultas")
    fig.add_vline(
        x=np.log10(df["Costo_Total"].median()),
        line_color="#0b0b0b",
        annotation_text=f"Mediana {fmt.cop_compacto(df['Costo_Total'].median())}",
        annotation_position="top right",
    )
    der.plotly_chart(estilo(fig, 320), width="stretch")

# ----------------------------------------------------------------- EPS
with tab_eps:
    por_eps = an.costos_por_eps(df).reset_index()
    izq, der = st.columns([1.1, 1])
    fig = px.bar(
        por_eps,
        x="Costo_Total",
        y="EPS",
        orientation="h",
        title="Costo total por EPS",
        color_discrete_sequence=[AZUL],
        text=por_eps["Participacion"].map(fmt.porcentaje),
    )
    fig.update_traces(
        textposition="outside", cliponaxis=False, hovertemplate="%{y}<br>$ %{x:,.0f}<extra></extra>"
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending", "title": None},
        xaxis={"title": None, "tickprefix": "$ ", "range": [0, por_eps["Costo_Total"].max() * 1.18]},
    )
    izq.plotly_chart(estilo(fig, 420), width="stretch")

    fig = px.scatter(
        por_eps,
        x="Consultas",
        y="Costo_Por_Paciente",
        size="Pacientes",
        text="EPS",
        title="Volumen vs. costo por paciente",
        color_discrete_sequence=[AZUL],
        size_max=48,
    )
    fig.update_traces(
        textposition="top center",
        marker={"line": {"width": 2, "color": "white"}},
        hovertemplate="%{text}<br>Consultas: %{x:,}<br>Costo/paciente: $ %{y:,.0f}<extra></extra>",
    )
    fig.update_yaxes(title="Costo por paciente", tickprefix="$ ")
    der.plotly_chart(estilo(fig, 420), width="stretch")

    tabla = por_eps.assign(
        Costo_Total=por_eps["Costo_Total"].map(fmt.cop),
        Costo_Promedio=por_eps["Costo_Promedio"].map(fmt.cop),
        Costo_Mediano=por_eps["Costo_Mediano"].map(fmt.cop),
        Costo_Por_Paciente=por_eps["Costo_Por_Paciente"].map(fmt.cop),
        Participacion=por_eps["Participacion"].map(fmt.porcentaje),
    )
    st.dataframe(tabla, hide_index=True, width="stretch")

# ----------------------------------------------------------------- diagnósticos
with tab_dx:
    por_dx = an.costos_por_diagnostico(df).reset_index()
    fig = go.Figure()
    fig.add_bar(
        x=por_dx["Diagnostico"],
        y=por_dx["Costo_Total"],
        marker_color=AZUL,
        name="Costo total",
        text=por_dx["Participacion"].map(fmt.porcentaje),
        textposition="outside",
        cliponaxis=False,
        customdata=por_dx["Participacion_Acumulada"],
        hovertemplate="%{x}<br>$ %{y:,.0f}<br>Acumulado: %{customdata:.1%}<extra></extra>",
    )
    fig.update_layout(
        title="Pareto de costos por diagnóstico",
        showlegend=False,
        yaxis={"tickprefix": "$ "},
        xaxis={"tickangle": -30},
    )
    st.plotly_chart(estilo(fig, 420), width="stretch")

    orden_eps = an.costos_por_eps(df).index
    matriz = an.matriz_eps_diagnostico(df).reindex(index=por_dx["Diagnostico"], columns=orden_eps)
    # Color en escala logarítmica para que un caso extremo no aplane el resto
    fig = px.imshow(
        np.log10(matriz),
        color_continuous_scale=SECUENCIAL,
        aspect="auto",
        title="Costo promedio por consulta: diagnóstico × EPS (color en escala log)",
    )
    fig.update_traces(
        customdata=matriz.to_numpy(),
        text=matriz.map(lambda v: "" if pd.isna(v) else fmt.cop_compacto(v)[2:]),
        texttemplate="%{text}",
        hovertemplate="%{y}<br>%{x}<br>$ %{customdata:,.0f}<extra></extra>",
    )
    escala = [
        v
        for v in (5e4, 1e5, 2.5e5, 5e5, 1e6, 2.5e6, 5e6)
        if np.nanmin(matriz.to_numpy()) <= v <= np.nanmax(matriz.to_numpy())
    ]
    fig.update_layout(
        coloraxis_colorbar={
            "title": None,
            "tickvals": np.log10(escala),
            "ticktext": [fmt.cop_compacto(v) for v in escala],
        }
    )
    fig.update_xaxes(title=None, gridcolor="rgba(0,0,0,0)")
    fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)")
    st.plotly_chart(estilo(fig, 520), width="stretch")

# ----------------------------------------------------------------- pacientes
with tab_pac:
    grupo = an.costos_por_grupo_etario(df).reset_index()
    grupo["Sexo"] = grupo["Sexo"].map({"F": "Mujeres", "M": "Hombres"})
    izq, der = st.columns(2)
    fig = px.bar(
        grupo,
        x="Grupo_Etario",
        y="Costo_Por_Paciente",
        color="Sexo",
        barmode="group",
        title="Costo por paciente según edad y sexo",
        color_discrete_map=COLOR_SEXO,
        category_orders={"Grupo_Etario": an.GRUPOS_ETARIOS, "Sexo": ["Mujeres", "Hombres"]},
    )
    fig.update_traces(hovertemplate="%{x} años<br>$ %{y:,.0f}<extra>%{fullData.name}</extra>")
    fig.update_layout(xaxis_title="Grupo etario", yaxis={"title": None, "tickprefix": "$ "})
    izq.plotly_chart(estilo(fig), width="stretch")

    regimen = (
        df.groupby("Regimen")
        .agg(Pacientes=("ID_Paciente", "nunique"), Costo_Total=("Costo_Total", "sum"))
        .reset_index()
    )
    regimen["Costo_Por_Paciente"] = regimen["Costo_Total"] / regimen["Pacientes"]
    fig = px.bar(
        regimen,
        x="Regimen",
        y="Costo_Por_Paciente",
        title="Costo por paciente según régimen",
        color_discrete_sequence=[AZUL],
        text=regimen["Costo_Por_Paciente"].map(fmt.cop_compacto),
    )
    fig.update_traces(
        textposition="outside", cliponaxis=False, hovertemplate="%{x}<br>$ %{y:,.0f}<extra></extra>"
    )
    fig.update_layout(xaxis_title=None, yaxis={"title": None, "tickprefix": "$ "})
    der.plotly_chart(estilo(fig), width="stretch")

    st.subheader("Pacientes de alto costo (percentil 99)")
    alto = an.pacientes_alto_costo(df)
    st.dataframe(alto.assign(Gasto_Total=alto["Gasto_Total"].map(fmt.cop)), hide_index=True, width="stretch")

# ----------------------------------------------------------------- medicamentos
with tab_med:
    if meds_f.empty:
        st.info("No hay medicamentos formulados para la selección actual.")
    else:
        top = an.top_medicamentos(meds_f, 12).reset_index()
        izq, der = st.columns([1.2, 1])
        fig = px.bar(
            top,
            x="Costo_Total",
            y="Nombre_Medicamento",
            orientation="h",
            title="Top 12 medicamentos por costo",
            color_discrete_sequence=[AZUL],
            custom_data=["Formulaciones"],
        )
        fig.update_traces(
            hovertemplate="%{y}<br>$ %{x:,.0f}<br>%{customdata[0]:,} formulaciones<extra></extra>"
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending", "title": None},
            xaxis={"title": None, "tickprefix": "$ "},
        )
        izq.plotly_chart(estilo(fig, 460), width="stretch")
        der.metric(
            "Participación de medicamentos en el costo", fmt.porcentaje(k["participacion_medicamentos"])
        )
        der.metric("Formulaciones", fmt.numero(len(meds_f)))
        der.metric("Consultas con fórmula", fmt.porcentaje((df["Num_Medicamentos"] > 0).mean()))

# ----------------------------------------------------------------- datos
with tab_datos:
    st.subheader("Consultas atípicas (Tukey sobre log-costo, k = 3)")
    st.dataframe(an.detectar_atipicos(df).head(50), hide_index=True, width="stretch")
    st.subheader("Detalle de consultas")
    columnas = [
        "ID_Consulta",
        "Fecha_Consulta",
        "EPS",
        "Regimen",
        "Ciudad",
        "Sexo",
        "Edad",
        "Tipo_Atencion",
        "Codigo_CIE10",
        "Diagnostico",
        "Costo_Consulta",
        "Costo_Medicamentos",
        "Costo_Total",
    ]
    st.dataframe(df[columnas], hide_index=True, width="stretch", height=360)
    d1, d2, _ = st.columns([1, 1, 4])
    d1.download_button(
        "⬇️ CSV", df[columnas].to_csv(index=False).encode("utf-8"), "consultas_eps.csv", "text/csv"
    )
    d2.download_button(
        "⬇️ Excel",
        a_excel(df[columnas]),
        "consultas_eps.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
