import pandas as pd
import pytest

from eps_analytics import analysis as an
from eps_analytics import database, riesgo


@pytest.fixture(scope="module")
def datos(engine):
    return an.preparar(database.cargar_dataset(engine))


def perfil(**kwargs) -> pd.DataFrame:
    base = {"Edad": 30, "Urgencias": 0, "Consultas": 2, "Cronicas": [], "Gasto_Total": 100_000.0}
    filas = [{**base, **kwargs}] + [base] * 19  # 20 pacientes para que los percentiles tengan sentido
    return pd.DataFrame(filas, index=pd.Index(range(1, 21), name="ID_Paciente"))


def test_paciente_sano_queda_en_nivel_1():
    fila = riesgo.puntuar(perfil()).loc[1]
    assert fila["Puntaje"] == 0
    assert fila["Nivel"] == riesgo.NIVELES[0]
    assert fila["Factores"] == "Sin factores"


def test_puntaje_suma_factores_explicables():
    fila = riesgo.puntuar(
        perfil(Edad=70, Cronicas=["I10", "E11.9"], Urgencias=2, Consultas=10, Gasto_Total=9_000_000)
    ).loc[1]
    # 65+ (2) + HTA (2) + DM2 (2) + multimorbilidad (1) + 2 urgencias (2) + frecuencia (1) + top 5 % (3)
    assert fila["Puntaje"] == 13
    assert fila["Nivel"] == riesgo.NIVELES[2]
    for factor in ("65+ años", "Hipertensión", "Diabetes", "Multimorbilidad", "2 urgencias", "Gasto top 5 %"):
        assert factor in fila["Factores"]


def test_cortes_de_nivel():
    nivel_2 = riesgo.puntuar(perfil(Edad=50, Cronicas=["I10"])).loc[1]  # 1 + 2 = 3
    assert nivel_2["Puntaje"] == riesgo.CORTE_NIVEL_2
    assert nivel_2["Nivel"] == riesgo.NIVELES[1]


def test_perfil_pacientes_extrae_cronicas(datos):
    perfiles = riesgo.perfil_pacientes(datos)
    assert len(perfiles) == datos["ID_Paciente"].nunique()
    con_hta = datos.loc[datos["Codigo_CIE10"] == "I10", "ID_Paciente"].unique()
    assert all("I10" in perfiles.loc[p, "Cronicas"] for p in con_hta)
    assert perfiles["Gasto_Total"].sum() == pytest.approx(datos["Costo_Total"].sum())


def test_piramide_suma_100(datos):
    pir = riesgo.resumen_piramide(riesgo.estratificar(datos))
    assert list(pir.index) == riesgo.NIVELES
    assert pir["Participacion_Pacientes"].sum() == pytest.approx(1)
    assert pir["Participacion_Gasto"].sum() == pytest.approx(1)
    # Forma de pirámide: menos pacientes y más gasto por paciente a medida que sube el nivel
    assert pir["Pacientes"].is_monotonic_decreasing
    assert pir["Gasto_Por_Paciente"].is_monotonic_increasing


def test_validacion_prospectiva_es_monotona(datos):
    val = riesgo.validar_prospectivo(datos)
    assert val["Razon_vs_Nivel_1"].iloc[0] == pytest.approx(1)
    assert val["Gasto_Futuro_Por_Paciente"].is_monotonic_increasing


def test_validacion_no_usa_datos_futuros(datos):
    corte = pd.Timestamp("2024-07-01")
    val = riesgo.validar_prospectivo(datos, corte)
    pacientes_previos = datos.loc[datos["Fecha_Consulta"] < corte, "ID_Paciente"].nunique()
    assert val["Pacientes"].sum() == pacientes_previos
