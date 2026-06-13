# -*- coding: utf-8 -*-
"""Genera el informe PDF del proyecto PRASS (reportlab).

Reproduce el resumen de las etapas (exploración, preprocesamiento, EDA) y añade
las etapas de justificación de la dispersión (conglomerados) y de modelado
(GLM binomial y su redefinición). Las cifras provienen del cuaderno
`Proyecto_PRASS_Seguimiento_COVID19.ipynb`. Ejecutar:  python generar_informe.py
"""
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem,
)

SALIDA = "Informe_PRASS_Seguimiento_COVID19.pdf"
AZUL = colors.HexColor("#1F4E79")
AZUL_CLARO = colors.HexColor("#D9E1F2")
GRIS = colors.HexColor("#666666")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=20, leading=24,
                    textColor=colors.black, alignment=TA_CENTER, spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, leading=12,
                     textColor=GRIS, alignment=TA_CENTER)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=13, leading=16,
                    textColor=AZUL, spaceBefore=14, spaceAfter=6)
BODY = ParagraphStyle("BODY", parent=ss["Normal"], fontSize=9.5, leading=13,
                      alignment=TA_JUSTIFY, spaceAfter=4)
CELL = ParagraphStyle("CELL", parent=ss["Normal"], fontSize=8.5, leading=11)
CELLH = ParagraphStyle("CELLH", parent=ss["Normal"], fontSize=8.5, leading=11,
                       textColor=colors.white, fontName="Helvetica-Bold")


def P(t):
    return Paragraph(t, BODY)


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(t, BODY), leftIndent=10, value="●") for t in items],
        bulletType="bullet", start="●", leftIndent=12,
    )


def tabla(filas, anchos):
    data = [[Paragraph(c, CELLH) for c in filas[0]]]
    data += [[Paragraph(c, CELL) for c in fila] for fila in filas[1:]]
    t = Table(data, colWidths=anchos, repeatRows=1)
    st = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFBFBF")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(filas)):
        if i % 2 == 0:
            st.append(("BACKGROUND", (0, i), (-1, i), AZUL_CLARO))
    t.setStyle(TableStyle(st))
    return t


flow = []
A = flow.append

# ----------------------------- Encabezado ---------------------------------- #
A(Paragraph("Proyecto PRASS: Seguimiento al COVID-19", H1))
A(Paragraph("Especialización en Analítica y Ciencia de Datos - Fundamentos de Ciencia de Datos", SUB))
A(Paragraph("Autor: Jabes Monroy", SUB))
A(Paragraph("Fuente: Portal de Datos Abiertos de Colombia (datos.gov.co), conjunto r6r5-w84k. "
            "Informe resumen de las etapas de exploración, preprocesamiento, análisis exploratorio y modelado.", SUB))
A(Spacer(1, 0.3 * cm))

# 1. Datos y objetivo
A(Paragraph("1. Datos y objetivo", H2))
A(P("El conjunto registra el seguimiento epidemiológico del programa PRASS (Pruebas, Rastreo y "
    "Aislamiento Selectivo Sostenible) en Colombia. Cada fila es un agregado por fuente, fecha, "
    "departamento, municipio y entidad reportante, con el número de casos y cuántos recibieron "
    "seguimiento. Volumen: <b>339.646 registros y 12 variables</b>, sin valores faltantes. El objetivo "
    "analítico es cuantificar la <b>cobertura de seguimiento</b> e identificar brechas por fuente, "
    "territorio y entidad. Todo el trabajo se desarrolla en un cuaderno único que importa el módulo "
    "<i>utils.py</i> con las funciones reutilizables."))

# 2. Parte I
A(Paragraph("2. Parte I - Exploración y evaluación de calidad", H2))
A(P("Diagnóstico del dato crudo mediante las siguientes técnicas:"))
A(tabla([
    ["Técnica", "En qué consiste y qué se obtuvo"],
    ["Estructura y tipos (info, dtypes)", "Inspección de columnas y tipos. 12 variables; medias muy superiores a las medianas, primer indicio de asimetría."],
    ["Estadísticos descriptivos (describe)", "Resumen de posición y dispersión. Mediana de casos entre 1 y 2; máximo 31.654 (cola larga)."],
    ["Datos faltantes (isna)", "Conteo de nulos por variable. Resultado: 0 nulos, no se requiere imputación."],
    ["Duplicados (duplicated)", "Filas completamente repetidas. Resultado: 0 duplicados."],
    ["Unicidad y categorías (nunique)", "Cardinalidad por variable. Fuente: 3; Departamento: 33; Municipio: 1.121; Entidad: 68."],
    ["Inconsistencias de texto (strip, regex)", "Espacios al borde y dobles. EntidadRegistro tiene espacios dobles, sin crear categorías nuevas."],
    ["Varianza nula (std=0)", "Detección de columnas constantes. FechaCorte es constante (sin información) -> a eliminar."],
    ["Outliers (IQR / boxplot)", "Valores fuera de [Q1-1.5*IQR, Q3+1.5*IQR]. ~13% atípicos, pero reflejan el sesgo natural de conteo, no errores."],
    ["Coherencia de conteos", "Identidad total = con + sin seguimiento. Se cumple en el 100% de los registros."],
    ["Calidad de porcentajes", "Las columnas de porcentaje están corruptas (100% codificado como 1e22). Decisión: recalcular desde conteos."],
    ["Test de Little (MCAR)", "Evalúa si los faltantes son completamente aleatorios. No aplica: no hay datos faltantes."],
], [5.2 * cm, 11.3 * cm]))

# 3. Parte II
A(Paragraph("3. Parte II - Preprocesamiento", H2))
A(P("Transformaciones derivadas de la exploración, encapsuladas en <i>utils.preprocesar</i>:"))
A(tabla([
    ["Técnica", "En qué consiste y qué se obtuvo"],
    ["Tipado de fecha (to_datetime)", "FechaRegistro de texto a fecha. Rango cubierto: 2020-05-04 a 2022-05-18."],
    ["Separación código/nombre (split)", "Departamento y Municipio (formato 'código - nombre') divididos en columnas *Codigo y *Nombre."],
    ["Estandarización de texto", "Recorte y colapso de espacios en EntidadRegistro (0 espacios dobles tras el proceso)."],
    ["Recálculo de cobertura", "CoberturaConSeguimiento = con/total*100, en reemplazo de los porcentajes corruptos. Rango coherente [0,100]."],
    ["Eliminación de columnas", "Se descartan FechaCorte (constante), los porcentajes corruptos y los campos territoriales originales."],
    ["Diagnóstico y conversión de tipos", "Se distinguen identificadores (códigos DIVIPOLA, se conservan como categoría) de numéricas. Categóricas a 'category' y semana ordinal."],
], [5.2 * cm, 11.3 * cm]))
A(P("Resultado: <b>df_prep con 13 variables tipadas y sin nulos</b>, listo para el análisis."))

# 4. Parte III
A(Paragraph("4. Parte III - Análisis exploratorio (EDA)", H2))
A(P("La cobertura agregada se calcula <b>ponderada por casos</b> (sum(con)/sum(total)), que refleja la "
    "cobertura real del sistema y no sobrerrepresenta a los grupos pequeños."))
A(tabla([
    ["Técnica", "En qué consiste y qué se obtuvo"],
    ["Distribuciones (histogramas log, KDE)", "Forma de las variables. Conteos con fuerte asimetría positiva; cobertura concentrada en 100%."],
    ["Univariado categórico (pie, barras)", "Composición. Predominio de CONFIRMADOS; concentración en Antioquia/Cundinamarca y en NUEVA EPS y Sanitas."],
    ["Cobertura global ponderada", "Sobre 3.532.353 casos: 94,4% ponderada frente a 92,0% del promedio simple (los grupos grandes cubren mejor)."],
    ["Bivariado categórico (cobertura por grupo)", "Por fuente: CONFIRMADOS 96,0%, SOSPECHOSOS 79,9%, POBLACIÓN NO AFILIADA 75,5%. Heterogeneidad por territorio y entidad."],
    ["Bivariado numérico (correlación, scatter)", "Correlaciones lineales con la cobertura débiles (máx |0,12|): la relación es no lineal por la saturación en 100%."],
    ["Cruce de categorías (heatmap Depto x Fuente)", "Las brechas surgen de la interacción territorio-fuente, no de un solo factor."],
    ["Análisis temporal (serie mensual)", "El volumen dibuja las olas epidémicas; la cobertura se mantuvo alta y estable durante los picos."],
], [5.6 * cm, 10.9 * cm]))

# 5. Parte III.B - Dispersion estructural
A(Paragraph("5. Parte III.B - ¿La dispersión de la cobertura es estructural?", H2))
A(P("Antes de afirmar que la cobertura tiene alta dispersión se investiga su causa con un análisis no "
    "supervisado. Se agrupan los grupos (K-Means) por su perfil —cobertura, tamaño en escala "
    "logarítmica y fuente, estandarizados— y luego se predice el conglomerado con un árbol de decisión, "
    "que mide cuán diferenciados están y por cuáles características."))
A(tabla([
    ["Conglomerado (k=4)", "% casos", "Cobertura ponderada"],
    ["Régimen dominante (CONFIRMADOS)", "88,6%", "97,5%"],
    ["Brecha dura (CONFIRMADOS)", "2,7%", "12,4%"],
    ["SOSPECHOSOS SIVIGILA", "7,6%", "90,2%"],
    ["POBLACIÓN NO AFILIADA", "1,1%", "75,5%"],
], [9.0 * cm, 3.0 * cm, 4.5 * cm]))
A(Spacer(1, 0.15 * cm))
A(P("El árbol predice el conglomerado con <b>exactitud ≈ 0,999</b>: los grupos están netamente "
    "diferenciados. Las características que los separan son la <b>fuente</b> (importancia ≈ 0,56) y la "
    "<b>cobertura</b> (≈ 0,44); el <b>tamaño no aporta</b> (0,000). El eta-cuadrado de la cobertura entre "
    "conglomerados es <b>0,886</b>. Conclusión: la dispersión es <b>estructural, no ruido</b>; su causa es "
    "el origen del caso combinado con el régimen de cobertura (coexisten un bloque casi totalmente "
    "seguido y un bloque de brecha dura). Esto justifica modelar y no solo describir."))
A(P("<b>Peso de las variables antes del modelo</b> (reducción de devianza de un GLM binomial de un solo "
    "factor): Fuente explica 12,1% de la devianza con solo 2 grados de libertad (el más eficiente); "
    "EntidadRegistro 35,7% (67 gl, alta cardinalidad); Departamento 5,0% (32 gl); y la semana 0,3% "
    "(irrelevante). Fundamenta los predictores del modelo."))

# 6. Parte IV - Modelado
A(Paragraph("6. Parte IV - Modelado: GLM binomial de la cobertura", H2))
A(P("En lugar de modelar el porcentaje de cobertura (saturado en 100%), se modela la probabilidad de "
    "que un caso reciba seguimiento: de N casos de un grupo, k son seguidos, con k ~ Binomial(N, p). "
    "La familia se elige por el tipo de respuesta (un conteo acotado de éxitos sobre ensayos):"))
A(tabla([
    ["Familia", "Soporte", "¿Adecuada aquí?"],
    ["Normal", "Real continuo", "No: la cobertura está acotada en [0,100] y es heterocedástica."],
    ["Gamma", "Real positivo", "No: para magnitudes positivas continuas."],
    ["Poisson", "Enteros sin tope", "No: k está acotado por N; interesa la proporción k/N."],
    ["Binomial", "0...N éxitos", "Sí: proceso exacto k éxitos en N ensayos; pondera por N; enlace logit en rango."],
], [3.0 * cm, 3.6 * cm, 9.9 * cm]))
A(Spacer(1, 0.15 * cm))
A(P("<b>Modelo base.</b> GLM binomial con enlace logit y predictores Fuente, Departamento, Entidad y "
    "semana, ponderado por N. Pseudo-R2 por devianza ≈ 0,51 y estadístico de dispersión ≈ 2,8 "
    "(sobredispersión). Odds ratio de SOSPECHOSOS ≈ 0,09 frente a CONFIRMADOS (once veces menos "
    "probabilidad de seguimiento). POBLACIÓN NO AFILIADA, con menor cobertura marginal, presenta un OR "
    "ajustado mayor que 1: un caso de paradoja de Simpson revelado al controlar por territorio y "
    "entidad. En prueba, el Brier score (≈ 0,042) mejora frente al baseline (≈ 0,055) y el AUC-ROC ≈ "
    "0,88; con desbalance, la especificidad para detectar la brecha es baja (≈ 0,21) al umbral 0,5."))
A(P("<b>Modelo redefinido a partir de los conglomerados.</b> Como el clustering mostró que la brecha "
    "vive en la interacción fuente-territorio, se añade el término <b>Fuente × Departamento</b> (solo en "
    "celdas con soporte y no saturadas, para evitar separación) y se ajusta como <b>quasi-binomial</b> "
    "(escala fijada en la dispersión de Pearson, errores estándar honestos ante la sobredispersión)."))
A(tabla([
    ["Modelo", "Pseudo-R2", "Dispersión", "Brier (prueba)"],
    ["Base (Fuente + Depto + Entidad)", "0,514", "2,77", "0,0425"],
    ["Redefinido (+ Fuente × Depto, quasi)", "0,529", "2,94", "0,0421"],
], [7.6 * cm, 3.0 * cm, 3.0 * cm, 2.9 * cm]))
A(Spacer(1, 0.15 * cm))
A(P("La interacción mejora el ajuste de forma <b>moderada</b> (pseudo-R2 y Brier algo mejores), pero la "
    "<b>sobredispersión persiste</b> (~2,9): no proviene de un término faltante sino de heterogeneidad "
    "intrínseca entre grupos. Por eso la redefinición correcta es doble: el quasi-binomial corrige la "
    "inferencia (errores estándar) y, como fondo estructural, se recomienda un modelo jerárquico "
    "(beta-binomial / GLMM con efectos aleatorios por territorio y entidad), que el propio análisis de "
    "conglomerados ya motivaba."))

# 7. Hallazgos principales
A(Paragraph("7. Hallazgos principales", H2))
A(bullets([
    "Cobertura global del <b>94,4%</b> (ponderada por casos); el promedio simple (92,0%) la subestima.",
    "La <b>fuente</b> es el factor más discriminante: confirmados 96,0% frente a sospechosos 79,9% y no afiliados 75,5%.",
    "La dispersión de la cobertura es <b>estructural</b>: cuatro regímenes nítidos (eta-cuadrado 0,886; árbol con exactitud 0,999), separados por fuente y por la existencia de un bloque de brecha dura.",
    "El modelo binomial confirma la brecha por fuente (OR sospechosos ≈ 0,09) y revela una paradoja de Simpson en la población no afiliada al controlar por territorio y entidad.",
    "La sobredispersión (~2,8-2,9) persiste pese a la interacción fuente-territorio: hay heterogeneidad intrínseca entre grupos que exige quasi-binomial y, como fondo, un modelo jerárquico.",
    "El seguimiento se sostuvo a lo largo de las olas epidémicas del periodo 2020-2022.",
]))

# 8. Conclusiones
A(Paragraph("8. Conclusiones y próximos pasos", H2))
A(P("El sistema PRASS alcanzó una cobertura global alta, pero con brechas claras y persistentes en la "
    "población no afiliada y en los casos sospechosos, además de diferencias territoriales y por "
    "entidad. La calidad del dato es buena (sin faltantes ni duplicados, conteos coherentes), salvo las "
    "columnas de porcentaje del origen, corregidas mediante recálculo. El análisis no supervisado "
    "demostró que la dispersión de la cobertura responde a una estructura, y el modelado la formalizó: "
    "un GLM binomial ponderado, redefinido con la interacción fuente-territorio y ajustado como "
    "quasi-binomial, explica e identifica las brechas de forma interpretable y calibrada. El próximo "
    "paso es un modelo jerárquico (beta-binomial / GLMM) que capture la heterogeneidad residual entre "
    "territorios y entidades, y la priorización accionable de las brechas detectadas."))

doc = SimpleDocTemplate(
    SALIDA, pagesize=LETTER,
    leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    title="Informe PRASS - Seguimiento COVID-19", author="Jabes Monroy",
)
doc.build(flow)
print(f"PDF generado: {SALIDA}")
