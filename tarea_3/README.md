# Tarea 3 – Capacidades municipales y necesidad de apoyo sobre el SISFOH

**Dashboard público:** https://municipalidades-sisfoh.streamlit.app/

**Publicación de LinkedIn:** PENDIENTE

> Análisis personal con datos públicos; no representa la posición del MIDIS.

## 1. Tema y pregunta de investigación

**Tema:** las municipalidades, a través de sus Unidades Locales de Empadronamiento (ULE), son el brazo operativo del Sistema de Focalización de Hogares (SISFOH): reciben las solicitudes de Clasificación Socioeconómica (CSE), recogen la información de los hogares, la digitan y firman las declaraciones juradas. Para hacerlo bien, necesitan personal capacitado y recursos (Pérez Pardo, 2025).

**Pregunta:** ¿Las municipalidades con menos capacidades (conectividad, equipos, personal estable) son las que más requieren capacitación y asistencia técnica sobre la operatividad del SISFOH? Perú, 2024–2026.

**Hipótesis:** las municipalidades sin conexión fija a internet, con pocas computadoras o con personal mayoritariamente temporal declaran con más frecuencia que requieren capacitación o asistencia técnica.

## 2. Descripción del proyecto

El proyecto tiene tres productos:

1. **Análisis** (`01_procesamiento.ipynb`): obtención, revisión de calidad y limpieza de los datos, construcción de indicadores y de un índice de capacidad municipal, hallazgos y limitaciones.
2. **Dashboard** (`dashboard/app.py`, en Streamlit): 5 KPIs; mapa y ranking por departamento; gráficos de evolución, nivel de capacidad, participación en la MCLCP y componentes del índice; filtros por edición, tipo de municipalidad, tipo de apoyo, ubigeo, departamento, provincia y distrito, y un botón para limpiar los filtros. Incluye pestañas con la definición del problema, los hallazgos, la metodología, las limitaciones y los datos filtrados para descargar.
3. **Reel** (`reel/`): video vertical (1080 × 1920) con narración generada a partir de la voz de la autora, gráficos y mapas, subtítulos y música de fondo.

```text
tarea_3/
├── 01_procesamiento.ipynb        # Parte 1: datos, indicadores, hallazgos y limitaciones
├── pyproject.toml, uv.lock       # entorno del análisis y del dashboard (uv, Python 3.12)
├── datos/
│   ├── originales/               # bases .dta del INEI (no se publican, ver sección 3)
│   ├── diccionarios/             # diccionarios de variables del RENAMU 2024, 2025 y 2026
│   ├── procesados/               # renamu_indicadores_2024_2026.csv y vaso_de_leche_2024_2026.csv
│   └── geo/                      # límites departamentales (GeoJSON)
├── dashboard/
│   ├── app.py                    # dashboard en Streamlit
│   ├── problema.md               # texto de la pestaña "Definición del problema"
│   └── requirements.txt          # dependencias para Streamlit Community Cloud
└── reel/
    ├── guion.json                # guion de 7 escenas
    ├── imagenes.py, imagenes/    # gráficos, mapas y captura del dashboard usados en el video
    ├── mi_reel.py                # voz clonada + imágenes + subtítulos + música
    └── reel.py, hacer_reel.py, guion.py   # scripts de la sesión 15 del curso
```

## 3. Fuentes de datos y metodología

**Fuente:** Registro Nacional de Municipalidades (RENAMU), Formulario 01, ediciones 2024, 2025 y 2026, del Instituto Nacional de Estadística e Informática (INEI, 2024, 2025, 2026). Se descargó el 27/10/2026 del [portal de microdatos del INEI](https://proyectos.inei.gob.pe/microdatos/). Las bases originales no se publican porque incluyen datos de contacto de los alcaldes; la sección 1.2 del notebook explica cómo obtenerlas. Los límites departamentales son una versión simplificada de los del INEI, usada en la sesión 06 del curso.

**Cobertura:** las mismas 1 891 municipalidades en cada edición (196 provinciales y 1 695 distritales), es decir, 5 673 registros. Se excluye Santa Rosa de Loreto, que solo aparece en la edición 2026.

**Indicadores:**

- **Requiere apoyo:** la municipalidad declara que requiere asistencia técnica (`P22_AT23`) o capacitación (`P22_C23`) sobre el SISFOH (pregunta 22).
- **Índice de capacidad (0 a 3):** suma de tres componentes: (1) conexión fija a internet (Wi-Fi, ADSL/DSL o fibra óptica); (2) al menos 0,5 computadoras por trabajador; (3) al menos 50 % de personal estable (nombrados del D. Leg. 276 y personal del D. Leg. 728). Capacidad **baja** (0–1), **media** (2) o **alta** (3).
- **Contexto:** participación en la Mesa de Concertación para la Lucha contra la Pobreza (MCLCP, `P101_4`). El número de beneficiarios del Vaso de Leche (`P60B_T_1`) se guarda en una tabla aparte para análisis futuros.

El análisis es descriptivo: compara el porcentaje que requiere apoyo según el nivel de capacidad, cada componente del índice, el año y el departamento.

## 4. Hallazgos principales

1. **La necesidad es generalizada y persistente.** Cerca de 8 de cada 10 municipalidades declaran requerir capacitación o asistencia técnica sobre el SISFOH (79,2 % en 2024, 80,4 % en 2025 y 77,0 % en 2026). La capacitación es la necesidad más frecuente (entre 68 % y 73 %), por encima de la asistencia técnica (alrededor de 60 %). El 53,9 % lo declaró en las tres ediciones y solo el 2,8 % en ninguna.
2. **El nivel de capacidad no marca la diferencia.** En todos los niveles y años, entre 74 % y 82 % requiere apoyo, sin un patrón claro. Tener o no conexión fija, suficientes computadoras o mayoría de personal estable cambia la necesidad en menos de 3 puntos. La hipótesis no se confirma.
3. **El territorio pesa más que la capacidad.** En el promedio 2024–2026, la necesidad va de 72,3 % en Áncash a 88,4 % en Ayacucho: una brecha de 16 puntos, frente a menos de 6 puntos entre niveles de capacidad.

**Análisis complementario:** las municipalidades que participan en la MCLCP tienen casi la misma distribución de capacidad que las que no participan (alrededor de 27 % baja, 54 % media y 19 % alta) y requieren apoyo en una proporción parecida (81,6 % frente a 77,8 %).

**Respuesta:** no. Las municipalidades con menos capacidades no requieren más capacitación o asistencia técnica que las demás; la necesidad es alta en todos los niveles.

## 5. Limitaciones

1. **Necesidad declarada:** la pregunta 22 recoge lo que la municipalidad declara requerir, no su desempeño en el SISFOH; además, quien responde el RENAMU no necesariamente es el personal de la ULE.
2. **Capacidades de toda la municipalidad**, no de la ULE: desde 2018, el RENAMU no incluye un módulo sobre la ULE.
3. **Personal estable:** es una aproximación según el régimen laboral; puede subestimarse (excluye al personal CAS) o sobrestimarse (incluye a todo el personal del D. Leg. 728).
4. **Información faltante:** 307 registros (5,4 %), todos de municipalidades distritales, no tienen información de personal y no reciben índice.
5. **Umbrales del índice:** son decisiones de la autora; el resultado se mantiene al analizar cada componente por separado.
6. **Asociación, no causalidad:** no se controlan otros factores, como la pobreza, la población o la ruralidad del distrito.
7. **Pocos casos:** en Callao (7), Madre de Dios (11) y Tumbes (13), los porcentajes cambian mucho con pocas municipalidades.
8. **Periodo de referencia:** el personal corresponde al 31 de diciembre del año anterior a cada edición; la necesidad de apoyo, al momento de la encuesta.

## 6. Enlaces

- Dashboard: https://municipalidades-sisfoh.streamlit.app/
- Publicación de LinkedIn (con el reel): PENDIENTE
- Repositorio: https://github.com/Clandra91/Python_intermedio/tree/main/tarea_3

## 7. Cómo reproducir el proyecto

Se usa [uv](https://docs.astral.sh/uv/) con Python 3.12. Los comandos son para PowerShell (Windows).

**Análisis:**

1. Descargar las tres bases del RENAMU y guardarlas en `datos/originales/` como `renamu_2024.dta`, `renamu_2025.dta` y `renamu_2026.dta` (detalle en la sección 1.2 del notebook).
2. Crear el entorno e instalar las dependencias:
   ```powershell
   cd tarea_3
   uv sync
   ```
3. Abrir `01_procesamiento.ipynb` con el kernel de `.venv` y ejecutar todas las celdas. Se generan los CSV de `datos/procesados/`.

**Dashboard** (solo necesita los archivos de `datos/procesados/` y `datos/geo/`, que sí están en el repositorio):

```powershell
cd tarea_3
uv run streamlit run dashboard/app.py
```

Sin uv: `pip install -r dashboard/requirements.txt` y luego `streamlit run dashboard/app.py`.

**Reel:**

```powershell
cd tarea_3
uv run python reel/imagenes.py      # gráficos y mapas del video
cd reel
uv venv --python 3.12
uv pip install --python .venv\Scripts\python.exe qwen-tts faster-whisper pillow imageio-ffmpeg soundfile jiwer num2words pypdf
.venv\Scripts\python.exe mi_reel.py # unos 40 minutos en CPU; el video queda en reel/salidas/reel.mp4
```

Antes de ejecutar `mi_reel.py`, hay que grabar la propia voz (15 a 25 segundos) en `reel/mi_voz.m4a` y guardar una música con licencia en `reel/musica.mp3`. Ninguno de los dos archivos se publica: la grabación es un dato personal y la licencia de Pixabay no permite redistribuir el archivo de música por separado. En Windows, si la descarga de los modelos falla con `WinError 1314`, se pueden descargar antes con `huggingface_hub.snapshot_download(..., max_workers=1)`.

## 8. Uso de inteligencia artificial

- **Claude Code (Claude Opus 5.5, de Anthropic)** se usó como asistente en todas las etapas: revisar el diccionario del RENAMU, proponer y probar el código de limpieza, indicadores, gráficos y dashboard, redactar el guion del reel y revisar la redacción.
- **Qwen3-TTS 0.6B** generó la narración del reel a partir de una grabación de la voz de la autora, y **faster-whisper large-v3-turbo** generó los subtítulos.
- La autora definió el tema y la pregunta, tomó las decisiones metodológicas (por ejemplo, qué se considera conexión fija y personal estable, y la exclusión de Santa Rosa de Loreto), verificó las cifras con los datos y es responsable de los resultados.

## Créditos

- Scripts del reel (`reel.py`, `hacer_reel.py` y `guion.py`): sesión 15 del curso [Data-Science-Python](https://github.com/d2cml-ai/Data-Science-Python). `mi_reel.py` les agrega imágenes, música y la corrección de "SISFOH" en los subtítulos.
- Música: «Inspirational - Inspirational Music», de NastelBom ([Pixabay](https://pixabay.com/music/), Licencia de Contenido de Pixabay).
- Tipografías del reel: Oswald y Public Sans (Google Fonts, licencia SIL Open Font License).

## Referencias

Instituto Nacional de Estadística e Informática. (2024). *Registro Nacional de Municipalidades (RENAMU) 2024* [Conjunto de datos]. https://proyectos.inei.gob.pe/microdatos/

Instituto Nacional de Estadística e Informática. (2025). *Registro Nacional de Municipalidades (RENAMU) 2025* [Conjunto de datos]. https://proyectos.inei.gob.pe/microdatos/

Instituto Nacional de Estadística e Informática. (2026). *Registro Nacional de Municipalidades (RENAMU) 2026* [Conjunto de datos]. https://proyectos.inei.gob.pe/microdatos/

Pérez Pardo, C. A. (2025). *Reflexión sobre la operatividad del SISFOH en el marco de la implementación de la Directiva 001-2020-MIDIS* [Trabajo de suficiencia profesional, Pontificia Universidad Católica del Perú]. Repositorio de Tesis PUCP. http://hdl.handle.net/20.500.12404/32749
