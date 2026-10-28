import pytest

from eps_analytics import database


def test_dataset_una_fila_por_consulta(mini_db):
    df = database.cargar_dataset(mini_db).set_index("ID_Consulta")
    assert len(df) == 3
    # La consulta sin medicamentos no se pierde (LEFT JOIN)
    assert df.loc[11, "Num_Medicamentos"] == 0
    assert df.loc[11, "Costo_Medicamentos"] == 0


def test_costo_consulta_no_se_duplica(mini_db):
    """Regresión del JOIN original: con 2 medicamentos el costo de la consulta se sumaba 2 veces."""
    df = database.cargar_dataset(mini_db).set_index("ID_Consulta")
    assert df.loc[10, "Costo_Consulta"] == 50_000
    assert df.loc[10, "Costo_Medicamentos"] == 19_000
    assert df["Costo_Consulta"].sum() == 470_000


def test_cargar_medicamentos_incluye_contexto(mini_db):
    meds = database.cargar_medicamentos(mini_db)
    assert len(meds) == 3
    assert {"EPS", "Diagnostico", "Fecha_Consulta"} <= set(meds.columns)


def test_esquema_existe(engine, engine_vacio):
    assert database.esquema_existe(engine)
    assert not database.esquema_existe(engine_vacio)


def test_reset_recrea_tablas_vacias(tablas, engine_vacio):
    eng = engine_vacio
    database.crear_esquema(eng)
    database.cargar_tablas(eng, tablas)
    database.crear_esquema(eng, reset=True)
    assert database.cargar_dataset(eng).empty


def test_llave_primaria_duplicada_falla(tablas, engine_vacio):
    eng = engine_vacio
    database.crear_esquema(eng)
    database.cargar_tablas(eng, tablas)
    with pytest.raises(Exception):  # noqa: B017 - el tipo depende del driver
        database.cargar_tablas(eng, tablas)


def test_get_engine_crea_carpeta_sqlite(tmp_path):
    ruta = tmp_path / "anidada" / "demo.db"
    database.get_engine(f"sqlite:///{ruta.as_posix()}").dispose()
    assert ruta.parent.is_dir()
