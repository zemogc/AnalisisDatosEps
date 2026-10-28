import numpy as np
import pandas as pd
import pytest

from eps_analytics import forecast as fc


def serie_sintetica(meses: int = 36, ruido: float = 0.0, seed: int = 0) -> pd.Series:
    """Tendencia +1 %/mes y pico de +40 % en abril, en escala multiplicativa."""
    fechas = pd.date_range("2022-01-01", periods=meses, freq="MS")
    t = np.arange(meses)
    estacional = np.where(fechas.month == 4, np.log(1.4), 0.0)
    log_y = np.log(1000) + 0.01 * t + estacional
    log_y += np.random.default_rng(seed).normal(0, ruido, meses)
    return pd.Series(np.exp(log_y), index=fechas)


def mensual_desde(consultas: pd.Series, costo_promedio: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"Consultas": consultas, "Costo_Total": consultas * costo_promedio})


def test_recupera_tendencia_y_estacionalidad_exactas():
    serie = serie_sintetica(36)
    pron = fc.pronosticar_consultas(serie, horizonte=12)
    esperado = serie_sintetica(48).iloc[-12:].to_numpy()
    np.testing.assert_allclose(pron.tabla["Pronostico"].to_numpy(), esperado, rtol=1e-6)
    pd.testing.assert_series_equal(pron.ajuste, serie, check_names=False, rtol=1e-6)


def test_intervalos_contienen_pronostico_y_crecen_con_horizonte():
    pron = fc.pronosticar_consultas(serie_sintetica(36, ruido=0.05), horizonte=24)
    t = pron.tabla
    assert (t["Limite_Inferior"] < t["Pronostico"]).all()
    assert (t["Pronostico"] < t["Limite_Superior"]).all()
    assert (t["Limite_Inferior"] > 0).all()
    # Mismo mes calendario un año después: solo cambia la distancia al último dato
    ancho = np.log(t["Limite_Superior"] / t["Limite_Inferior"])
    assert ancho.iloc[12] > ancho.iloc[0]


def test_fechas_del_pronostico_continuan_la_serie():
    pron = fc.pronosticar_consultas(serie_sintetica(24), horizonte=3)
    assert list(pron.tabla.index) == list(pd.date_range("2024-01-01", periods=3, freq="MS"))


def test_serie_corta_usa_solo_tendencia():
    serie = serie_sintetica(8)
    pron = fc.pronosticar_consultas(serie, horizonte=2)
    assert len(pron.tabla) == 2
    assert np.isfinite(pron.tabla.to_numpy()).all()


def test_tolera_meses_sin_registros():
    serie = serie_sintetica(30).drop(pd.Timestamp("2023-02-01"))
    pron = fc.pronosticar_consultas(serie, horizonte=1)
    assert pron.tabla.index[0] == pd.Timestamp("2024-07-01")


@pytest.mark.parametrize(
    ("serie", "horizonte"),
    [
        (pd.Series([1.0, 2.0, 3.0], index=pd.date_range("2024-01-01", periods=3, freq="MS")), 1),
        (pd.Series([1.0, 0.0, 3.0, 4.0], index=pd.date_range("2024-01-01", periods=4, freq="MS")), 1),
        (serie_sintetica(12), 0),
    ],
)
def test_entradas_invalidas(serie, horizonte):
    with pytest.raises(ValueError):
        fc.pronosticar_consultas(serie, horizonte)


def test_costo_robusto_ante_evento_extremo():
    """Un evento catastrófico aislado no debe trasladarse al mismo mes de años siguientes."""
    consultas = serie_sintetica(36)
    severidad = pd.Series(100_000.0, index=consultas.index)
    severidad.iloc[12] *= 8  # enero del segundo año
    pron = fc.pronosticar_costo(mensual_desde(consultas, severidad), horizonte=1)
    esperado = serie_sintetica(37).iloc[-1] * 100_000
    assert pron.tabla["Pronostico"].iloc[0] == pytest.approx(esperado, rel=0.02)


def test_backtest_le_gana_al_ingenuo_con_tendencia():
    consultas = serie_sintetica(36, ruido=0.02, seed=3) * np.exp(0.03 * np.arange(36))
    mensual = mensual_desde(consultas, pd.Series(50_000.0, index=consultas.index))
    resultado = fc.pronosticar_mensual(mensual, horizonte=6)
    for pron in resultado.values():
        assert pron.mape_modelo is not None
        assert pron.mape_modelo < pron.mape_ingenuo


def test_sin_backtest_si_no_hay_historia_suficiente():
    consultas = serie_sintetica(10)
    resultado = fc.pronosticar_mensual(mensual_desde(consultas, consultas * 0 + 1_000), horizonte=3)
    assert resultado["Costo_Total"].mape_modelo is None


def test_mape():
    assert fc.mape([100, 200], [110, 180]) == pytest.approx(0.1)


def test_tabla_pronostico_une_columnas():
    consultas = serie_sintetica(24)
    tabla = fc.tabla_pronostico(
        fc.pronosticar_mensual(mensual_desde(consultas, consultas * 0 + 1_000), horizonte=4)
    )
    assert len(tabla) == 4
    assert {"Consultas_Pronostico", "Costo_Pronostico", "Costo_Limite_Superior"} <= set(tabla.columns)
