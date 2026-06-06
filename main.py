"""main.py — Punto de entrada del proyecto PRASS (Seguimiento COVID-19).

Orquesta el pipeline por etapas mediante subcomandos. Solo `preprocess`
está habilitado (en construcción); el resto son marcadores de posición.

Uso:
    python main.py preprocess [--input PATH] [--output PATH]
    python main.py eda | viz | model
"""
from __future__ import annotations

import argparse
import sys

import utils


def cmd_preprocess(args: argparse.Namespace) -> int:
    """Etapa 1 — Preprocesamiento (EN CONSTRUCCIÓN).

    Por ahora solo carga el dato crudo y reporta su forma. La limpieza
    concreta se implementará a continuación (ver TODOs en utils.py y
    DATABASE.md para los problemas de calidad detectados).
    """
    log = utils.get_logger()
    df = utils.cargar_crudo(args.input)

    log.info("Columnas: %s", list(df.columns))
    log.info("Vista previa:\n%s", df.head().to_string())

    log.warning(
        "Limpieza aún no implementada. Próximos pasos: porcentajes, "
        "fechas y separación de código/nombre (ver DATABASE.md)."
    )
    return 0


def cmd_pendiente(args: argparse.Namespace) -> int:
    """Etapas 2-4 — aún no implementadas."""
    utils.get_logger().warning(
        "La etapa '%s' todavía no está implementada.", args.etapa
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py", description="Pipeline PRASS — Seguimiento COVID-19."
    )
    sub = parser.add_subparsers(dest="etapa", required=True)

    p = sub.add_parser("preprocess", help="Etapa 1: limpieza/normalización (en curso)")
    p.add_argument("--input", default=utils.DATA_RAW, help="CSV crudo de entrada")
    p.add_argument("--output", default=utils.DATA_PROCESSED, help="Salida procesada")
    p.set_defaults(func=cmd_preprocess)

    for etapa, ayuda in [
        ("eda", "Etapa 2: análisis exploratorio (pendiente)"),
        ("viz", "Etapa 3: visualizaciones (pendiente)"),
        ("model", "Etapa 4: modelado (pendiente)"),
    ]:
        ps = sub.add_parser(etapa, help=ayuda)
        ps.set_defaults(func=cmd_pendiente)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
