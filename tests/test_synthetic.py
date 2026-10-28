from datetime import date

import pandas as pd
import pytest

from eps_analytics import synthetic


def test_misma_semilla_mismos_datos():
    a = synthetic.generar_datos(n_pacientes=50, seed=1)
    b = synthetic.generar_datos(n_pacientes=50, seed=1)
    for nombre in a:
        pd.testing.assert_frame_equal(a[nombre], b[nombre])


def test_semillas_distintas_datos_distintos():
    a = synthetic.generar_datos(n_pacientes=50, seed=1)["ConsultasMedicas"]
    b = synthetic.generar_datos(n_pacientes=50, seed=2)["ConsultasMedicas"]
    assert not a.equals(b)


def test_integridad_referencial(tablas):
    pacientes, consultas, meds = tablas["Pacientes"], tablas["ConsultasMedicas"], tablas["Medicamentos"]
    assert pacientes["ID_Paciente"].is_unique
    assert consultas["ID_Consulta"].is_unique
    assert meds["ID_Medicamento"].is_unique
    assert consultas["ID_Paciente"].isin(pacientes["ID_Paciente"]).all()
    assert meds["ID_Consulta"].isin(consultas["ID_Consulta"]).all()


def test_dominios_validos(tablas):
    p, c, m = tablas["Pacientes"], tablas["ConsultasMedicas"], tablas["Medicamentos"]
    assert p["Edad"].between(0, 120).all()
    assert set(p["Sexo"]) <= {"F", "M"}
    assert set(p["EPS"]) <= set(synthetic.EPS)
    assert set(p["Regimen"]) <= {"Contributivo", "Subsidiado"}
    assert (c["Costo"] > 0).all()
    assert (m["Costo"] > 0).all() and (m["Cantidad"] > 0).all()
    fechas = pd.to_datetime(c["Fecha_Consulta"])
    assert fechas.min() >= pd.Timestamp("2024-01-01")
    assert fechas.max() <= pd.Timestamp("2024-12-31")


def test_todo_paciente_tiene_al_menos_una_consulta(tablas):
    assert set(tablas["Pacientes"]["ID_Paciente"]) == set(tablas["ConsultasMedicas"]["ID_Paciente"])


def test_coherencia_clinica(tablas):
    datos = tablas["ConsultasMedicas"].merge(tablas["Pacientes"], on="ID_Paciente")
    cancer_mama = datos[datos["Codigo_CIE10"] == "C50.9"]
    assert (cancer_mama["Sexo"] == "F").all()
    cronicas = datos[datos["Codigo_CIE10"].isin(["I10", "E11.9", "I25.1"])]
    assert (cronicas["Edad"] >= 18).all()


@pytest.mark.parametrize(
    "kwargs",
    [{"n_pacientes": 0}, {"inicio": date(2025, 1, 1), "fin": date(2024, 1, 1)}],
)
def test_parametros_invalidos(kwargs):
    with pytest.raises(ValueError):
        synthetic.generar_datos(**kwargs)
