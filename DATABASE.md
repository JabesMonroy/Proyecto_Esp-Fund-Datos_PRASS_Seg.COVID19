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
