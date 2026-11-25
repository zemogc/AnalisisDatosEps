"""Casos de uso: orquestan el dominio a través de los puertos.

No importan adaptadores: reciben sus dependencias en el constructor y el
contenedor (``eps_analytics.contenedor``) decide qué implementación usar.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from eps_analytics.aplicacion.puertos import ExportadorReporte, GeneradorDatos, RepositorioAtenciones, Tablas
from eps_analytics.dominio import indicadores
from eps_analytics.dominio.indicadores import ResultadoAnalisis


class BaseConDatos(RuntimeError):
    """La base ya tiene datos y no se pidió reemplazarlos."""


class BaseSinDatos(RuntimeError):
    """No hay datos que analizar."""


@dataclass(frozen=True)
class ParametrosDemo:
    n_pacientes: int = 2_000
    seed: int = 42
    inicio: date = date(2024, 1, 1)
    fin: date = date(2025, 12, 31)


@dataclass
class PoblarBaseDemo:
    repositorio: RepositorioAtenciones
    generador: GeneradorDatos

    def ejecutar(self, parametros: ParametrosDemo = ParametrosDemo(), reemplazar: bool = False) -> Tablas:
        if self.repositorio.tiene_datos() and not reemplazar:
            raise BaseConDatos("La base ya tiene datos. Usa --reset para regenerarla.")
        tablas = self.generador.generar(
            parametros.n_pacientes, parametros.seed, parametros.inicio, parametros.fin
        )
        self.repositorio.preparar_esquema()
        self.repositorio.guardar(tablas)
        return tablas


@dataclass
class AnalizarCostos:
    repositorio: RepositorioAtenciones
    horizonte: int = 6

    def ejecutar(self) -> ResultadoAnalisis:
        if not self.repositorio.tiene_datos():
            raise BaseSinDatos("La base no tiene datos. Ejecuta primero: eps-analytics seed")
        return indicadores.ejecutar_analisis(
            self.repositorio.consultas(), self.repositorio.medicamentos(), self.horizonte
        )


@dataclass
class ReporteGenerado:
    resultado: ResultadoAnalisis
    archivos: dict[str, list[Path]] = field(default_factory=dict)


@dataclass
class GenerarReporte:
    analizar: AnalizarCostos
    exportadores: Sequence[ExportadorReporte]

    def ejecutar(self, carpeta: Path) -> ReporteGenerado:
        res = self.analizar.ejecutar()
        reporte = ReporteGenerado(res)
        for exportador in self.exportadores:
            reporte.archivos[exportador.nombre] = exportador.exportar(res, carpeta)
        return reporte


@dataclass
class CargarDatosTablero:
    """Datos del dashboard; si la base está vacía y se permite, la puebla con la demo."""

    repositorio: RepositorioAtenciones
    poblar: PoblarBaseDemo | None = None

    def ejecutar(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        if not self.repositorio.tiene_datos():
            if self.poblar is None:
                raise BaseSinDatos("La base no tiene datos. Ejecuta primero: eps-analytics seed")
            self.poblar.ejecutar()
        return indicadores.preparar(self.repositorio.consultas()), self.repositorio.medicamentos()
