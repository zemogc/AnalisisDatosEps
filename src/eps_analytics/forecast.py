"""Pronóstico mensual de consultas y costo.

El costo se descompone como en la práctica actuarial, **frecuencia × severidad**:

- Frecuencia (consultas/mes): regresión log-lineal con tendencia y
  estacionalidad mensual. El volumen es una serie estable y su estacionalidad
  (temporadas de lluvia) es real.
- Severidad (costo promedio por consulta): tendencia log-lineal robusta
  (Huber) sin efectos mensuales. Los eventos de alto costo son raros y
  aleatorios; con efectos por mes, un solo evento definiría la
  "estacionalidad" de ese mes en todos los años siguientes.

Los intervalos se calculan en escala log (asimétricos y nunca negativos) y la
calidad se mide con un backtest frente al ingenuo estacional (mismo mes del año
anterior).
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd

PERIODO = 12
HUBER_K = 1.345
MAX_ITER = 50


@dataclass
class _Proyeccion:
    fechas: pd.DatetimeIndex
    log_pred: np.ndarray
    error_log: np.ndarray  # error estándar de predicción en escala log
    ajuste: pd.Series


@dataclass
class Pronostico:
    historico: pd.Series
    ajuste: pd.Series
    tabla: pd.DataFrame  # índice Mes; columnas Pronostico, Limite_Inferior, Limite_Superior
    mape_modelo: float | None = None
    mape_ingenuo: float | None = None


def _diseno(t: np.ndarray, meses: np.ndarray, estacional: bool) -> np.ndarray:
    columnas = [np.ones_like(t, dtype=float), t.astype(float)]
    if estacional:
        # Enero es la referencia; once variables indicadoras para el resto
        columnas += [(meses == m).astype(float) for m in range(2, 13)]
    return np.column_stack(columnas)


def _ajustar(x: np.ndarray, y: np.ndarray, robusto: bool) -> tuple[np.ndarray, np.ndarray, float]:
    """Mínimos cuadrados, opcionalmente reponderados con pesos de Huber (IRLS)."""
    pesos = np.ones_like(y)
    for _ in range(MAX_ITER if robusto else 1):
        raiz = np.sqrt(pesos)
        coef, *_ = np.linalg.lstsq(x * raiz[:, None], y * raiz, rcond=None)
        residuos = y - x @ coef
        if not robusto:
            break
        escala = 1.4826 * np.median(np.abs(residuos - np.median(residuos))) or 1e-9
        nuevos = np.minimum(1.0, HUBER_K * escala / np.maximum(np.abs(residuos), 1e-12))
        if np.allclose(nuevos, pesos, atol=1e-6):
            break
        pesos = nuevos
    gl = max(pesos.sum() - x.shape[1], 1.0)
    sigma = float(np.sqrt((pesos * residuos**2).sum() / gl))
    return coef, pesos, sigma


def _proyectar(serie: pd.Series, horizonte: int, estacional: bool, robusto: bool) -> _Proyeccion:
    if len(serie) < 4:
        raise ValueError("Se necesitan al menos 4 meses de historia para pronosticar")
    if (serie <= 0).any():
        raise ValueError("La serie debe ser estrictamente positiva")
    if horizonte < 1:
        raise ValueError("El horizonte debe ser de al menos 1 mes")
    # Con poco más de un año no hay grados de libertad para estimar 11 efectos mensuales
    estacional = estacional and len(serie) >= PERIODO + 6

    y = np.log(serie.to_numpy(dtype=float))
    # El tiempo se mide en meses calendario: tolera meses sin registros
    t = (serie.index.year - serie.index[0].year) * 12 + (serie.index.month - serie.index[0].month)
    t = t.to_numpy()
    x = _diseno(t, serie.index.month.to_numpy(), estacional)
    coef, pesos, sigma = _ajustar(x, y, robusto)

    fechas = pd.date_range(serie.index[-1] + pd.offsets.MonthBegin(1), periods=horizonte, freq="MS")
    x_fut = _diseno(np.arange(t[-1] + 1, t[-1] + 1 + horizonte), fechas.month.to_numpy(), estacional)
    # Error de predicción: ruido + incertidumbre de los coeficientes, x0' (X'WX)^-1 x0
    cov = np.linalg.pinv((x * pesos[:, None]).T @ x)
    error = sigma * np.sqrt(1 + np.einsum("ij,jk,ik->i", x_fut, cov, x_fut))
    return _Proyeccion(fechas, x_fut @ coef, error, pd.Series(np.exp(x @ coef), index=serie.index))


def _tabla(fechas: pd.DatetimeIndex, log_pred: np.ndarray, error: np.ndarray, nivel: float) -> pd.DataFrame:
    z = NormalDist().inv_cdf(0.5 + nivel / 2)
    return pd.DataFrame(
        {
            "Pronostico": np.exp(log_pred),
            "Limite_Inferior": np.exp(log_pred - z * error),
            "Limite_Superior": np.exp(log_pred + z * error),
        },
        index=pd.Index(fechas, name="Mes"),
    )


def pronosticar_consultas(consultas: pd.Series, horizonte: int = 6, nivel: float = 0.9) -> Pronostico:
    serie = consultas.astype(float).sort_index()
    p = _proyectar(serie, horizonte, estacional=True, robusto=False)
    return Pronostico(serie, p.ajuste, _tabla(p.fechas, p.log_pred, p.error_log, nivel))


def pronosticar_costo(mensual: pd.DataFrame, horizonte: int = 6, nivel: float = 0.9) -> Pronostico:
    """Costo = consultas (con estacionalidad) × costo promedio (tendencia robusta)."""
    mensual = mensual.sort_index()
    frecuencia = _proyectar(mensual["Consultas"].astype(float), horizonte, estacional=True, robusto=False)
    severidad = _proyectar(
        (mensual["Costo_Total"] / mensual["Consultas"]).astype(float),
        horizonte,
        estacional=False,
        robusto=True,
    )
    error = np.sqrt(frecuencia.error_log**2 + severidad.error_log**2)
    return Pronostico(
        mensual["Costo_Total"].astype(float),
        frecuencia.ajuste * severidad.ajuste,
        _tabla(frecuencia.fechas, frecuencia.log_pred + severidad.log_pred, error, nivel),
    )


def mape(real, pred) -> float:
    real, pred = np.asarray(real, float), np.asarray(pred, float)
    return float(np.mean(np.abs(real - pred) / real))


def _evaluar(
    resultado: Pronostico, modelo, mensual: pd.DataFrame, columna: str, horizonte: int
) -> Pronostico:
    """Reajusta sin los últimos meses y compara contra lo observado y contra el ingenuo estacional."""
    if len(mensual) < horizonte + PERIODO:
        return resultado
    real = mensual[columna].iloc[-horizonte:].to_numpy(dtype=float)
    pred = modelo(mensual.iloc[:-horizonte], horizonte).tabla["Pronostico"].to_numpy()
    ingenuo = mensual[columna].shift(PERIODO).iloc[-horizonte:].to_numpy(dtype=float)
    resultado.mape_modelo = mape(real, pred)
    resultado.mape_ingenuo = mape(real, ingenuo)
    return resultado


def pronosticar_mensual(
    mensual: pd.DataFrame, horizonte: int = 6, nivel: float = 0.9
) -> dict[str, Pronostico]:
    """Pronóstico con backtest de consultas y costo a partir de ``analysis.tendencia_mensual``."""
    return {
        "Consultas": _evaluar(
            pronosticar_consultas(mensual["Consultas"], horizonte, nivel),
            lambda m, h: pronosticar_consultas(m["Consultas"], h),
            mensual,
            "Consultas",
            horizonte,
        ),
        "Costo_Total": _evaluar(
            pronosticar_costo(mensual, horizonte, nivel), pronosticar_costo, mensual, "Costo_Total", horizonte
        ),
    }


def tabla_pronostico(pronosticos: dict[str, Pronostico]) -> pd.DataFrame:
    """Une los pronósticos de consultas y costo en una sola tabla mensual."""
    partes = []
    for nombre, prefijo in (("Consultas", "Consultas"), ("Costo_Total", "Costo")):
        if nombre in pronosticos:
            tabla = pronosticos[nombre].tabla
            partes.append(tabla.rename(columns=lambda c, p=prefijo: f"{p}_{c}"))
    return pd.concat(partes, axis=1) if partes else pd.DataFrame()
