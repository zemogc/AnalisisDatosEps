"""Reglas de dependencia de la arquitectura hexagonal, verificadas sobre el código.

dominio      -> solo biblioteca estándar, numpy y pandas
aplicacion   -> dominio (nunca adaptadores ni librerías de infraestructura)
adaptadores  -> pueden usar todo lo anterior
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PAQUETE = Path(__file__).resolve().parents[1] / "src" / "eps_analytics"
INFRA = {"sqlalchemy", "pyodbc", "openpyxl", "matplotlib", "streamlit", "plotly"}


def _imports(archivo: Path) -> set[str]:
    nombres: set[str] = set()
    for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.Import):
            nombres.update(a.name for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            nombres.add(nodo.module)
    return nombres


def _modulos(capa: str) -> list[Path]:
    return sorted((PAQUETE / capa).rglob("*.py"))


def _prohibidos(capa: str, prohibidos: set[str]) -> list[str]:
    malos = []
    for archivo in _modulos(capa):
        for nombre in _imports(archivo):
            if any(nombre == p or nombre.startswith(p + ".") for p in prohibidos):
                malos.append(f"{archivo.relative_to(PAQUETE)} importa {nombre}")
    return malos


@pytest.mark.parametrize("capa", ["dominio", "aplicacion", "adaptadores"])
def test_capa_tiene_modulos(capa):
    assert _modulos(capa)


def test_dominio_es_puro():
    prohibidos = INFRA | {"eps_analytics.aplicacion", "eps_analytics.adaptadores", "eps_analytics.config"}
    assert _prohibidos("dominio", prohibidos) == []


def test_aplicacion_no_conoce_adaptadores():
    prohibidos = INFRA | {"eps_analytics.adaptadores", "eps_analytics.contenedor"}
    assert _prohibidos("aplicacion", prohibidos) == []


def test_adaptadores_cumplen_sus_puertos():
    from eps_analytics.adaptadores.persistencia import RepositorioSQL
    from eps_analytics.adaptadores.reportes import ExportadorExcel, ExportadorGraficos
    from eps_analytics.adaptadores.sinteticos import GeneradorSintetico
    from eps_analytics.aplicacion import puertos

    def metodos(protocolo) -> set[str]:
        return {n for n in vars(protocolo) if not n.startswith("_")} - {"nombre"}

    pares = [
        (RepositorioSQL, puertos.RepositorioAtenciones),
        (GeneradorSintetico, puertos.GeneradorDatos),
        (ExportadorExcel, puertos.ExportadorReporte),
        (ExportadorGraficos, puertos.ExportadorReporte),
    ]
    for adaptador, puerto in pares:
        faltan = metodos(puerto) - set(dir(adaptador))
        assert not faltan, f"{adaptador.__name__} no implementa {faltan}"
