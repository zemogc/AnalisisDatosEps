"""Indicadores y agregaciones sobre el dataset de consultas.

Todas las funciones son puras (DataFrame -> DataFrame), así se reutilizan en
el reporte por línea de comandos, en el dashboard y en las pruebas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

GRUPOS_ETARIOS = ["0-17", "18-29", "30-44", "45-59", "60+"]
_CORTES_EDAD = [-1, 17, 29, 44, 59, 200]

COLUMNAS_REQUERIDAS = {
    "ID_Consulta",
    "ID_Paciente",
    "Edad",
    "Sexo",
    "EPS",
    "Fecha_Consulta",
    "Diagnostico",
    "Costo_Consulta",
    "Costo_Medicamentos",
}


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Valida columnas y agrega campos derivados (costo total, mes, grupo etario)."""
    faltantes = COLUMNAS_REQUERIDAS - set(df.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas en el dataset: {sorted(faltantes)}")
    out = df.copy()
    out["Fecha_Consulta"] = pd.to_datetime(out["Fecha_Consulta"])
    out["Costo_Total"] = out["Costo_Consulta"] + out["Costo_Medicamentos"]
    out["Mes"] = out["Fecha_Consulta"].dt.to_period("M").dt.to_timestamp()
    out["Grupo_Etario"] = pd.cut(out["Edad"], bins=_CORTES_EDAD, labels=GRUPOS_ETARIOS).astype(
        pd.CategoricalDtype(GRUPOS_ETARIOS, ordered=True)
    )
    return out


def calcular_kpis(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return dict.fromkeys(
            [
                "pacientes",
                "consultas",
                "costo_total",
                "costo_promedio_consulta",
                "costo_mediano_consulta",
                "costo_por_paciente",
                "consultas_por_paciente",
                "participacion_medicamentos",
            ],
            0.0,
        )
    pacientes = df["ID_Paciente"].nunique()
    total = df["Costo_Total"].sum()
    return {
        "pacientes": float(pacientes),
        "consultas": float(len(df)),
        "costo_total": float(total),
        "costo_promedio_consulta": float(df["Costo_Total"].mean()),
        "costo_mediano_consulta": float(df["Costo_Total"].median()),
        "costo_por_paciente": float(total / pacientes),
        "consultas_por_paciente": float(len(df) / pacientes),
        "participacion_medicamentos": float(df["Costo_Medicamentos"].sum() / total),
    }


def _resumen(df: pd.DataFrame, por: str | list[str]) -> pd.DataFrame:
    res = df.groupby(por, observed=True).agg(
        Pacientes=("ID_Paciente", "nunique"),
        Consultas=("ID_Consulta", "count"),
        Costo_Total=("Costo_Total", "sum"),
        Costo_Promedio=("Costo_Total", "mean"),
        Costo_Mediano=("Costo_Total", "median"),
    )
    res["Costo_Por_Paciente"] = res["Costo_Total"] / res["Pacientes"]
    res["Participacion"] = res["Costo_Total"] / res["Costo_Total"].sum()
    return res


def costos_por_eps(df: pd.DataFrame) -> pd.DataFrame:
    return _resumen(df, "EPS").sort_values("Costo_Total", ascending=False)


def costos_por_diagnostico(df: pd.DataFrame) -> pd.DataFrame:
    res = _resumen(df, ["Codigo_CIE10", "Diagnostico"] if "Codigo_CIE10" in df else "Diagnostico")
    res = res.sort_values("Costo_Total", ascending=False)
    res["Participacion_Acumulada"] = res["Participacion"].cumsum()
    return res


def costos_por_grupo_etario(df: pd.DataFrame) -> pd.DataFrame:
    return _resumen(df, ["Grupo_Etario", "Sexo"])


def costos_por_tipo_atencion(df: pd.DataFrame) -> pd.DataFrame:
    return _resumen(df, "Tipo_Atencion").sort_values("Costo_Total", ascending=False)


def tendencia_mensual(df: pd.DataFrame) -> pd.DataFrame:
    res = df.groupby("Mes").agg(
        Consultas=("ID_Consulta", "count"),
        Costo_Total=("Costo_Total", "sum"),
        Costo_Promedio=("Costo_Total", "mean"),
    )
    res["Variacion_Costo"] = res["Costo_Total"].pct_change()
    res["Media_Movil_3M"] = res["Costo_Total"].rolling(3, min_periods=1).mean()
    return res


def matriz_eps_diagnostico(df: pd.DataFrame, valor: str = "Costo_Total", agg: str = "mean") -> pd.DataFrame:
    return df.pivot_table(index="Diagnostico", columns="EPS", values=valor, aggfunc=agg)


def top_medicamentos(meds: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    res = meds.groupby("Nombre_Medicamento").agg(
        Formulaciones=("ID_Medicamento", "count"),
        Unidades=("Cantidad", "sum"),
        Costo_Total=("Costo", "sum"),
    )
    res["Costo_Unitario_Promedio"] = res["Costo_Total"] / res["Unidades"]
    return res.sort_values("Costo_Total", ascending=False).head(n)


def detectar_atipicos(df: pd.DataFrame, k: float = 3.0) -> pd.DataFrame:
    """Consultas con costo total atípico según el criterio de Tukey (Q3 + k·IQR).

    Se usa la escala logarítmica porque los costos en salud son asimétricos;
    en escala lineal casi cualquier consulta de especialista saldría atípica.
    """
    if df.empty:
        return df.iloc[0:0]
    log_costo = np.log1p(df["Costo_Total"])
    q1, q3 = log_costo.quantile([0.25, 0.75])
    umbral = q3 + k * (q3 - q1)
    return df.loc[log_costo > umbral].sort_values("Costo_Total", ascending=False)


def pacientes_alto_costo(df: pd.DataFrame, percentil: float = 0.99) -> pd.DataFrame:
    gasto = df.groupby(["ID_Paciente", "EPS"], as_index=False).agg(
        Consultas=("ID_Consulta", "count"), Gasto_Total=("Costo_Total", "sum")
    )
    corte = gasto["Gasto_Total"].quantile(percentil)
    return gasto[gasto["Gasto_Total"] >= corte].sort_values("Gasto_Total", ascending=False)


def concentracion_gasto(df: pd.DataFrame, top: float = 0.05) -> float:
    """Fracción del gasto total que concentra el ``top`` % de pacientes más costosos."""
    gasto = df.groupby("ID_Paciente")["Costo_Total"].sum().sort_values(ascending=False)
    if gasto.empty:
        return 0.0
    n = max(1, int(np.ceil(len(gasto) * top)))
    return float(gasto.iloc[:n].sum() / gasto.sum())


@dataclass
class ResultadoAnalisis:
    datos: pd.DataFrame
    kpis: dict[str, float]
    por_eps: pd.DataFrame
    por_diagnostico: pd.DataFrame
    por_grupo_etario: pd.DataFrame
    por_tipo_atencion: pd.DataFrame
    mensual: pd.DataFrame
    matriz_eps_dx: pd.DataFrame
    medicamentos: pd.DataFrame
    atipicos: pd.DataFrame
    alto_costo: pd.DataFrame
    concentracion_top5: float
    pronostico: dict = field(default_factory=dict)
    estratos: pd.DataFrame = field(default_factory=pd.DataFrame)
    piramide: pd.DataFrame = field(default_factory=pd.DataFrame)
    validacion_riesgo: pd.DataFrame = field(default_factory=pd.DataFrame)


def ejecutar_analisis(consultas: pd.DataFrame, meds: pd.DataFrame, horizonte: int = 6) -> ResultadoAnalisis:
    from eps_analytics import riesgo
    from eps_analytics.forecast import pronosticar_mensual

    df = preparar(consultas)
    mensual = tendencia_mensual(df)
    estratos = riesgo.estratificar(df)
    return ResultadoAnalisis(
        datos=df,
        kpis=calcular_kpis(df),
        por_eps=costos_por_eps(df),
        por_diagnostico=costos_por_diagnostico(df),
        por_grupo_etario=costos_por_grupo_etario(df),
        por_tipo_atencion=costos_por_tipo_atencion(df),
        mensual=mensual,
        matriz_eps_dx=matriz_eps_diagnostico(df),
        medicamentos=top_medicamentos(meds, n=15),
        atipicos=detectar_atipicos(df),
        alto_costo=pacientes_alto_costo(df),
        concentracion_top5=concentracion_gasto(df, 0.05),
        pronostico=pronosticar_mensual(mensual, horizonte) if len(mensual) >= 4 else {},
        estratos=estratos,
        piramide=riesgo.resumen_piramide(estratos),
        validacion_riesgo=riesgo.validar_prospectivo(df) if len(mensual) >= 6 else pd.DataFrame(),
    )
