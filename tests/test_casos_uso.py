"""Casos de uso con dobles en memoria: sin base de datos ni archivos."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from eps_analytics.adaptadores import sinteticos
from eps_analytics.aplicacion.casos_uso import (
    AnalizarCostos,
    BaseConDatos,
    BaseSinDatos,
    CargarDatosTablero,
    GenerarReporte,
    ParametrosDemo,
    PoblarBaseDemo,
)


class RepoMemoria:
    """Cumple RepositorioAtenciones guardando las tablas en un dict."""

    def __init__(self, tablas: dict[str, pd.DataFrame] | None = None) -> None:
        self.tablas = tablas or {}
        self.esquema = bool(tablas)

    def esquema_existe(self) -> bool:
        return self.esquema

    def tiene_datos(self) -> bool:
        return bool(self.tablas) and not self.tablas["Pacientes"].empty

    def preparar_esquema(self) -> None:
        self.esquema, self.tablas = True, {}

    def guardar(self, tablas):
        self.tablas = tablas

    def consultas(self) -> pd.DataFrame:
        t = self.tablas
        meds = t["Medicamentos"].groupby("ID_Consulta")["Costo"].sum().rename("Costo_Medicamentos")
        df = (
            t["ConsultasMedicas"]
            .merge(t["Pacientes"], on="ID_Paciente")
            .merge(meds, left_on="ID_Consulta", right_index=True, how="left")
        )
        df = df.rename(columns={"Costo": "Costo_Consulta"}).fillna({"Costo_Medicamentos": 0.0})
        df["Fecha_Consulta"] = pd.to_datetime(df["Fecha_Consulta"])
        return df

    def medicamentos(self) -> pd.DataFrame:
        c = self.tablas["ConsultasMedicas"][["ID_Consulta", "Fecha_Consulta"]]
        return (
            self.tablas["Medicamentos"]
            .merge(c, on="ID_Consulta")
            .assign(Fecha_Consulta=lambda d: pd.to_datetime(d["Fecha_Consulta"]))
        )

    def descripcion(self) -> str:
        return "memoria"


class GeneradorContado(sinteticos.GeneradorSintetico):
    def __init__(self) -> None:
        self.llamadas = 0

    def generar(self, *args, **kwargs):
        self.llamadas += 1
        return super().generar(*args, **kwargs)


class ExportadorFalso:
    nombre = "Falso"

    def __init__(self) -> None:
        self.recibido = None

    def exportar(self, res, carpeta: Path) -> list[Path]:
        self.recibido = res
        return [carpeta / "falso.txt"]


DEMO = ParametrosDemo(n_pacientes=120, seed=3, inicio=date(2024, 1, 1), fin=date(2024, 12, 31))


def test_poblar_llena_repositorio_vacio():
    repo = RepoMemoria()
    tablas = PoblarBaseDemo(repo, sinteticos.GeneradorSintetico()).ejecutar(DEMO)
    assert repo.tiene_datos()
    assert len(tablas["Pacientes"]) == 120


def test_poblar_no_pisa_datos_sin_reemplazar():
    repo = RepoMemoria()
    gen = GeneradorContado()
    caso = PoblarBaseDemo(repo, gen)
    caso.ejecutar(DEMO)
    with pytest.raises(BaseConDatos):
        caso.ejecutar(DEMO)
    caso.ejecutar(DEMO, reemplazar=True)
    assert gen.llamadas == 2


def test_analizar_sin_datos_falla():
    with pytest.raises(BaseSinDatos):
        AnalizarCostos(RepoMemoria()).ejecutar()


def test_generar_reporte_pasa_resultado_a_cada_exportador(tmp_path):
    repo = RepoMemoria()
    PoblarBaseDemo(repo, sinteticos.GeneradorSintetico()).ejecutar(DEMO)
    a, b = ExportadorFalso(), ExportadorFalso()
    b.nombre = "Otro"
    reporte = GenerarReporte(AnalizarCostos(repo), [a, b]).ejecutar(tmp_path)
    assert a.recibido is reporte.resultado and b.recibido is reporte.resultado
    assert reporte.archivos == {"Falso": [tmp_path / "falso.txt"], "Otro": [tmp_path / "falso.txt"]}
    assert reporte.resultado.kpis["pacientes"] > 0


def test_tablero_siembra_solo_si_se_permite():
    with pytest.raises(BaseSinDatos):
        CargarDatosTablero(RepoMemoria()).ejecutar()
    repo = RepoMemoria()
    datos, meds = CargarDatosTablero(repo, PoblarBaseDemo(repo, sinteticos.GeneradorSintetico())).ejecutar()
    assert "Grupo_Etario" in datos.columns
    assert not meds.empty
