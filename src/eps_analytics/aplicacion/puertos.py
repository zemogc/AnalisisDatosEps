"""Puertos: lo que los casos de uso necesitan del exterior, sin decir cómo se hace.

Cada puerto es un ``Protocol``; cualquier objeto con esos métodos sirve (tipado
estructural). Así los casos de uso se prueban con dobles en memoria y la base
de datos, el generador o el formato del reporte se cambian sin tocar el núcleo.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Protocol

import pandas as pd

from eps_analytics.dominio.indicadores import ResultadoAnalisis

Tablas = dict[str, pd.DataFrame]


class RepositorioAtenciones(Protocol):
    """Fuente y destino de pacientes, consultas y medicamentos."""

    def esquema_existe(self) -> bool: ...

    def tiene_datos(self) -> bool: ...

    def preparar_esquema(self) -> None:
        """Deja el esquema creado y sin registros."""

    def guardar(self, tablas: Tablas) -> None: ...

    def consultas(self) -> pd.DataFrame:
        """Dataset analítico a nivel de consulta (ver COLUMNAS_REQUERIDAS)."""

    def medicamentos(self) -> pd.DataFrame: ...

    def descripcion(self) -> str:
        """Destino legible para logs, sin credenciales."""


class GeneradorDatos(Protocol):
    def generar(self, n_pacientes: int, seed: int, inicio: date, fin: date) -> Tablas: ...


class ExportadorReporte(Protocol):
    nombre: str

    def exportar(self, res: ResultadoAnalisis, carpeta: Path) -> list[Path]: ...
