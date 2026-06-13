# HALLAZGOS.md — Hallazgos del EDA y propuesta de modelado

Documento de lectura del cuaderno `Proyecto_PRASS_Seguimiento_COVID19.ipynb`. La
**Parte A** recorre los hallazgos gráfica por gráfica (qué muestra, qué se encontró,
qué problema revela). La **Parte B** infiere, según esos hallazgos y su
factibilidad, qué modelo(s) conviene aplicar. La variable objetivo es
`CoberturaConSeguimiento` (%); su definición y propósito están en `DATABASE.md`.

---

## Parte A — Hallazgos por gráfica

### Preprocesamiento (problemas detectados antes de graficar)
- **Porcentajes corruptos.** `PorcentajeCasos*` codifican 100 % como `1e22` en unas
  filas y como decimales en otras (separador decimal perdido de forma
  inconsistente). Se descartan y la cobertura se **recalcula** desde los conteos.
- **Comas internas, falsa alarma.** Territorios como `"11001 - BOGOTÁ, D.C."` tienen
  comas dentro de comillas (RFC 4180); `pandas` los parsea bien. No hay
  desalineación ni nulos.
- **Campos `código - nombre`.** `Departamento` y `Municipio` mezclan DIVIPOLA y
  nombre; se separan en `*Codigo` / `*Nombre`.
- **Fecha no estándar** (`MM/DD/YYYY 12:00:00 AM`, hora constante) → se tipa a
  fecha y se descarta la hora.
- **Texto sucio.** `EntidadRegistro` tiene espacios dobles internos → se normaliza.
- **`FechaCorte` constante** (`2022-05-25`) → se elimina.
- **Calidad de base buena:** 339.646 filas, **sin nulos**, **sin duplicados**, e
  identidad `Total = Con + Sin` cumplida en el 100 % de las filas.

### Gráficas del cuaderno

**1. Boxplots de conteos (sec. 8).** Muestran la dispersión de `NumeroCasos`,
`...ConSeguimiento` y `...SinSeguimiento`. Hallazgo: ~13 % de filas son "atípicas"
por IQR, pero con mediana 1–2 casos y máximo 31.654 se trata de una **cola larga
natural** de un conteo, no de errores. Problema: el criterio IQR no es apropiado
para conteos asimétricos; eliminar esos "outliers" destruiría señal real.

**2. Histogramas `log1p` de conteos (sec. 20).** Incluso en escala logarítmica las
distribuciones decaen rápido: la mayoría de los grupos son **pequeños**.
`SinSeguimiento` se acumula en cero. Problema/consecuencia: asimetría extrema; las
escalas crudas no sirven para visualizar ni para modelos lineales.

**3. Histograma de `CoberturaConSeguimiento` (sec. 21) — LA GRÁFICA CRÍTICA.** Es la
que motiva toda la decisión de modelado. La cobertura **no** tiene forma de campana
ni una continua suave: hay un **pico dominante en 100 %**, una **acumulación en
0 %** y un **vacío en los valores intermedios**. El `describe()` lo confirma:
media 91,95, pero `25% = 50% = 75% = 100`. Es decir, **al menos tres cuartas partes
de las filas valen exactamente 100 %**. Es una distribución **cuasi-degenerada,
inflada en los extremos** (sobre todo en 1, con masa en 0). Este es el problema
central del proyecto.

**4. KDE de cobertura y `log1p(NumeroCasos)` (sec. 24).** La densidad suavizada
confirma la concentración casi total cerca del 100 % y la asimetría positiva de los
conteos. Refuerza el hallazgo 3.

**5. Cobertura global ponderada vs promedio simple (sec. 22).** Ponderada por casos
= **94,39 %**; promedio simple por fila = **91,95 %**. Hallazgo metodológico: el
promedio simple **sobrerrepresenta a los grupos pequeños**; la medida correcta del
sistema pondera por `NumeroCasos`. Todas las comparativas posteriores usan la
versión ponderada.

**6. Univariado categórico: torta + barras (sec. 23).** `Fuente` domina en
`CONFIRMADOS`. Los registros se concentran en pocos departamentos (Antioquia,
Cundinamarca, Valle) y pocas entidades (NUEVA EPS, Sanitas). Problema:
**desbalance** marcado de categorías, a tener en cuenta en comparaciones y en
cualquier modelo.

**7. Cobertura por fuente (sec. 25).** `CONFIRMADOS` ≈ 96,0 %, `SOSPECHOSOS
SIVIGILA` ≈ 79,9 %, `POBLACIÓN NO AFILIADA` ≈ 75,5 %. Hallazgo: el **origen del
caso es el factor más discriminante** de la brecha.

**8. Cobertura por departamento (sec. 26).** Barras de los 10 extremos. Hallazgo:
**heterogeneidad territorial** real; los departamentos del extremo inferior
concentran las brechas y serían prioritarios de intervención.

**9. Cobertura por entidad ≥ 1.000 casos (sec. 27).** Entre entidades de volumen
comparable la cobertura **también varía**, lo que apunta a diferencias de
**gestión** más allá del territorio.

**10. Heatmap de correlación (sec. 28).** `NumeroCasos` y `...ConSeguimiento`
correlacionan casi 1: es la **identidad estructural** (la mayoría de casos se
siguen), no información nueva. La semana correlaciona débil con todo.

**11. Correlación con la objetivo (sec. 29).** Todas las correlaciones lineales de
la cobertura con los conteos y la semana son **< 0,13 en valor absoluto** (la mayor,
−0,12 con `SinSeguimiento`). Problema: Pearson es **casi nulo y engañoso** porque la
cobertura **satura en 100 %**; la relación real es **no lineal**. Un modelo lineal
guiado por estas correlaciones fracasaría.

**12. Scatterplots (sec. 30).** Tamaño del grupo vs cobertura: la **varianza cae al
crecer N** — los grupos pequeños toman 0 % o 100 %, los grandes se estabilizan
arriba. Hallazgo: relación **heterocedástica y no lineal**; el tamaño del grupo es
clave para la confiabilidad de cada observación.

**13. Heatmap departamento × fuente (sec. 31).** La brecha vive en la
**interacción**: dentro de cada departamento, `CONFIRMADOS` mantiene cobertura
alta mientras `POBLACIÓN NO AFILIADA` y `SOSPECHOSOS` concentran los déficits, con
fuerte variación territorial. No es solo territorio ni solo fuente: es su cruce.

**14. Serie temporal mensual (sec. 32).** El volumen dibuja las **olas
epidémicas**; la cobertura mensual se mantiene **alta y estable**. Hallazgo: el
tiempo aporta poco a explicar la cobertura (el seguimiento se sostuvo en los picos).

### Síntesis de problemas que condicionan el modelado
1. **Objetivo con distribución inflada en los extremos** (≈75 %+ en 100 %, masa en
   0 %): no es normal ni una Beta clásica (gráficas 3 y 4).
2. **Correlaciones lineales nulas** → las relaciones son no lineales (gráfica 11).
3. **Heterocedasticidad ligada al tamaño del grupo** N (gráfica 12).
4. **Heterogeneidad con interacciones** territorio × fuente × entidad (gráficas
   7–9, 13).
5. **Desbalance** de categorías (gráfica 6).
6. **Dependencia por construcción:** los conteos generan la cobertura; usarlos como
   predictores del % sería fuga de información.

### Justificación pre-modelo: ¿la dispersión es estructural? (secciones 34–35)

En lugar de afirmar de entrada que hay alta dispersión, se investiga su causa:
primero se agrupa sin supervisión, luego se predice el grupo para medir cuán
diferenciado está y por cuáles características, y de ahí se concluye.

- **Conglomerados (K-Means, sección 34).** Sobre el perfil por grupo —cobertura,
  tamaño en `log1p` y fuente, estandarizados— emergen **cuatro regímenes**: el
  dominante `CONFIRMADOS` (88,6 % de los casos, cobertura ponderada 97,5 %), un
  bloque de **brecha dura** `CONFIRMADOS` con cobertura 12,4 %, `SOSPECHOSOS`
  ≈90,2 % y `POBLACIÓN NO AFILIADA` ≈75,5 %. El **eta² de la cobertura entre
  conglomerados es 0,886** y el del tamaño es casi nulo (0,006).
- **¿Hay variabilidad? Árbol que predice el conglomerado (sección 34).** Un árbol
  de decisión (modelo surrogate del K-Means) predice el grupo con **exactitud
  ≈0,999**: los conglomerados están **netamente diferenciados**, no se confunden.
  Sus importancias revelan **por cuáles características** se agrupan: `Fuente`
  (≈0,56) y cobertura (≈0,44); el **tamaño no aporta** (0,000). Veredicto: la
  dispersión es **estructural, no ruido**, y su **causa** es el origen del caso
  combinado con el régimen de cobertura (bloque casi totalmente seguido vs. bloque
  de brecha dura). Esto justifica modelar y no solo describir. (Nota: a nivel
  municipio la cobertura ponderada se homogeneíza —eta² 0,013—; la estructura vive
  a nivel de grupo, no de territorio agregado.)
- **Peso de variables (reducción de devianza, sección 35).** GLM binomial de un
  solo factor por predictor: `Fuente` explica 12,1 % de la devianza con solo 2 gl
  (el más **eficiente**), `EntidadRegistro` 35,7 % (67 gl, alta cardinalidad),
  `DepartamentoNombre` 5,0 % (32 gl) y `FechaRegistroSemana` 0,3 % (irrelevante).
  Confirma el orden de importancia del EDA y descarta apoyarse en el tiempo.

---

## Parte B — Qué modelo aplicar (inferido por factibilidad)

### El problema que define la decisión
La gráfica 3 (y la 4) muestran una variable objetivo **cuasi-degenerada, inflada en
1 y con masa en 0**. Esto descarta de entrada lo "básico":

| Enfoque ingenuo | Por qué **no** sirve aquí |
|-----------------|---------------------------|
| Regresión lineal (OLS) sobre la cobertura | Predice fuera de `[0,100]`, residuos no normales, ignora la masa puntual en 0 y 100, y es heterocedástica (gráfica 12). |
| Regresión Beta clásica | La Beta exige `y ∈ (0,1)` **abierto**; aquí abundan los 1 (100 %) y hay 0 exactos. Inaplicable sin inflar. |
| Guiarse por la correlación de Pearson | Es ≈0 por la saturación (gráfica 11); no detecta la relación real, que es no lineal. |

A partir de los hallazgos, estas son las opciones **factibles**, en orden de
recomendación.

### (1) Recomendado — Reformular: modelar la probabilidad de seguimiento por caso (GLM binomial / logística agregada)
En lugar de modelar el porcentaje continuo, reconocer el **proceso generador real**:
de `N = NumeroCasos`, `k = NumeroCasosConSeguimiento` reciben seguimiento, luego
`k ~ Binomial(N, p)`. Se ajusta una **regresión logística sobre datos agrupados**,
ponderada por `N`, con predictores `Fuente`, `Departamento`/`Municipio`,
`EntidadRegistro` y `FechaRegistroSemana`.

Por qué es la opción más factible y correcta:
- `p ∈ (0,1)` **nunca se sale de rango**; la saturación en 100 % se traduce en
  probabilidades cercanas a 1, **sin** el problema de la masa puntual.
- **Pondera por `N`**, lo que resuelve directamente el ruido de los grupos pequeños
  visto en el scatter (gráfica 12).
- Es interpretable (odds ratios por fuente, territorio, entidad) y se ajusta con
  `statsmodels` (`GLM` familia `Binomial`).
- **Sobredispersión** esperada por la heterogeneidad entre grupos → corregir con
  quasi-binomial o escalar a **beta-binomial**.

**Por qué la binomial dentro de la familia exponencial (sección 38).** La familia
la fija el dato: la respuesta es `k` éxitos sobre `N` ensayos (conteo acotado), no
una magnitud continua ni un conteo sin tope.

| Familia | Soporte | Media–varianza | ¿Aplica? |
|---|---|---|---|
| Normal | real continuo | varianza constante | No: acotada en `[0,100]` y heterocedástica. |
| Gamma / inversa gaussiana | real positivo | Var ∝ media² | No: para continuas positivas. |
| Poisson | enteros sin tope | Var = media | No: `k` está acotado por `N`. |
| **Binomial** | 0…N éxitos | **Var = N·p·(1−p)** | **Sí**: proceso exacto, pondera por N, enlace logit en rango. |

**Redefinición implementada (interacción Fuente × Departamento + quasi-binomial,
sección 46).** A partir de los conglomerados —que muestran que la fuente y un régimen
de **brecha dura** (interacción fuente × territorio) son lo que diferencia y ayuda a
predecir la cobertura— se añadió el término `Fuente × Departamento` (solo en celdas con
soporte y **no saturadas** en 0/100 %, para evitar separación) y se ajustó como
**quasi-binomial**. Resultado: la interacción mejora el ajuste de forma **moderada**
(pseudo-R² 0,514 → 0,529; Brier 0,0425 → 0,0421 en prueba), pero la **sobredispersión
persiste** (2,77 → 2,94): es **heterogeneidad intrínseca entre grupos**, no un término
faltante. El quasi-binomial corrige los errores estándar (escala 2,94, SE ≈ ×1,7); el
camino estructural es la opción (2).

### (2) Modelo multinivel / jerárquico (GLMM logístico binomial)
Extiende la opción (1) con **efectos aleatorios** por `Departamento` (con
`Municipio` anidado) y por `EntidadRegistro`. Es la respuesta directa a la
heterogeneidad de las gráficas 8, 9 y 13.

Por qué encaja con los hallazgos:
- Captura que la brecha vive en la **interacción territorio × fuente × entidad**.
- El **shrinkage** produce rankings de brecha **más robustos** que comparar
  promedios crudos, especialmente para entidades/municipios con pocos casos.
- Es el enfoque "publicable" en vigilancia epidemiológica. Factible con
  `statsmodels` (`BinomialBayesMixedGLM`) o `pymc`.

### (3) Zero-One-Inflated Beta (ZOIB) — el modelo teóricamente exacto para la distribución única
Si se exige modelar el **porcentaje tal cual** (gráfica 3), la familia correcta es
la Beta **inflada en cero y uno**, que modela explícitamente tres procesos:
`P(Y=0)`, `P(Y=1)` y una **Beta** para los valores interiores `(0,1)`.

Por qué es el ajuste más fiel:
- Es la única familia que **respeta la masa puntual en 0 % y 100 %** que ninguna
  continua estándar admite. Responde de frente a "la distribución es única".
- Costo: mayor complejidad, normalmente **bayesiano** (`pymc` o estilo `brms`).
  Factible, pero más esfuerzo que (1). Recomendado como modelo "fino" tras tener la
  base logística.

### (4) Reformular como clasificación de "brecha" + gradient boosting + SHAP
Como la objetivo es **cuasi-binaria** (100 % vs no-100 %), definir
`brecha = cobertura < umbral` (p. ej. < 100 % o < 90 %) y predecir con
**LightGBM/XGBoost**.

Por qué es muy factible y útil:
- Convierte un objetivo de forma rara en un problema **bien planteado**.
- El boosting captura las **no linealidades e interacciones** (territorio × fuente)
  que Pearson no veía (gráficas 11, 13), sin supuestos distribucionales.
- **SHAP** cuantifica e interpreta qué factores generan la brecha (se anticipa que
  `Fuente` domina). Maneja el **desbalance** con pesos de clase.
- Salida **accionable**: probabilidad de brecha por grupo → priorización de
  intervención territorial.

### Análisis complementario (no supervisado)
**Clustering** (K-Means o HDBSCAN) de municipios o entidades por perfil —cobertura
ponderada, volumen, mezcla de fuentes— para **segmentar territorios** y orientar
política. Opcional, complementa pero no reemplaza el modelo de la objetivo.

### Qué evitar
- OLS lineal sobre la cobertura.
- Beta sin inflar.
- Usar los conteos como predictores del porcentaje (fuga por construcción).
- Tomar Pearson como criterio de relación.

### Recomendación final
Empezar por **(1)** logística binomial ponderada por `N` como base correcta;
escalar a **(2)** multinivel para la heterogeneidad territorio/entidad; usar **(4)**
boosting + SHAP para interpretar y priorizar la brecha; y reservar **(3)** ZOIB como
el modelo teóricamente exacto para la distribución inflada si el objetivo es
modelar el porcentaje en sí.
