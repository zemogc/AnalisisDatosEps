"""Capa de acceso a datos.

Define el modelo relacional (Pacientes, ConsultasMedicas, Medicamentos) con
SQLAlchemy Core para que el mismo código funcione contra SQL Server en
producción y SQLite en desarrollo/pruebas.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import (
    Column,
    Date,
    Engine,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    create_engine,
    inspect,
    text,
)

metadata = MetaData()

pacientes = Table(
    "Pacientes",
    metadata,
    Column("ID_Paciente", Integer, primary_key=True, autoincrement=False),
    Column("Nombre", String(120), nullable=False),
    Column("Edad", Integer, nullable=False),
    Column("Sexo", String(1), nullable=False),
    Column("EPS", String(60), nullable=False),
    Column("Regimen", String(20), nullable=False),
    Column("Ciudad", String(60), nullable=False),
)

consultas = Table(
    "ConsultasMedicas",
    metadata,
    Column("ID_Consulta", Integer, primary_key=True, autoincrement=False),
    Column("ID_Paciente", Integer, ForeignKey("Pacientes.ID_Paciente"), nullable=False),
    Column("Fecha_Consulta", Date, nullable=False),
    Column("Tipo_Atencion", String(30), nullable=False),
    Column("Codigo_CIE10", String(10), nullable=False),
    Column("Diagnostico", String(120), nullable=False),
    Column("Costo", Numeric(14, 2), nullable=False),
)

medicamentos = Table(
    "Medicamentos",
    metadata,
    Column("ID_Medicamento", Integer, primary_key=True, autoincrement=False),
    Column("ID_Consulta", Integer, ForeignKey("ConsultasMedicas.ID_Consulta"), nullable=False),
    Column("Nombre_Medicamento", String(120), nullable=False),
    Column("Cantidad", Integer, nullable=False),
    Column("Costo", Numeric(14, 2), nullable=False),
)

TABLAS = ("Pacientes", "ConsultasMedicas", "Medicamentos")

# Una fila por consulta. Los medicamentos se agregan ANTES del JOIN: unirlos
# directamente duplicaría el costo de la consulta por cada medicamento y
# descartaría las consultas sin fórmula médica.
CONSULTA_DATASET = text(
    """
    SELECT
        c.ID_Consulta,
        p.ID_Paciente,
        p.Nombre,
        p.Edad,
        p.Sexo,
        p.EPS,
        p.Regimen,
        p.Ciudad,
        c.Fecha_Consulta,
        c.Tipo_Atencion,
        c.Codigo_CIE10,
        c.Diagnostico,
        c.Costo                          AS Costo_Consulta,
        COALESCE(m.Num_Medicamentos, 0)  AS Num_Medicamentos,
        COALESCE(m.Costo_Medicamentos, 0) AS Costo_Medicamentos
    FROM ConsultasMedicas c
    INNER JOIN Pacientes p ON p.ID_Paciente = c.ID_Paciente
    LEFT JOIN (
        SELECT ID_Consulta,
               COUNT(*)   AS Num_Medicamentos,
               SUM(Costo) AS Costo_Medicamentos
        FROM Medicamentos
        GROUP BY ID_Consulta
    ) m ON m.ID_Consulta = c.ID_Consulta
    """
)

CONSULTA_MEDICAMENTOS = text(
    """
    SELECT
        m.ID_Medicamento,
        m.ID_Consulta,
        m.Nombre_Medicamento,
        m.Cantidad,
        m.Costo,
        p.EPS,
        c.Diagnostico,
        c.Fecha_Consulta
    FROM Medicamentos m
    INNER JOIN ConsultasMedicas c ON c.ID_Consulta = m.ID_Consulta
    INNER JOIN Pacientes p ON p.ID_Paciente = c.ID_Paciente
    """
)


def get_engine(db_url: str) -> Engine:
    """Crea el engine; para SQLite garantiza que exista la carpeta del archivo."""
    if db_url.startswith("sqlite:///") and db_url != "sqlite:///:memory:":
        Path(db_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(db_url, future=True)


def crear_esquema(engine: Engine, reset: bool = False) -> None:
    if reset:
        metadata.drop_all(engine)
    metadata.create_all(engine)


def esquema_existe(engine: Engine) -> bool:
    existentes = set(inspect(engine).get_table_names())
    return all(t in existentes for t in TABLAS)


def cargar_tablas(engine: Engine, tablas: dict[str, pd.DataFrame]) -> None:
    """Inserta DataFrames respetando el orden de las llaves foráneas."""
    with engine.begin() as conn:
        for nombre in TABLAS:
            tablas[nombre].to_sql(nombre, conn, if_exists="append", index=False, chunksize=1000)


def cargar_dataset(engine: Engine) -> pd.DataFrame:
    """Devuelve el dataset analítico a nivel de consulta."""
    with engine.connect() as conn:
        df = pd.read_sql(CONSULTA_DATASET, conn, parse_dates=["Fecha_Consulta"])
    for col in ("Costo_Consulta", "Costo_Medicamentos"):
        df[col] = df[col].astype(float)
    return df


def cargar_medicamentos(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(CONSULTA_MEDICAMENTOS, conn, parse_dates=["Fecha_Consulta"])
    df["Costo"] = df["Costo"].astype(float)
    return df
