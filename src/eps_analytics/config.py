"""Configuración de la aplicación a partir de variables de entorno.

Variables soportadas:

- ``EPS_DB_URL``: URL de conexión SQLAlchemy. Por defecto usa una base SQLite
  local con datos sintéticos. Ejemplo SQL Server (autenticación Windows)::

      mssql+pyodbc://@localhost/ProyectoEPS?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes

- ``EPS_OUTPUT_DIR``: carpeta donde se escriben los reportes (``output`` por defecto).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "data" / "eps_demo.db"


@dataclass(frozen=True)
class Settings:
    db_url: str
    output_dir: Path

    @property
    def is_sqlite(self) -> bool:
        return self.db_url.startswith("sqlite")


def load_settings() -> Settings:
    db_url = os.getenv("EPS_DB_URL") or f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
    output_dir = Path(os.getenv("EPS_OUTPUT_DIR") or PROJECT_ROOT / "output")
    return Settings(db_url=db_url, output_dir=output_dir)
