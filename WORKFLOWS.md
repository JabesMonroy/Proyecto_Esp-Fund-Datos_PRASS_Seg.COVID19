# WORKFLOWS.md — Flujo de trabajo

El proyecto se desarrolla sobre un **único cuaderno**:
`Proyecto_PRASS_Seguimiento_COVID19.ipynb`. Cada decisión se justifica de forma breve,
con lenguaje académico y sin emojis.

## Entorno

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell
pip install -r requirements.txt
```

Abrir el `.ipynb` en JupyterLab o VS Code y ejecutar las celdas en orden.

## Roadmap

1. **Exploración** (hecha): naturaleza del dato, faltantes, unicidad, varianza nula,
   outliers, calidad de porcentajes, test de Little (no aplica).
2. **Preprocesamiento** (en curso): conversión de fechas, separación de
   `Departamento`/`Municipio` en código y nombre, eliminación de la columna constante
   `FechaCorte` y recálculo de la cobertura de seguimiento (ver [DATABASE.md](DATABASE.md)).
3. **EDA** — estadísticas descriptivas y agregados.
4. **Visualización** — series temporales y comparativas territoriales.
5. **Modelado** — features y modelos predictivos.

## Flujo de ramas

- `main`: estable; recibe fusiones tras cambios grandes.
- `develop`: rama principal de trabajo.
- `feature/<tema>`: mini-rama dentro de `develop` por cada cambio o plan grande; al
  terminar se fusiona a `develop`.

```bash
git checkout develop
git checkout -b feature/<tema>
# ... trabajo ...
git add -A && git commit -m "descripción en español"
git checkout develop && git merge --no-ff feature/<tema>
git push origin develop
```

## Convenciones

- **Commits:** en español, modo imperativo (`agrega…`, `corrige…`). Autor único: Jabes
  Monroy (sin coautores).
- **Datos:** el CSV crudo se versiona; los derivados se ignoran (ver `.gitignore`).
