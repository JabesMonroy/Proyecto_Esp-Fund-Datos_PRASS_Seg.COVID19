"""utils.py — Funciones reutilizables del proyecto PRASS.

Configuración, rutas y carga de datos. La lógica de limpieza concreta
se implementará en la etapa de preprocesamiento (ver TODOs).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv es opcional en tiempo de ejecución
    pass

# --- Rutas base -----------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

DATA_RAW = Path(os.getenv("DATA_RAW", DATA_DIR / "SegCovid19-Seguimiento_PRASS.csv"))
DATA_PROCESSED = Path(os.getenv("DATA_PROCESSED", DATA_DIR / "processed.parquet"))

# Esquema esperado del CSV crudo (12 columnas, separador coma, UTF-8).
COLUMNAS = [
    "Fuente",
    "FechaRegistro",
    "FechaRegistroSemana",
    "Departamento",
    "Municipio",
    "EntidadRegistro",
    "NumeroCasos",
    "NumeroCasosSinSeguimiento",
    "NumeroCasosConSeguimiento",
    "PorcentajeCasosSinSeguimiento",
    "PorcentajeCasosConSeguimiento",
    "FechaCorte",
]


# --- Logging --------------------------------------------------------------
def get_logger(name: str = "prass") -> logging.Logger:
    """Devuelve un logger configurado según LOG_LEVEL."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    return logger


# --- Carga de datos -------------------------------------------------------
def cargar_crudo(path: Path | str = DATA_RAW):
    """Carga el CSV crudo de forma tolerante a filas desalineadas.

    El archivo tiene ~2,3 % de filas con comas sin escapar dentro de campos
    de texto (ver DATABASE.md). Se usa el motor de Python para saltar/avisar
    sobre líneas problemáticas sin interrumpir la carga.
    """
    import pandas as pd  # import perezoso: arranque más rápido del CLI

    log = get_logger()
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el dato crudo: {path}")

    log.info("Cargando %s", path)
    df = pd.read_csv(
        path,
        sep=",",
        encoding="utf-8",
        engine="python",
        on_bad_lines="warn",
    )
    log.info("Cargado: %d filas x %d columnas", len(df), df.shape[1])
    return df


# --- Helpers de preprocesamiento (a implementar en la etapa 1) ------------
# TODO(preprocesamiento): separar `Departamento`/`Municipio` en *_codigo y *_nombre.
# TODO(preprocesamiento): parsear `FechaRegistro` ("MM/DD/YYYY ...") y `FechaCorte`.
# TODO(preprocesamiento): recalcular porcentajes desde los conteos
#     (las columnas Porcentaje* vienen corruptas; ver DATABASE.md).
