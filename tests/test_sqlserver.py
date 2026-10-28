r"""Pruebas de integración contra un SQL Server real.

Se omiten salvo que ``EPS_TEST_MSSQL_URL`` apunte a una base desechable con el
esquema de ``sql/01_schema.sql`` (sus datos se reemplazan). Con Docker:

    docker compose up -d
    docker compose run --rm -v ./tests:/app/tests --entrypoint "" app sh -c \
      'pip install pytest && EPS_TEST_MSSQL_URL="$EPS_DB_URL" pytest tests/test_sqlserver.py'
"""

import os
from datetime import date

import pytest

from eps_analytics import database, synthetic
from eps_analytics.analysis import ejecutar_analisis

URL = os.getenv("EPS_TEST_MSSQL_URL")
pytestmark = pytest.mark.skipif(not URL, reason="EPS_TEST_MSSQL_URL no definida")


@pytest.fixture(scope="module")
def tablas():
    return synthetic.generar_datos(n_pacientes=150, seed=11, inicio=date(2024, 1, 1), fin=date(2024, 12, 31))


@pytest.fixture(scope="module")
def mssql(tablas):
    eng = database.get_engine(URL)
    assert database.esquema_existe(eng), "Ejecuta sql/01_schema.sql antes de estas pruebas"
    database.vaciar_tablas(eng)
    database.cargar_tablas(eng, tablas)
    yield eng
    eng.dispose()


@pytest.fixture(scope="module")
def sqlite(tablas):
    eng = database.get_engine("sqlite:///:memory:")
    database.crear_esquema(eng)
    database.cargar_tablas(eng, tablas)
    yield eng
    eng.dispose()


def test_mismos_kpis_en_sql_server_y_sqlite(mssql, sqlite):
    a = ejecutar_analisis(database.cargar_dataset(mssql), database.cargar_medicamentos(mssql))
    b = ejecutar_analisis(database.cargar_dataset(sqlite), database.cargar_medicamentos(sqlite))
    assert a.kpis == pytest.approx(b.kpis)
    assert a.por_eps["Costo_Total"].to_dict() == pytest.approx(b.por_eps["Costo_Total"].to_dict())


def test_restricciones_check_del_esquema_tsql(mssql, tablas):
    pacientes = tablas["Pacientes"].head(1).assign(ID_Paciente=999_999, Sexo="X")
    with pytest.raises(Exception, match="CK_Pacientes_Sexo"):  # noqa: B017
        pacientes.to_sql("Pacientes", mssql, if_exists="append", index=False)
