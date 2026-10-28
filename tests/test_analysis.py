import pandas as pd
import pytest

from eps_analytics import analysis as an
from eps_analytics import database


@pytest.fixture
def mini(mini_db):
    return an.preparar(database.cargar_dataset(mini_db))


@pytest.fixture(scope="module")
def resultado(engine):
    return an.ejecutar_analisis(database.cargar_dataset(engine), database.cargar_medicamentos(engine))


def test_preparar_valida_columnas():
    with pytest.raises(ValueError, match="Faltan columnas"):
        an.preparar(pd.DataFrame({"EPS": ["Sanitas"]}))


def test_preparar_campos_derivados(mini):
    assert mini.set_index("ID_Consulta").loc[10, "Costo_Total"] == 69_000
    assert list(mini["Grupo_Etario"].astype(str)) == ["30-44", "30-44", "60+"]
    assert mini["Mes"].dt.day.eq(1).all()


def test_kpis_calculados_a_mano(mini):
    k = an.calcular_kpis(mini)
    assert k["pacientes"] == 2
    assert k["consultas"] == 3
    assert k["costo_total"] == 69_000 + 120_000 + 310_000
    assert k["costo_por_paciente"] == pytest.approx(499_000 / 2)
    assert k["consultas_por_paciente"] == pytest.approx(1.5)
    assert k["participacion_medicamentos"] == pytest.approx(29_000 / 499_000)


def test_kpis_dataset_vacio(mini):
    assert all(v == 0 for v in an.calcular_kpis(mini.iloc[0:0]).values())


def test_por_eps_suma_total(resultado):
    assert resultado.por_eps["Costo_Total"].sum() == pytest.approx(resultado.kpis["costo_total"])
    assert resultado.por_eps["Participacion"].sum() == pytest.approx(1)
    assert resultado.por_eps["Costo_Total"].is_monotonic_decreasing


def test_pareto_acumulado_termina_en_100(resultado):
    acumulado = resultado.por_diagnostico["Participacion_Acumulada"]
    assert acumulado.is_monotonic_increasing
    assert acumulado.iloc[-1] == pytest.approx(1)


def test_tendencia_mensual(resultado):
    m = resultado.mensual
    assert m["Consultas"].sum() == resultado.kpis["consultas"]
    assert len(m) == 12
    assert pd.isna(m["Variacion_Costo"].iloc[0])


def test_grupo_etario_cubre_todos_los_pacientes(resultado):
    assert resultado.por_grupo_etario["Consultas"].sum() == resultado.kpis["consultas"]


def test_matriz_eps_diagnostico(mini):
    mat = an.matriz_eps_diagnostico(mini)
    assert mat.loc["Hipertensión esencial", "Nueva EPS"] == 310_000
    assert pd.isna(mat.loc["Hipertensión esencial", "Sanitas"])


def test_top_medicamentos(mini_db):
    top = an.top_medicamentos(database.cargar_medicamentos(mini_db), n=2)
    assert len(top) == 2
    assert top.index[0] == "Loratadina 10 mg"
    assert top.loc["Loratadina 10 mg", "Costo_Unitario_Promedio"] == 7_000


def test_detectar_atipicos_marca_valor_extremo():
    base = pd.DataFrame({"Costo_Total": [100_000.0] * 50 + [110_000.0] * 50 + [50_000_000.0]})
    atipicos = an.detectar_atipicos(base)
    assert list(atipicos["Costo_Total"]) == [50_000_000.0]


def test_concentracion_gasto(mini):
    # 2 pacientes: el 5 % redondea a 1 paciente, el de mayor gasto (310.000 de 499.000)
    assert an.concentracion_gasto(mini, 0.05) == pytest.approx(310_000 / 499_000)


def test_pacientes_alto_costo(resultado):
    alto = resultado.alto_costo
    assert not alto.empty
    assert alto["Gasto_Total"].is_monotonic_decreasing
