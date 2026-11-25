"""Interfaz de línea de comandos.

eps-analytics seed --pacientes 2000 --seed 42   # crea/llena la base demo
eps-analytics report                            # genera Excel + gráficos
eps-analytics dashboard                         # abre el dashboard web
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import date
from pathlib import Path

from eps_analytics import __version__
from eps_analytics.adaptadores import formato as fmt
from eps_analytics.aplicacion.casos_uso import BaseConDatos, BaseSinDatos, ParametrosDemo
from eps_analytics.config import PROJECT_ROOT, load_settings
from eps_analytics.contenedor import contenedor

log = logging.getLogger("eps_analytics")


def _seed(args: argparse.Namespace) -> int:
    parametros = ParametrosDemo(
        n_pacientes=args.pacientes,
        seed=args.seed,
        inicio=date.fromisoformat(args.desde),
        fin=date.fromisoformat(args.hasta),
    )
    with contenedor() as app:
        try:
            tablas = app.poblar_base.ejecutar(parametros, reemplazar=args.reset)
        except BaseConDatos as error:
            log.error("%s", error)
            return 1
        destino = app.repositorio.descripcion()
    resumen = ", ".join(f"{k}: {fmt.numero(len(v))}" for k, v in tablas.items())
    log.info("Base poblada en %s (%s)", destino, resumen)
    return 0


def _report(args: argparse.Namespace) -> int:
    salida = Path(args.output) if args.output else load_settings().output_dir
    with contenedor() as app:
        try:
            reporte = app.generar_reporte.ejecutar(salida)
        except BaseSinDatos as error:
            log.error("%s", error)
            return 1

    res = reporte.resultado
    k = res.kpis
    log.info("Pacientes: %s | Consultas: %s", fmt.numero(k["pacientes"]), fmt.numero(k["consultas"]))
    log.info(
        "Costo total: %s | Promedio/consulta: %s | Mediana/consulta: %s",
        fmt.cop(k["costo_total"]),
        fmt.cop(k["costo_promedio_consulta"]),
        fmt.cop(k["costo_mediano_consulta"]),
    )
    log.info(
        "El 5 %% de pacientes más costosos concentra %s del gasto", fmt.porcentaje(res.concentracion_top5)
    )
    log.info("Consultas atípicas detectadas: %d", len(res.atipicos))
    nivel_3 = res.piramide.iloc[-1]
    log.info(
        "Pirámide de riesgo: nivel 3 = %s de los pacientes y %s del gasto",
        fmt.porcentaje(nivel_3["Participacion_Pacientes"]),
        fmt.porcentaje(nivel_3["Participacion_Gasto"]),
    )
    if res.pronostico:
        costo = res.pronostico["Costo_Total"]
        log.info(
            "Costo pronosticado próximos %d meses: %s",
            len(costo.tabla),
            fmt.cop(costo.tabla["Pronostico"].sum()),
        )
        if costo.mape_modelo is not None:
            log.info(
                "Backtest costo: MAPE %s (ingenuo estacional %s)",
                fmt.porcentaje(costo.mape_modelo),
                fmt.porcentaje(costo.mape_ingenuo),
            )
    for tipo, rutas in reporte.archivos.items():
        for ruta in rutas:
            log.info("%s: %s", tipo, ruta)
    return 0


def _dashboard(args: argparse.Namespace) -> int:
    app = PROJECT_ROOT / "dashboard" / "app.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(app), "--server.port", str(args.port)]
    return subprocess.call(cmd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eps-analytics", description="Análisis de costos de atención en salud por EPS."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Muestra logs de depuración")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_seed = sub.add_parser("seed", help="Genera datos sintéticos y los carga en la base")
    p_seed.add_argument("--pacientes", type=int, default=2000)
    p_seed.add_argument("--seed", type=int, default=42, help="Semilla aleatoria (reproducible)")
    p_seed.add_argument("--desde", default="2024-01-01", help="Fecha inicial (AAAA-MM-DD)")
    p_seed.add_argument("--hasta", default="2025-12-31", help="Fecha final (AAAA-MM-DD)")
    p_seed.add_argument("--reset", action="store_true", help="Reemplaza los datos existentes")
    p_seed.set_defaults(func=_seed)

    p_rep = sub.add_parser("report", help="Genera el reporte Excel y los gráficos")
    p_rep.add_argument("-o", "--output", help="Carpeta de salida (por defecto ./output)")
    p_rep.set_defaults(func=_report)

    p_dash = sub.add_parser("dashboard", help="Inicia el dashboard interactivo (Streamlit)")
    p_dash.add_argument("--port", type=int, default=8501)
    p_dash.set_defaults(func=_dashboard)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
