# Proyecto PRASS — Seguimiento COVID-19

Análisis de datos del programa **PRASS** (Pruebas, Rastreo y Aislamiento Selectivo
Sostenible) sobre el seguimiento a casos COVID-19 en Colombia.

> Proyecto de la Especialización — *Fundamentos de Ciencias de Datos*.

## Objetivo

Construir un pipeline reproducible que vaya, por etapas, desde la **limpieza** del
dato crudo hasta **modelos predictivos** y otros estudios analíticos.

Estado actual del roadmap:

| Etapa | Estado | Descripción |
|-------|--------|-------------|
| 1. Preprocesamiento | 🚧 En curso | Carga, saneamiento y normalización del CSV crudo. |
| 2. EDA | ⏳ Pendiente | Análisis exploratorio y estadísticas descriptivas. |
| 3. Visualización | ⏳ Pendiente | Tendencias temporales y comparativas territoriales. |
| 4. Modelado | ⏳ Pendiente | Modelos predictivos / inferenciales. |

## Estructura del repositorio

```
mi-proyecto-pip/
├── main.py            # Punto de entrada (CLI por etapas)
├── utils.py           # Funciones reutilizables (carga, rutas, config)
├── requirements.txt   # Dependencias
├── .env.example       # Plantilla de variables de entorno
├── .gitignore
├── README.md
├── WORKFLOWS.md       # Flujos de trabajo y comandos
├── DATABASE.md        # Diccionario de datos y calidad del dato
└── data/
    └── SegCovid19-Seguimiento_PRASS.csv   # Dato crudo
```

## Inicio rápido

```bash
# 1. Crear y activar entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows (PowerShell)
# source .venv/bin/activate   # Linux / macOS

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
copy .env.example .env        # Windows
# cp .env.example .env        # Linux / macOS

# 4. Ejecutar (etapa de preprocesamiento)
python main.py preprocess
```

## Datos

El dataset crudo (`data/SegCovid19-Seguimiento_PRASS.csv`, ~46 MB) se incluye en el
repositorio. Su diccionario de datos, formato y problemas de calidad detectados se
documentan en [DATABASE.md](DATABASE.md).

## Documentación

- [WORKFLOWS.md](WORKFLOWS.md) — flujos de trabajo, comandos y convenciones.
- [DATABASE.md](DATABASE.md) — diccionario de datos y calidad del dato.

## Autor

Jabes Monroy — `jmonroyb@unal.edu.co`
