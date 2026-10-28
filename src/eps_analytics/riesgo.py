"""Estratificación de pacientes en una pirámide de riesgo.

Modelo de puntaje explicable inspirado en la pirámide de Kaiser Permanente,
usada por las EPS para enfocar la gestión del riesgo en salud:

- Nivel 3 · Gestión de caso: pocos pacientes, complejos, de gasto muy alto.
- Nivel 2 · Gestión de enfermedad: crónicos que requieren seguimiento.
- Nivel 1 · Promoción y prevención: el resto de la población.

Cada punto tiene una razón legible, así un auditor o un médico puede ver por
qué un paciente quedó en su nivel. ``validar_prospectivo`` comprueba que el
puntaje calculado con un año de historia anticipa el gasto del año siguiente.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Condiciones crónicas y sus puntos (las de alto costo pesan más)
CRONICAS = {
    "I10": ("Hipertensión", 2),
    "E11.9": ("Diabetes", 2),
    "J45.9": ("Asma", 2),
    "F41.1": ("Ansiedad", 1),
    "I25.1": ("Cardiopatía isquémica", 3),
    "C50.9": ("Cáncer de mama", 4),
}

NIVELES = ["Nivel 1 · Promoción y prevención", "Nivel 2 · Gestión de enfermedad", "Nivel 3 · Gestión de caso"]
CORTE_NIVEL_2 = 3
CORTE_NIVEL_3 = 7


def perfil_pacientes(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por paciente con las variables que alimentan el puntaje."""
    base = df.groupby("ID_Paciente").agg(
        EPS=("EPS", "first"),
        Edad=("Edad", "first"),
        Sexo=("Sexo", "first"),
        Consultas=("ID_Consulta", "count"),
        Urgencias=("Tipo_Atencion", lambda s: int((s == "Urgencias").sum())),
        Gasto_Total=("Costo_Total", "sum"),
    )
    cronicas = (
        df[df["Codigo_CIE10"].isin(CRONICAS)]
        .groupby("ID_Paciente")["Codigo_CIE10"]
        .agg(lambda s: sorted(set(s)))
    )
    base["Cronicas"] = cronicas.reindex(base.index).apply(lambda v: v if isinstance(v, list) else [])
    return base


def puntuar(perfil: pd.DataFrame) -> pd.DataFrame:
    """Asigna puntaje, nivel y factores explicativos a cada paciente."""
    out = perfil.copy()
    percentil_gasto = out["Gasto_Total"].rank(pct=True)
    p90 = out["Consultas"].quantile(0.9)

    puntos, factores = [], []
    for edad, urg, consultas, cron, pct in zip(
        out["Edad"], out["Urgencias"], out["Consultas"], out["Cronicas"], percentil_gasto, strict=True
    ):
        p, f = 0, []
        if edad >= 65:
            p, f = p + 2, [*f, "65+ años"]
        elif edad >= 45:
            p, f = p + 1, [*f, "45-64 años"]
        for codigo in cron:
            nombre, valor = CRONICAS[codigo]
            p, f = p + valor, [*f, nombre]
        if len(cron) >= 2:
            p, f = p + 1, [*f, "Multimorbilidad"]
        if urg >= 2:
            p, f = p + 2, [*f, f"{urg} urgencias"]
        elif urg == 1:
            p, f = p + 1, [*f, "1 urgencia"]
        if consultas > p90:
            p, f = p + 1, [*f, "Alta frecuencia de uso"]
        if pct >= 0.95:
            p, f = p + 3, [*f, "Gasto top 5 %"]
        elif pct >= 0.80:
            p, f = p + 1, [*f, "Gasto top 20 %"]
        puntos.append(p)
        factores.append(", ".join(f) if f else "Sin factores")

    out["Puntaje"] = puntos
    out["Factores"] = factores
    out["Nivel"] = pd.Categorical(
        np.select(
            [out["Puntaje"] >= CORTE_NIVEL_3, out["Puntaje"] >= CORTE_NIVEL_2], NIVELES[:0:-1], NIVELES[0]
        ),
        categories=NIVELES,
        ordered=True,
    )
    return out.sort_values(["Puntaje", "Gasto_Total"], ascending=False)


def estratificar(df: pd.DataFrame) -> pd.DataFrame:
    return puntuar(perfil_pacientes(df))


def resumen_piramide(estratos: pd.DataFrame) -> pd.DataFrame:
    res = estratos.groupby("Nivel", observed=False).agg(
        Pacientes=("Puntaje", "size"),
        Gasto_Total=("Gasto_Total", "sum"),
        Edad_Promedio=("Edad", "mean"),
        Consultas_Promedio=("Consultas", "mean"),
    )
    res["Participacion_Pacientes"] = res["Pacientes"] / res["Pacientes"].sum()
    res["Participacion_Gasto"] = res["Gasto_Total"] / res["Gasto_Total"].sum()
    res["Gasto_Por_Paciente"] = res["Gasto_Total"] / res["Pacientes"].replace(0, np.nan)
    return res


def validar_prospectivo(df: pd.DataFrame, corte: pd.Timestamp | str | None = None) -> pd.DataFrame:
    """Estratifica con la historia anterior al corte y mide el gasto posterior por nivel.

    Por defecto el corte es la mitad del periodo. Si el puntaje es útil, el
    gasto futuro por paciente debe crecer de forma monótona con el nivel.
    """
    fechas = pd.to_datetime(df["Fecha_Consulta"])
    corte = pd.Timestamp(corte) if corte is not None else fechas.min() + (fechas.max() - fechas.min()) / 2
    antes, despues = df[fechas < corte], df[fechas >= corte]
    estratos = estratificar(antes)
    gasto_futuro = despues.groupby("ID_Paciente")["Costo_Total"].sum()
    estratos["Gasto_Futuro"] = gasto_futuro.reindex(estratos.index).fillna(0.0)
    res = estratos.groupby("Nivel", observed=False).agg(
        Pacientes=("Puntaje", "size"),
        Gasto_Futuro_Por_Paciente=("Gasto_Futuro", "mean"),
    )
    res["Razon_vs_Nivel_1"] = res["Gasto_Futuro_Por_Paciente"] / res["Gasto_Futuro_Por_Paciente"].iloc[0]
    return res
