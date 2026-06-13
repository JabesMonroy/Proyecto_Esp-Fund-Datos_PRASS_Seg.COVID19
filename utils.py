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
    if len(categoricas):
        X = pd.get_dummies(df[list(categoricas)], drop_first=True, dtype=float)
    else:
        X = pd.DataFrame(index=df.index)
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


def construir_diseno_interaccion(
    df: pd.DataFrame,
    par: tuple[str, str] = ("Fuente", "DepartamentoNombre"),
    otras_categoricas: tuple[str, ...] = ("EntidadRegistro",),
    numericas=PREDICTORES_NUMERICOS,
    min_casos_celda: int = 500,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Matriz de diseño con la interacción entre los dos factores de `par`.

    Redefinición del modelo a partir del análisis de conglomerados: estos
    revelaron que la fuente del caso, cruzada con el territorio, genera un régimen
    de **brecha dura** que un efecto principal homogéneo no captura (se filtra como
    sobredispersión). Se añaden por ello los términos de interacción
    `Fuente × Departamento` —productos de sus variables indicadoras (sin la
    categoría de referencia)— junto a los efectos principales, `EntidadRegistro` y
    la semana. La respuesta binomial es la misma pareja `(k, N - k)`.

    Solo se incluye el término de interacción de una celda cuando tiene al menos
    `min_casos_celda` casos y **no está saturada** (coexisten casos seguidos y no
    seguidos). Las celdas con cobertura exacta de 0 % o 100 % están perfectamente
    separadas y producirían coeficientes divergentes; esos territorios se
    representan solo por su efecto principal. Así sobreviven los términos de las
    celdas con brecha real, que son las relevantes.
    """
    a, b = par
    da = pd.get_dummies(df[a], prefix=a, drop_first=True, dtype=float)
    db = pd.get_dummies(df[b], prefix=b, drop_first=True, dtype=float)
    celda = df.groupby([a, b], observed=True).agg(
        n=("NumeroCasos", "sum"), k=("NumeroCasosConSeguimiento", "sum")
    )
    inter = {}
    for ca in da.columns:
        va = ca[len(a) + 1 :]
        for cb in db.columns:
            vb = cb[len(b) + 1 :]
            if (va, vb) in celda.index:
                n, k = celda.loc[(va, vb), "n"], celda.loc[(va, vb), "k"]
                if n >= min_casos_celda and 0 < k < n:
                    inter[f"{ca}:{cb}"] = da[ca].to_numpy() * db[cb].to_numpy()
    X = pd.concat([da, db, pd.DataFrame(inter, index=df.index)], axis=1)
    for c in otras_categoricas:
        X = pd.concat(
            [X, pd.get_dummies(df[c], prefix=c, drop_first=True, dtype=float)], axis=1
        )
    for c in numericas:
        X[c] = df[c].astype(str).astype(float).to_numpy()
    X = sm.add_constant(X)
    y = df[["NumeroCasosConSeguimiento", "NumeroCasosSinSeguimiento"]].to_numpy(
        dtype=float
    )
    return X, y


def ajustar_quasibinomial(X: pd.DataFrame, y: np.ndarray):
    """Ajusta un GLM **quasi-binomial**: estima el binomial y fija la escala en la
    dispersión de Pearson (chi-cuadrado de Pearson sobre los grados de libertad).
    Las estimaciones puntuales coinciden con las del binomial, pero los errores
    estándar se inflan por la raíz de la sobredispersión, dando inferencia honesta
    ante la heterogeneidad entre grupos que el clustering reveló.
    """
    binom = sm.GLM(y, X, family=sm.families.Binomial()).fit()
    phi = binom.pearson_chi2 / binom.df_resid
    return sm.GLM(y, X, family=sm.families.Binomial()).fit(scale=phi)


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


# --------------------------------------------------------------------------- #
# Justificación de la dispersión: análisis de conglomerados (no supervisado)
# --------------------------------------------------------------------------- #
# La cobertura presenta una dispersión marcada (sección 30). Antes de modelar se
# verifica si esa dispersión responde a una estructura: se agrupan los grupos
# (filas) por su perfil y se examina si emergen conglomerados de cobertura
# claramente distinta (variabilidad estructural) o si todos se parecen (ruido).


def features_grupo(df: pd.DataFrame) -> pd.DataFrame:
    """Matriz de características por grupo (fila) para el agrupamiento.

    Combina: la cobertura de seguimiento (%), el tamaño del grupo en escala
    logarítmica `log1p(NumeroCasos)` —que normaliza la fuerte asimetría de los
    conteos (sección 20) sin descartar la información de tamaño— y la `Fuente`
    del caso codificada como variables indicadoras. Es el insumo del K-Means.
    """
    feat = pd.DataFrame(index=df.index)
    feat["cobertura_pct"] = df["CoberturaConSeguimiento"].to_numpy(float)
    feat["log_casos"] = np.log1p(df["NumeroCasos"].to_numpy(float))
    du = pd.get_dummies(df["Fuente"], prefix="fuente", drop_first=True, dtype=float)
    du.index = feat.index
    return pd.concat([feat, du], axis=1)


def escalar(feats: pd.DataFrame) -> np.ndarray:
    """Estandariza todas las columnas (media 0, desviación 1) para que ninguna
    domine la distancia euclídea por su escala. Devuelve un arreglo de numpy."""
    from sklearn.preprocessing import StandardScaler

    return StandardScaler().fit_transform(feats.to_numpy(float))


def seleccionar_k(
    X: np.ndarray,
    k_min: int = 2,
    k_max: int = 7,
    n_init: int = 5,
    random_state: int = 0,
    muestra_silueta: int = 20000,
) -> pd.DataFrame:
    """Recorre K-Means para k en `[k_min, k_max]` y reporta, por cada k, la
    inercia (codo) y el coeficiente de silueta. La silueta se evalúa sobre una
    submuestra de tamaño `muestra_silueta` porque su cálculo es cuadrático en el
    número de observaciones. La silueta máxima sugiere el número de
    conglomerados mejor separados."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    rng = np.random.RandomState(random_state)
    filas = []
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, n_init=n_init, random_state=random_state).fit(X)
        if muestra_silueta and len(X) > muestra_silueta:
            idx = rng.choice(len(X), muestra_silueta, replace=False)
            sil = silhouette_score(X[idx], km.labels_[idx])
        else:
            sil = silhouette_score(X, km.labels_)
        filas.append(
            {"k": k, "inercia": float(km.inertia_), "silueta": float(sil)}
        )
    return pd.DataFrame(filas)


def ajustar_kmeans(X: np.ndarray, k: int, n_init: int = 5, random_state: int = 0):
    """Ajusta K-Means con `k` conglomerados y devuelve el modelo entrenado."""
    from sklearn.cluster import KMeans

    return KMeans(n_clusters=k, n_init=n_init, random_state=random_state).fit(X)


def caracterizar_clusters(
    df: pd.DataFrame, feats: pd.DataFrame, etiquetas: np.ndarray
) -> pd.DataFrame:
    """Resume cada conglomerado para leer qué lo caracteriza: número de grupos,
    porcentaje de filas y de casos, fuente predominante, tamaño medio (log),
    cobertura simple media y cobertura ponderada por casos. Si las filas de
    cobertura difieren marcadamente entre conglomerados, la dispersión es
    estructural; si se parecen, sería ruido."""
    d = df[["NumeroCasos", "NumeroCasosConSeguimiento", "Fuente"]].copy()
    d["cluster"] = etiquetas
    d["log_casos"] = feats["log_casos"].to_numpy(float)
    d["cobertura_pct"] = feats["cobertura_pct"].to_numpy(float)
    g = d.groupby("cluster")
    resumen = pd.DataFrame(
        {
            "n_filas": g.size(),
            "casos": g["NumeroCasos"].sum(),
            "fuente_domina": g["Fuente"].agg(lambda s: s.value_counts().index[0]),
            "log_casos_medio": g["log_casos"].mean().round(2),
            "cobertura_simple": g["cobertura_pct"].mean().round(2),
            "cobertura_ponderada": (
                g["NumeroCasosConSeguimiento"].sum() / g["NumeroCasos"].sum() * 100
            ).round(2),
        }
    )
    resumen["pct_filas"] = (resumen["n_filas"] / resumen["n_filas"].sum() * 100).round(1)
    resumen["pct_casos"] = (resumen["casos"] / resumen["casos"].sum() * 100).round(1)
    return resumen.sort_values("cobertura_ponderada")


def eta2_entre_clusters(
    feats: pd.DataFrame, etiquetas: np.ndarray, columna: str = "cobertura_pct"
) -> float:
    """Razón de correlación eta-cuadrado de `columna` respecto a los
    conglomerados: fracción de la varianza total de la variable explicada por la
    pertenencia al grupo. Cercano a 0, los grupos no difieren en esa variable;
    cercano a 1, la separan casi por completo. Aplicado a la cobertura, cuantifica
    en qué grado el agrupamiento captura la dispersión observada."""
    y = feats[columna].to_numpy(float)
    media = y.mean()
    ss_total = float(((y - media) ** 2).sum())
    ss_entre = 0.0
    for grupo in np.unique(etiquetas):
        yg = y[etiquetas == grupo]
        ss_entre += len(yg) * (yg.mean() - media) ** 2
    return float(ss_entre / ss_total) if ss_total > 0 else 0.0


def arbol_clusters(
    feats: pd.DataFrame,
    etiquetas: np.ndarray,
    max_depth: int = 3,
    test_size: float = 0.3,
    random_state: int = 0,
):
    """Ajusta un árbol de decisión que predice el conglomerado a partir de las
    características del agrupamiento (modelo surrogate interpretativo del K-Means).

    Su exactitud mide cuán diferenciados/separables están los grupos: si el árbol
    los predice con alta exactitud, los conglomerados están bien definidos (hay
    variabilidad estructural); si fuese baja, se confundirían entre sí. La
    importancia de las características y las reglas del árbol revelan **por cuáles
    características** se agrupó cada conglomerado.

    Returns:
        arbol: `DecisionTreeClassifier` ajustado.
        info: dict con exactitud de entrenamiento y de prueba e importancias
            (Series ordenada de mayor a menor).
    """
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.model_selection import train_test_split

    X = feats.to_numpy(float)
    Xtr, Xte, ytr, yte = train_test_split(
        X, etiquetas, test_size=test_size, random_state=random_state, stratify=etiquetas
    )
    arbol = DecisionTreeClassifier(max_depth=max_depth, random_state=random_state).fit(
        Xtr, ytr
    )
    importancias = pd.Series(
        arbol.feature_importances_, index=feats.columns
    ).sort_values(ascending=False)
    info = {
        "exactitud_train": float(arbol.score(Xtr, ytr)),
        "exactitud_test": float(arbol.score(Xte, yte)),
        "importancias": importancias,
    }
    return arbol, info


def reglas_arbol(arbol, columnas) -> str:
    """Reglas del árbol en texto legible: los umbrales por característica que
    definen cada conglomerado, para leer qué caracteriza a cada grupo."""
    from sklearn.tree import export_text

    return export_text(arbol, feature_names=list(columnas))


# --------------------------------------------------------------------------- #
# Peso de las variables antes del modelo: reducción de devianza por predictor
# --------------------------------------------------------------------------- #


def ajustar_glmm_intercepto(
    df: pd.DataFrame,
    grupo_aleatorio: str = "DepartamentoNombre",
    efecto_fijo: str = "Fuente",
    n_muestra: int = 120000,
    random_state: int = 0,
):
    """Ajusta un GLMM logístico de intercepto aleatorio: efecto fijo `efecto_fijo`
    e intercepto aleatorio por `grupo_aleatorio`.

    A diferencia del GLM binomial, la heterogeneidad entre territorios deja de ser
    sobredispersión y se modela como un **componente de varianza**: la desviación
    del intercepto aleatorio cuantifica cuánto difieren los departamentos en escala
    logit, y el *shrinkage* estabiliza los niveles con pocos casos. Es el paso
    jerárquico que el clustering y la sobredispersión (≈2.8) ya motivaban.

    El ajuste (`statsmodels`) requiere respuesta binaria por caso, pero el dato está
    agregado en conteos. Por viabilidad se ajusta sobre una muestra de `n_muestra`
    casos individuales (seguido=1 / no seguido=0), generados por celda
    `grupo_aleatorio x efecto_fijo` con probabilidad `k/N` y tamaño proporcional a
    `N`. Se usa la aproximación de Laplace (`fit_map`).

    Returns:
        Objeto de resultados de `BinomialBayesMixedGLM`; los nombres de los efectos
        fijos están en `res.model.fep_names` y la desviación del intercepto
        aleatorio es `exp(res.vcp_mean[0])`.
    """
    from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

    cel = (
        df.groupby([grupo_aleatorio, efecto_fijo], observed=True)
        .agg(N=("NumeroCasos", "sum"), k=("NumeroCasosConSeguimiento", "sum"))
        .reset_index()
    )
    total = cel["N"].sum()
    cel["m"] = np.maximum(1, np.round(cel["N"] / total * n_muestra)).astype(int)
    rng = np.random.RandomState(random_state)
    filas = []
    for _, r in cel.iterrows():
        p = r["k"] / r["N"] if r["N"] > 0 else 0.0
        filas.append(
            pd.DataFrame(
                {
                    "seguido": (rng.random(int(r["m"])) < p).astype(int),
                    efecto_fijo: r[efecto_fijo],
                    grupo_aleatorio: r[grupo_aleatorio],
                }
            )
        )
    datos = pd.concat(filas, ignore_index=True)
    modelo = BinomialBayesMixedGLM.from_formula(
        f"seguido ~ C({efecto_fijo})",
        vc_formulas={"territorio": f"0 + C({grupo_aleatorio})"},
        data=datos,
    )
    return modelo.fit_map()


def predecir_glmm_intercepto(
    res,
    df: pd.DataFrame,
    efecto_fijo: str = "Fuente",
    grupo_aleatorio: str = "DepartamentoNombre",
) -> np.ndarray:
    """Probabilidad de seguimiento por grupo según el GLMM ajustado.

    Reconstruye el predictor lineal `intercepto + efecto_fijo + intercepto
    aleatorio del territorio` y aplica la logística. Los niveles ausentes en el
    ajuste (sin efecto aleatorio estimado) toman 0, es decir, el promedio global.
    Devuelve un arreglo de probabilidades alineado con las filas de `df`.
    """
    import re

    m = res.model
    inter = float(res.fe_mean[0])
    coef_fijo = {}
    for nm, c in zip(m.fep_names[1:], res.fe_mean[1:]):
        coef_fijo[re.search(r"\[T\.(.*)\]", nm).group(1)] = float(c)
    re_grupo = {}
    for nm, v in zip(m.vc_names, res.vc_mean):
        re_grupo[re.search(r"\[(.*)\]", nm).group(1)] = float(v)
    lp = (
        inter
        + df[efecto_fijo].astype(str).map(coef_fijo).fillna(0.0).to_numpy(float)
        + df[grupo_aleatorio].astype(str).map(re_grupo).fillna(0.0).to_numpy(float)
    )
    return 1.0 / (1.0 + np.exp(-lp))


def peso_devianza_predictores(
    df: pd.DataFrame,
    categoricas=PREDICTORES_CATEGORICOS,
    numericas=PREDICTORES_NUMERICOS,
) -> pd.DataFrame:
    """Mide el peso marginal de cada predictor antes del modelo conjunto.

    Para cada predictor ajusta un GLM binomial de un solo factor (frente al
    modelo nulo) y reporta la fracción de devianza nula que explica por sí solo
    (`1 - devianza/devianza_nula`), junto con sus grados de libertad. Un valor
    mayor indica que la variable separa mejor la probabilidad de seguimiento. Se
    informan los grados de libertad porque un predictor con más niveles puede
    explicar más devianza solo por su mayor flexibilidad.
    """
    filas = []
    for p in list(categoricas) + list(numericas):
        cats = (p,) if p in categoricas else ()
        nums = (p,) if p in numericas else ()
        X, y = construir_diseno_glm(df, categoricas=cats, numericas=nums)
        res = ajustar_glm_binomial(X, y)
        filas.append(
            {
                "predictor": p,
                "gl": int(X.shape[1] - 1),
                "devianza_explicada": float(1 - res.deviance / res.null_deviance),
            }
        )
    return (
        pd.DataFrame(filas)
        .sort_values("devianza_explicada", ascending=False)
        .reset_index(drop=True)
    )
