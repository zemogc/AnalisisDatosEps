from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from eps_analytics import database, synthetic


@pytest.fixture(scope="session")
def tablas() -> dict[str, pd.DataFrame]:
    return synthetic.generar_datos(n_pacientes=300, seed=7, inicio=date(2024, 1, 1), fin=date(2024, 12, 31))


@pytest.fixture(scope="session")
def engine(tablas):
    eng = database.get_engine("sqlite:///:memory:")
    database.crear_esquema(eng)
    database.cargar_tablas(eng, tablas)
    yield eng
    eng.dispose()


@pytest.fixture
def engine_vacio():
    eng = database.get_engine("sqlite:///:memory:")
    yield eng
    eng.dispose()


@pytest.fixture
def mini_db():
    """Base mínima con valores calculables a mano."""
    eng = database.get_engine("sqlite:///:memory:")
    database.crear_esquema(eng)
    database.cargar_tablas(
        eng,
        {
            "Pacientes": pd.DataFrame(
                {
                    "ID_Paciente": [1, 2],
                    "Nombre": ["Ana Ruiz", "Luis Mora"],
                    "Edad": [34, 70],
                    "Sexo": ["F", "M"],
                    "EPS": ["Sanitas", "Nueva EPS"],
                    "Regimen": ["Contributivo", "Subsidiado"],
                    "Ciudad": ["Bogotá", "Cali"],
                }
            ),
            "ConsultasMedicas": pd.DataFrame(
                {
                    "ID_Consulta": [10, 11, 12],
                    "ID_Paciente": [1, 1, 2],
                    "Fecha_Consulta": [date(2024, 1, 5), date(2024, 2, 9), date(2024, 2, 20)],
                    "Tipo_Atencion": ["Medicina general", "Especialista", "Urgencias"],
                    "Codigo_CIE10": ["J06.9", "M54.5", "I10"],
                    "Diagnostico": ["Infección respiratoria aguda", "Lumbalgia", "Hipertensión esencial"],
                    "Costo": [50_000, 120_000, 300_000],
                }
            ),
            # Consulta 10 con dos medicamentos, 11 sin medicamentos, 12 con uno
            "Medicamentos": pd.DataFrame(
                {
                    "ID_Medicamento": [1, 2, 3],
                    "ID_Consulta": [10, 10, 12],
                    "Nombre_Medicamento": ["Acetaminofén 500 mg", "Loratadina 10 mg", "Losartán 50 mg"],
                    "Cantidad": [1, 2, 1],
                    "Costo": [5_000, 14_000, 10_000],
                }
            ),
        },
    )
    yield eng
    eng.dispose()
