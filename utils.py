"""utils.py — Funciones reutilizables del proyecto PRASS.

Carga del dataset y transformaciones de preprocesamiento. Este módulo se importa
desde el cuaderno `Proyecto_PRASS_Seguimiento_COVID19.ipynb` para evitar duplicar
código y mantener el análisis legible.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RUTA_DATOS = "data/SegCovid19-Seguimiento_PRASS.csv"


def cargar_datos(ruta: str | Path = RUTA_DATOS) -> pd.DataFrame:
    """Carga el CSV crudo. El lector por defecto respeta el entrecomillado
    (RFC 4180), por lo que las comas internas de los nombres no desalinean."""
    return pd.read_csv(ruta)


def separar_codigo_nombre(serie: pd.Series) -> pd.DataFrame:
    """Divide un campo con formato 'codigo - NOMBRE' en columnas independientes
    `codigo` y `nombre`. Solo separa en el primer ' - '."""
    partes = serie.astype(str).str.split(" - ", n=1, expand=True)
    return pd.DataFrame(
        {"codigo": partes[0].str.strip(), "nombre": partes[1].str.strip()}
    )


def parsear_fecha(serie: pd.Series) -> pd.Series:
    """Convierte 'MM/DD/AAAA hh:mm:ss AM/PM' a fecha (a medianoche, sin hora)."""
    return pd.to_datetime(serie, format="%m/%d/%Y %I:%M:%S %p").dt.normalize()


def estandarizar_texto(serie: pd.Series) -> pd.Series:
    """Recorta espacios en los bordes y colapsa espacios múltiples internos."""
    return serie.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)


def agregar_cobertura(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega la cobertura de seguimiento (%) recalculada desde los conteos,
    en reemplazo de las columnas de porcentaje corruptas del origen."""
    df = df.copy()
    df["CoberturaConSeguimiento"] = (
        df["NumeroCasosConSeguimiento"] / df["NumeroCasos"] * 100
    ).round(2)
    df["CoberturaSinSeguimiento"] = (
        df["NumeroCasosSinSeguimiento"] / df["NumeroCasos"] * 100
    ).round(2)
    return df


def preprocesar(df: pd.DataFrame) -> pd.DataFrame:
    """Pipeline completo de preprocesamiento del dato PRASS.

    Aplica, en orden: tipado de fecha, separación de código y nombre
    territorial, estandarización de texto, recálculo de cobertura y eliminación
    de columnas constantes o corruptas. Devuelve un nuevo DataFrame.
    """
    df = df.copy()
    df["FechaRegistro"] = parsear_fecha(df["FechaRegistro"])
    for col in ("Departamento", "Municipio"):
        cn = separar_codigo_nombre(df[col])
        df[f"{col}Codigo"] = cn["codigo"]
        df[f"{col}Nombre"] = cn["nombre"]
    df["EntidadRegistro"] = estandarizar_texto(df["EntidadRegistro"])
    df = agregar_cobertura(df)
    df = df.drop(
        columns=[
            "FechaCorte",
            "PorcentajeCasosSinSeguimiento",
            "PorcentajeCasosConSeguimiento",
            "Departamento",
            "Municipio",
        ]
    )
    return df
