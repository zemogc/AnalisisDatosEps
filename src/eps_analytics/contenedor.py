"""Raíz de composición: el único lugar que conecta casos de uso con adaptadores."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from eps_analytics.adaptadores.persistencia import RepositorioSQL
from eps_analytics.adaptadores.reportes import ExportadorExcel, ExportadorGraficos
from eps_analytics.adaptadores.sinteticos import GeneradorSintetico
from eps_analytics.aplicacion.casos_uso import (
    AnalizarCostos,
    CargarDatosTablero,
    GenerarReporte,
    PoblarBaseDemo,
)
from eps_analytics.config import Settings, load_settings


@dataclass
class Contenedor:
    repositorio: RepositorioSQL

    @property
    def poblar_base(self) -> PoblarBaseDemo:
        return PoblarBaseDemo(self.repositorio, GeneradorSintetico())

    @property
    def analizar(self) -> AnalizarCostos:
        return AnalizarCostos(self.repositorio)

    @property
    def generar_reporte(self) -> GenerarReporte:
        return GenerarReporte(self.analizar, [ExportadorExcel(), ExportadorGraficos()])

    def cargar_tablero(self, sembrar_si_vacia: bool = False) -> CargarDatosTablero:
        return CargarDatosTablero(self.repositorio, self.poblar_base if sembrar_si_vacia else None)


@contextmanager
def contenedor(settings: Settings | None = None) -> Iterator[Contenedor]:
    repo = RepositorioSQL.desde_url((settings or load_settings()).db_url)
    try:
        yield Contenedor(repo)
    finally:
        repo.cerrar()
