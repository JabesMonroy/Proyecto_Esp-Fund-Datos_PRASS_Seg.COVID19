# WORKFLOWS.md — Flujos de trabajo

Convenciones y comandos para trabajar el proyecto por etapas.

## Entorno

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell
pip install -r requirements.txt
copy .env.example .env          # ajustar rutas si hace falta
```

## CLI por etapas

`main.py` expone subcomandos, uno por etapa del pipeline. Solo
`preprocess` está habilitado; el resto son marcadores de posición.

```bash
python main.py preprocess       # Etapa 1: limpieza/normalización  (EN CURSO)
python main.py eda              # Etapa 2: análisis exploratorio    (pendiente)
python main.py viz              # Etapa 3: visualizaciones          (pendiente)
python main.py model            # Etapa 4: modelado                 (pendiente)
```

Opciones comunes:

```bash
python main.py preprocess --input data/SegCovid19-Seguimiento_PRASS.csv \
                          --output data/processed.parquet
```

## Roadmap de desarrollo

1. **Preprocesamiento** (etapa actual). Tareas previstas en `utils.py`:
   - Carga tolerante a filas desalineadas (comas sin escapar).
   - Separar `Departamento`/`Municipio` en código y nombre.
   - Parsear `FechaRegistro` y `FechaCorte` a `datetime`.
   - Recalcular porcentajes desde los conteos (las columnas `Porcentaje*`
     vienen corruptas — ver [DATABASE.md](DATABASE.md)).
   - Exportar dataset limpio (`parquet`).
2. **EDA** — estadísticas descriptivas, agregados por departamento/fuente/semana.
3. **Visualización** — series temporales y comparativas territoriales.
4. **Modelado** — features + modelos predictivos.

## Convenciones

- **Datos:** crudos en `data/`; los derivados (`*.parquet`, `*_clean.csv`) se
  ignoran en git (ver `.gitignore`), salvo el crudo que sí se versiona.
- **Ramas:** `main` estable; `feature/<etapa>` para trabajo en curso.
- **Commits:** mensajes en español, imperativo (`agrega…`, `corrige…`).
- **Estilo:** funciones reutilizables en `utils.py`; `main.py` solo orquesta.

## Git

```bash
git checkout -b feature/preprocesamiento
git add -A
git commit -m "agrega limpieza de columnas de porcentaje"
git push -u origin feature/preprocesamiento
```
