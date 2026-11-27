"""Adaptadores de salida para reportes: libro Excel y gráficos PNG."""

from eps_analytics.adaptadores.reportes.excel import ExportadorExcel, generar_excel
from eps_analytics.adaptadores.reportes.graficos import ExportadorGraficos, generar_graficos

__all__ = ["ExportadorExcel", "ExportadorGraficos", "generar_excel", "generar_graficos"]
