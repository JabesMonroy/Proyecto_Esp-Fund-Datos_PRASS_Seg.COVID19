# DATABASE.md — Diccionario de datos y calidad del dato

Fuente: `data/SegCovid19-Seguimiento_PRASS.csv`

| Propiedad | Valor |
|-----------|-------|
| Registros | 339.646 filas (+ 1 cabecera) |
| Columnas  | 12 |
| Tamaño    | ~46 MB |
| Separador | coma (`,`) |
| Codificación | UTF-8 (sin BOM) |
| Origen    | Programa PRASS — Seguimiento COVID-19 (Colombia) |
| Fuente    | datos.gov.co · conjunto `r6r5-w84k` ([descarga](https://www.datos.gov.co/api/views/r6r5-w84k/rows.csv?accessType=DOWNLOAD)) |

## Propósito del dato y variable objetivo

Esta sección explica, antes del detalle técnico, **qué se recolectó, con qué fin y
cuál es la variable que el estudio busca explicar**.

### Por qué existe esta base
PRASS (Pruebas, Rastreo y Aislamiento Selectivo Sostenible) fue la estrategia de
vigilancia epidemiológica de Colombia durante la pandemia. Su meta operativa era
que cada caso COVID-19 detectado recibiera **seguimiento**: contacto con el
paciente, rastreo de sus contactos y verificación del aislamiento. Esta base es el
**registro de cumplimiento** de esa estrategia: cuántos casos se identificaron y
cuántos fueron efectivamente seguidos, desagregado por origen, tiempo, territorio
y entidad reportante.

### Qué representa cada fila (granularidad)
No hay un registro por persona. Cada fila es un **agregado** que cuenta los casos
de una combinación única de `Fuente` × `FechaRegistro` (semana) × `Departamento` ×
`Municipio` × `EntidadRegistro`. Por eso `NumeroCasos` puede valer 1 o varios
miles: es el total del grupo, no un individuo. La extracción es una sola foto, con
fecha de corte única (25/05/2022).

### Rol de cada variable: dimensiones, métricas y descartes
- **Dimensiones (con qué se agrupa / posibles predictores):** `Fuente`,
  `FechaRegistro`, `FechaRegistroSemana`, `Departamento`, `Municipio`,
  `EntidadRegistro`.
- **Métricas crudas (lo que se cuenta):** `NumeroCasos`,
  `NumeroCasosConSeguimiento`, `NumeroCasosSinSeguimiento`. Cumplen la identidad
  `Total = Con + Sin` en el 100 % de las filas, lo que las vuelve confiables.
- **Variables descartadas:** `PorcentajeCasos*` (escala corrupta, ver más abajo) y
  `FechaCorte` (constante).

### La variable objetivo: cobertura de seguimiento
El fenómeno de interés es la **cobertura de seguimiento**: qué fracción de los
casos de un grupo recibió seguimiento. Como las columnas de porcentaje del origen
están corruptas, se **recalcula** desde los conteos confiables:

`CoberturaConSeguimiento (%) = NumeroCasosConSeguimiento / NumeroCasos · 100`

**Para qué sirve.** Es el indicador que mide el desempeño del sistema PRASS y la
variable que cualquier modelo posterior busca explicar o predecir. Permite
responder las preguntas del estudio:
- ¿Dónde están las **brechas** (grupos con baja cobertura)?
- ¿La cobertura depende del **origen del caso** (`Fuente`), del **territorio** o de
  la **entidad** reportante?
- ¿Se **sostuvo** la cobertura durante las olas epidémicas?

> Advertencia clave para el modelado: esta variable **no** sigue una distribución
> habitual. Está fuertemente saturada en 100 % (al menos el 75 % de las filas en
> exactamente 100 %), con masa adicional en 0 % y muy pocos valores intermedios. Su
> forma —no una continua suave, sino una distribución **inflada en los extremos**—
> condiciona qué modelos son válidos. El análisis de gráficas y la propuesta de
> modelado están en `HALLAZGOS.md`.

## Diccionario de datos

| # | Columna | Tipo lógico | Descripción |
|---|---------|-------------|-------------|
| 1 | `Fuente` | categórica | Origen del caso. 3 valores: `CONFIRMADOS`, `POBLACIÓN NO AFILIADA`, `SOSPECHOSOS SIVIGILA`. |
| 2 | `FechaRegistro` | fecha/hora | Fecha del registro. Formato `MM/DD/YYYY 12:00:00 AM`. |
| 3 | `FechaRegistroSemana` | entero | Número de semana epidemiológica asociada al registro. |
| 4 | `Departamento` | categórica codificada | Formato `CÓDIGO - NOMBRE` (p. ej. `41 - HUILA`). 33 departamentos. |
| 5 | `Municipio` | categórica codificada | Formato `CÓDIGO - NOMBRE` (p. ej. `41551 - PITALITO`). |
| 6 | `EntidadRegistro` | texto | Entidad (EPS / aseguradora / institución) que reporta. |
| 7 | `NumeroCasos` | entero | Total de casos. |
| 8 | `NumeroCasosSinSeguimiento` | entero | Casos sin seguimiento PRASS. |
| 9 | `NumeroCasosConSeguimiento` | entero | Casos con seguimiento PRASS. |
| 10 | `PorcentajeCasosSinSeguimiento` | numérico (⚠️) | % de casos sin seguimiento. **Formato corrupto, ver abajo.** |
| 11 | `PorcentajeCasosConSeguimiento` | numérico (⚠️) | % de casos con seguimiento. **Formato corrupto, ver abajo.** |
| 12 | `FechaCorte` | fecha | Fecha de corte de la extracción (p. ej. `2022-05-25`). |

## Problemas de calidad detectados

Estos hallazgos guían la etapa de **preprocesamiento**.

### 1. ⚠️ Columnas de porcentaje con escala/decimal corrupto
Las columnas `PorcentajeCasos*` no están en una escala consistente:
- En muchas filas aparecen como **enteros gigantes** donde `100%` se codifica como `1e22`
  (ej.: `9615384615384610000000` ≈ `96.15%` para 25/26 casos). Equivale a multiplicar
  el porcentaje por `1e20`.
- En otras filas aparecen como **decimales** normales (ej.: `0.0118…`).
- El separador decimal se perdió de forma inconsistente.

**Estrategia recomendada:** no confiar en estas columnas tal cual. Recalcular el
porcentaje desde las columnas de conteo:
`PctConSeguimiento = NumeroCasosConSeguimiento / NumeroCasos`.

### 2. Comas internas en campos entrecomillados (NO hay desalineación)
Algunos territorios contienen comas en el nombre (p. ej. `"11001 - BOGOTÁ, D.C."`,
7.032 filas). En el archivo **están entrecomillados** según RFC 4180, por lo que el
lector por defecto de `pandas` (`pd.read_csv`) los parsea correctamente: las 339.646
filas cargan sin desalineación ni valores nulos.

> Nota: un conteo ingenuo de comas por línea (sin considerar comillas) sugiere ~2,3 %
> de filas con 13–14 campos. Es un **falso positivo**: esas comas viven dentro de
> comillas. No se requiere parser tolerante.

### 3. Campos codificados `CÓDIGO - NOMBRE`
`Departamento` y `Municipio` mezclan código DIVIPOLA y nombre en un solo campo.
Conviene **separarlos** en `*_codigo` y `*_nombre`.

### 4. Formato de fecha no estándar
`FechaRegistro` viene como `MM/DD/YYYY 12:00:00 AM` (hora siempre medianoche, sin
información útil). Parsear a `datetime` y descartar la parte horaria.

## Notas

- DIVIPOLA: codificación oficial de divisiones político-administrativas de Colombia
  (DANE), usada en `Departamento` y `Municipio`.
- PRASS: Pruebas, Rastreo y Aislamiento Selectivo Sostenible.
