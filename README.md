# Proyecto PRASS — Seguimiento COVID-19

Análisis de datos del programa **PRASS** (Pruebas, Rastreo y Aislamiento Selectivo
Sostenible) sobre el seguimiento a casos COVID-19 en Colombia.

> Proyecto de la Especialización — *Fundamentos de Ciencia de Datos*.

## Objetivo

Desarrollar, de forma reproducible y como **entregable único**, un análisis que avance
por etapas desde la **exploración y limpieza** del dato hasta **modelos predictivos** y
otros estudios. Todo el trabajo vive en un solo cuaderno Jupyter, donde cada decisión se
justifica de manera breve.

Estado del roadmap:

| Etapa | Estado | Descripción |
|-------|--------|-------------|
| 1. Exploración | Hecho | Observación y diagnóstico del dato crudo. |
| 2. Preprocesamiento | En curso | Tipado de fechas, separación código/nombre, depuración. |
| 3. EDA | Pendiente | Análisis exploratorio y estadísticas descriptivas. |
| 4. Visualización | Pendiente | Tendencias temporales y comparativas territoriales. |
| 5. Modelado | Pendiente | Modelos predictivos / inferenciales. |

## Estructura

```
mi-proyecto-pip/
├── Proyecto_PRASS_Seguimiento_COVID19.ipynb   # Entregable único (análisis + justificación)
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── WORKFLOWS.md
├── DATABASE.md
└── data/
    └── SegCovid19-Seguimiento_PRASS.csv        # Dato crudo
```

## Inicio rápido

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (PowerShell)
pip install -r requirements.txt
jupyter lab                       # o abrir el .ipynb en VS Code
```

Abrir `Proyecto_PRASS_Seguimiento_COVID19.ipynb` y ejecutar las celdas en orden.

## Datos

El dataset crudo (`data/SegCovid19-Seguimiento_PRASS.csv`, ~46 MB) se versiona en el
repositorio. Su diccionario de datos y problemas de calidad están en
[DATABASE.md](DATABASE.md).

## Documentación

- [WORKFLOWS.md](WORKFLOWS.md) — flujo de ramas y convenciones.
- [DATABASE.md](DATABASE.md) — diccionario de datos y calidad del dato.

## Autor

Jabes Monroy — `jmonroyb@unal.edu.co`
