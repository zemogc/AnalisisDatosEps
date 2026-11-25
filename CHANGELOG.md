# Cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[versionado semántico](https://semver.org/lang/es/).

## [3.0.0] - 2026-11-25

### Cambiado

- Arquitectura hexagonal. El paquete se organiza en `dominio/` (indicadores, riesgo, pronóstico),
  `aplicacion/` (puertos y casos de uso) y `adaptadores/` (persistencia, generador sintético,
  reportes, formato y CLI), conectados en `contenedor.py`.
- La CLI y el dashboard dejan de hablar con la base de datos: usan los casos de uso
  `PoblarBaseDemo`, `GenerarReporte` y `CargarDatosTablero`.
- Rutas de importación nuevas, por ejemplo `eps_analytics.dominio.indicadores` (antes
  `eps_analytics.analysis`) y `eps_analytics.adaptadores.persistencia` (antes
  `eps_analytics.database`). El comando `eps-analytics` no cambia.
- Dashboard rediseñado: encabezado con el periodo y el alcance de la selección, tarjetas de
  indicadores, hallazgos clave calculados con los filtros, pestañas tipo píldora y hoja de estilos
  propia (`dashboard/estilos.css`).
- El dashboard siembra la base demo también cuando el esquema existe pero está vacío.

### Agregado

- `tests/test_arquitectura.py`: verifica las reglas de dependencia entre capas.
- `tests/test_casos_uso.py`: casos de uso probados con un repositorio en memoria.

## [2.0.0] - 2026-10-28

Reescritura completa del proyecto universitario original como un sistema de análisis instalable,
probado y documentado.

### Agregado

- Paquete `eps_analytics` con CLI: `seed`, `report` y `dashboard`.
- Capa de datos con SQLAlchemy 2.0 compatible con SQL Server y SQLite.
- Scripts T-SQL en `sql/`:
  - Esquema con restricciones `CHECK` e índices.
  - Vistas analíticas.
  - Consultas con funciones de ventana.
- Generador de datos sintéticos reproducible:
  - 8 EPS.
  - 12 diagnósticos CIE-10.
  - Condiciones crónicas persistentes por paciente.
  - Estacionalidad por temporadas de lluvia.
- Motor de indicadores:
  - KPIs y Pareto por diagnóstico.
  - Grupo etario × sexo.
  - Tendencia mensual.
  - Consultas atípicas (Tukey sobre log-costo).
  - Concentración del gasto.
- Pirámide de riesgo explicable con validación prospectiva.
- Pronóstico de costo y consultas (frecuencia × severidad) con intervalos y backtest.
- Reporte Excel de 14 hojas con gráficos nativos y 8 gráficos PNG.
- Dashboard en Streamlit + Plotly con filtros y 7 pestañas.
- Entorno Docker Compose con SQL Server 2022.
- 63 pruebas automatizadas (98 % de cobertura) y 2 pruebas de integración con SQL Server.

### Corregido

- La consulta original unía `Medicamentos` directamente. Eso duplicaba el costo de la consulta por
  cada medicamento y excluía las consultas sin fórmula médica.

### Eliminado

- Archivos generados que estaban versionados: `__pycache__`, `.xlsx` y `.png` de salida.

## [1.0.0] - 2025-01-26

- Versión académica inicial: consulta a SQL Server, promedio y desviación estándar de costos,
  exportación a Excel y dos gráficos.

[2.0.0]: https://github.com/zemogc/AnalisisDatosEps/compare/acc7cb4...v2.0.0
[1.0.0]: https://github.com/zemogc/AnalisisDatosEps/tree/acc7cb4
