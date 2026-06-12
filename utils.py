"""utils.py — Funciones reutilizables del proyecto PRASS.

Carga del dataset y transformaciones de preprocesamiento. Este módulo se importa
desde el cuaderno `Proyecto_PRASS_Seguimiento_COVID19.ipynb` para evitar duplicar
código y mantener el análisis legible.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

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


# Variables de baja cardinalidad que se tratan como categóricas.
COLS_CATEGORIA = (
    "Fuente",
    "EntidadRegistro",
    "DepartamentoCodigo",
    "DepartamentoNombre",
    "MunicipioCodigo",
    "MunicipioNombre",
)
# Códigos DIVIPOLA: son identificadores (conservan ceros a la izquierda), no
# magnitudes; no deben convertirse a tipo numérico.
COLS_IDENTIFICADOR = ("DepartamentoCodigo", "MunicipioCodigo")


def diagnosticar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    """Para cada columna no numérica y no fecha, informa si su contenido es
    convertible a número y si corresponde a un identificador. Sirve para
    detectar numéricas mal tipadas como texto sin convertir códigos por error."""
    filas = []
    for c in df.select_dtypes(exclude=["number", "datetime"]).columns:
        convertible = bool(pd.to_numeric(df[c], errors="coerce").notna().all())
        filas.append(
            {
                "columna": c,
                "dtype": str(df[c].dtype),
                "convertible_a_numerico": convertible,
                "es_identificador": c in COLS_IDENTIFICADOR,
            }
        )
    return pd.DataFrame(filas)


def tipar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte a `category` las variables de baja cardinalidad y trata la
    semana epidemiológica como categoría ordinal (1..53). Los identificadores
    permanecen como categoría textual, no como número."""
    df = df.copy()
    for c in COLS_CATEGORIA:
        if c in df.columns:
            df[c] = df[c].astype("category")
    if "FechaRegistroSemana" in df.columns:
        semanas = sorted(df["FechaRegistroSemana"].unique())
        df["FechaRegistroSemana"] = df["FechaRegistroSemana"].astype(
            pd.CategoricalDtype(categories=semanas, ordered=True)
        )
    return df


def cobertura_ponderada(
    df: pd.DataFrame, por, min_casos: int = 0
) -> pd.DataFrame:
    """Cobertura de seguimiento (%) por grupo, ponderada por casos:
    `sum(ConSeguimiento) / sum(NumeroCasos)`. Filtra grupos con menos de
    `min_casos` y devuelve el resultado ordenado de menor a mayor cobertura."""
    g = (
        df.groupby(por, observed=True)
        .agg(casos=("NumeroCasos", "sum"), con=("NumeroCasosConSeguimiento", "sum"))
        .reset_index()
    )
    g = g[g["casos"] >= min_casos]
    g["CoberturaPct"] = (g["con"] / g["casos"] * 100).round(2)
    return g.sort_values("CoberturaPct").reset_index(drop=True)


def preprocesar(df: pd.DataFrame) -> pd.DataFrame:
    """Pipeline completo de preprocesamiento del dato PRASS.

    Aplica, en orden: tipado de fecha, separación de código y nombre
    territorial, estandarización de texto, recálculo de cobertura, eliminación
    de columnas constantes o corruptas y tipado de categóricas. Devuelve un
    nuevo DataFrame.
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
    df = tipar_columnas(df)
    return df


# --------------------------------------------------------------------------- #
# Modelado: GLM binomial de la cobertura de seguimiento (Parte IV)
# --------------------------------------------------------------------------- #
# Variables empleadas como predictores del modelo base. Se excluye `Municipio`
# por su alta cardinalidad (1.121 niveles), que haría inviable la codificación
# dummy; el territorio se representa con `DepartamentoNombre`.
PREDICTORES_CATEGORICOS = ("Fuente", "DepartamentoNombre", "EntidadRegistro")
PREDICTORES_NUMERICOS = ("FechaRegistroSemana",)


def construir_diseno_glm(
    df: pd.DataFrame,
    categoricas=PREDICTORES_CATEGORICOS,
    numericas=PREDICTORES_NUMERICOS,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Construye la matriz de diseño y la respuesta binomial para el GLM.

    La respuesta no es el porcentaje de cobertura sino la pareja de conteos
    `(NumeroCasosConSeguimiento, NumeroCasosSinSeguimiento)`, que statsmodels
    interpreta como datos binomiales agrupados: de los `NumeroCasos` de cada
    grupo, una parte recibió seguimiento. Así el tamaño del grupo pondera de
    forma natural y la probabilidad estimada permanece en `[0, 1]`, lo que evita
    el problema de la distribución saturada en 100 %.

    Las categóricas se codifican como variables dummy (`drop_first=True` para
    eliminar la colinealidad con el intercepto) y las numéricas se incorporan tal
    cual. Se antepone la constante.

    Returns:
        X: matriz de diseño (con intercepto), `DataFrame` de columnas nombradas.
        y: arreglo de dos columnas `[exitos, fracasos]`.
    """
    X = pd.get_dummies(df[list(categoricas)], drop_first=True, dtype=float)
    for c in numericas:
        X[c] = df[c].astype(str).astype(float).to_numpy()
    X = sm.add_constant(X)
    y = df[["NumeroCasosConSeguimiento", "NumeroCasosSinSeguimiento"]].to_numpy(
        dtype=float
    )
    return X, y


def ajustar_glm_binomial(X: pd.DataFrame, y: np.ndarray):
    """Ajusta un GLM binomial con enlace logit (regresión logística agregada).

    Devuelve el objeto de resultados de statsmodels, del que se obtienen
    coeficientes, errores estándar, p-valores, devianza y diagnósticos.
    """
    modelo = sm.GLM(y, X, family=sm.families.Binomial())
    return modelo.fit()


def estadistico_dispersion(res) -> float:
    """Estadístico de dispersión: chi-cuadrado de Pearson sobre los grados de
    libertad residuales. Un valor cercano a 1 es consistente con el supuesto
    binomial; valores notablemente mayores que 1 indican sobredispersión (la
    varianza observada excede la binomial) y sugieren pasar a quasi-binomial,
    beta-binomial o a un modelo con efectos aleatorios.
    """
    return float(res.pearson_chi2 / res.df_resid)


def pseudo_r2_deviance(res) -> float:
    """Pseudo-R2 basado en devianza: `1 - devianza_modelo / devianza_nula`.
    Resume cuánta devianza del modelo nulo explica el modelo ajustado.
    """
    return float(1 - res.deviance / res.null_deviance)


def tabla_odds_ratios(res) -> pd.DataFrame:
    """Tabla de odds ratios por término: `exp(coeficiente)`, su intervalo de
    confianza al 95 % y el p-valor. Un odds ratio menor que 1 indica menor
    probabilidad de seguimiento frente a la categoría de referencia; mayor que 1,
    mayor probabilidad. Ordena de menor a mayor odds ratio.
    """
    ci = res.conf_int()
    tab = pd.DataFrame(
        {
            "odds_ratio": np.exp(res.params),
            "ic_2.5%": np.exp(ci[0]),
            "ic_97.5%": np.exp(ci[1]),
            "p_valor": res.pvalues,
        }
    )
    return tab.sort_values("odds_ratio")


def brier_ponderado(df: pd.DataFrame, p_pred: np.ndarray) -> float:
    """Brier score a nivel de caso para una predicción de probabilidad por grupo.

    Cada grupo aporta `NumeroCasosConSeguimiento` casos con resultado 1 y el resto
    con resultado 0, todos con la misma probabilidad predicha `p`. El Brier es el
    error cuadrático medio por caso; valores menores indican mejor calibración.
    """
    n = df["NumeroCasos"].to_numpy(float)
    k = df["NumeroCasosConSeguimiento"].to_numpy(float)
    sse = k * (1 - p_pred) ** 2 + (n - k) * p_pred**2
    return float(sse.sum() / n.sum())


def expandir_a_casos(df: pd.DataFrame, p_pred: np.ndarray):
    """Expande los grupos a nivel de caso para la evaluación binaria.

    Cada grupo aporta `NumeroCasosConSeguimiento` casos con resultado 1 (seguido) y
    `NumeroCasosSinSeguimiento` con resultado 0, todos con la misma probabilidad
    predicha `p`. Para no materializar millones de filas, se devuelven dos
    pseudo-registros por grupo (clase 1 y clase 0) con su peso en casos, listos
    para las métricas de scikit-learn vía `sample_weight`.

    Returns:
        y_true: clase real (1 seguido, 0 no seguido) de cada pseudo-registro.
        score:  probabilidad predicha asociada.
        peso:   número de casos que representa cada pseudo-registro.
    """
    k = df["NumeroCasosConSeguimiento"].to_numpy(float)
    n = df["NumeroCasos"].to_numpy(float)
    y_true = np.concatenate([np.ones(len(df)), np.zeros(len(df))])
    score = np.concatenate([p_pred, p_pred])
    peso = np.concatenate([k, n - k])
    return y_true, score, peso


def matriz_confusion_casos(
    y_true: np.ndarray, score: np.ndarray, peso: np.ndarray, umbral: float = 0.5
) -> pd.DataFrame:
    """Matriz de confusión a nivel de caso, ponderada por casos, a un umbral dado.

    Se predice "seguido" cuando la probabilidad iguala o supera el umbral. Las
    filas son la clase real y las columnas la predicha; cada celda cuenta casos.
    """
    from sklearn.metrics import confusion_matrix

    y_pred = (score >= umbral).astype(int)
    m = confusion_matrix(y_true, y_pred, labels=[0, 1], sample_weight=peso)
    return pd.DataFrame(
        m,
        index=["Real: No seguido", "Real: Seguido"],
        columns=["Pred: No seguido", "Pred: Seguido"],
    )


def metricas_clasificacion(
    y_true: np.ndarray, score: np.ndarray, peso: np.ndarray, umbral: float = 0.5
) -> dict:
    """Métricas de clasificación a nivel de caso (ponderadas) al umbral indicado.

    Incluye el AUC-ROC, que no depende del umbral y es la medida principal ante el
    fuerte desbalance (la mayoría de los casos sí reciben seguimiento). La
    especificidad mide la capacidad de detectar los casos sin seguimiento, que es
    la clase de interés (la brecha).
    """
    from sklearn.metrics import confusion_matrix, roc_auc_score

    y_pred = (score >= umbral).astype(int)
    tn, fp, fn, tp = confusion_matrix(
        y_true, y_pred, labels=[0, 1], sample_weight=peso
    ).ravel()
    eps = 1e-12
    return {
        "umbral": umbral,
        "accuracy": (tp + tn) / (tp + tn + fp + fn),
        "sensibilidad_seguido": tp / (tp + fn + eps),
        "especificidad_noseguido": tn / (tn + fp + eps),
        "precision_seguido": tp / (tp + fp + eps),
        "f1_seguido": 2 * tp / (2 * tp + fp + fn + eps),
        "auc_roc": float(roc_auc_score(y_true, score, sample_weight=peso)),
    }
