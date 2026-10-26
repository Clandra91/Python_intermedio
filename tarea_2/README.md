# Tarea 2 – Voces y documentos peruanos: del archivo escaneado al texto buscable

**Dashboard público:** https://trabajo-voces-documentos-capp.streamlit.app/

## Pregunta del proyecto
¿Pueden convertirse documentos escaneados y entrevistas en audio en un archivo de texto estructurado y buscable?

## Corpus, fuentes y licencias
| Corpus | Contenido | Fuente y licencia | Fecha |
|---|---|---|---|
| A. Documentos (25) | 8 impresos: páginas de un trabajo de licenciatura de la autora | Documento propio, uso autorizado | Capturas: 21/10/2026 |
| | 8 fotos con sombra o inclinación: *Estudio de Gobiernos Locales 2016* | SERVIR ([PDF oficial](https://cdn.www.gob.pe/uploads/document/file/1206414/Estudio-de-Gobiernos-Locales-2016-SERVIR.pdf)); fotos propias, uso académico citando la fuente | Fotos: 21/10/2026 |
| | 9 manuscritos: apuntes de clase de la autora | Documento propio, uso autorizado | Fotos: 21/10/2026 |
| B. Audio (26 clips, 37,0 min) | Conversación con la hermana de la autora (6 clips, TV de fondo), conversación de trabajo (8 clips, 2 personas) y conversación familiar (12 clips, 4 personas) | Grabaciones propias con consentimiento de todas las personas que hablan | Grabación: 21 al 23/10/2026 |

- Extracción: OCR el 22/10/2026; transcripción y diarización del 22 al 23/10/2026; evaluación y extracción con LLM, el 24 y 25/10/2026.
- El detalle por archivo (URL, licencia y acceso) está en `datos/fuentes.csv`.
- Los nombres reales se reemplazaron por seudónimos (`[PERSONA_n]`, `[APELLIDO]`): 28 menciones de 12 entidades. Las imágenes, los audios originales y las transcripciones crudas están en `datos/raw/`, que no se publica (`.gitignore`). Las personas autorizaron la grabación, no la publicación de su voz; por eso el dashboard muestra solo texto.

## Método
1. **`01_extraccion.ipynb`:** OCR con PaddleOCR 3.7 (PP-OCRv6 medium, `lang="es"`, con clasificador de orientación); ASR con faster-whisper `small` (int8, CPU) y VAD; diarización con WeSpeaker + k-means; seudonimización, limpieza, EDA y exportación a CSV.
2. **`02_evaluacion.ipynb`:** referencias manuales de 10 documentos y 10 clips; CER y WER de la línea base y de los modelos alternativos (Tesseract 5.5 y Qwen3-ASR 0.6B); extracción de campos en JSON con Claude Opus 5.5 y auditoría humana de 20 casos.
3. **`app.py`:** dashboard en Streamlit que solo lee los CSV de `datos/`.

## Resultados (muestra de evaluación)
| Modalidad | Modelo | Métrica | Resultado | Latencia (CPU) |
|---|---|---|---|---|
| Documentos | PaddleOCR (línea base) | CER | 0,402 | 60–216 s por imagen |
| Documentos | Tesseract 5.5 | CER | 0,500 | ≈6 s por imagen |
| Audio | faster-whisper `small` (línea base) | WER | 0,423 | RTF 1,00 |
| Audio | Qwen3-ASR 0.6B | WER | 0,400 | RTF 1,96 |
| Extracción | Claude Opus 5.5 | Acuerdo con la auditoría | 19/20 (95 %) | ≈15–20 s por lote |

## Hallazgos
1. **El CER castiga el orden de lectura, no solo los errores de lectura.** En las fotos de páginas a dos columnas, PaddleOCR recupera el 97 % de las palabras, pero intercala las columnas, y su CER sube a 0,65. Tesseract respeta las columnas en una página derecha (CER 0,05), pero no lee la foto inclinada (0,98) ni los manuscritos (0,86 frente a 0,30 de PaddleOCR). En los impresos limpios, los dos son casi perfectos. Para un uso real conviene un esquema mixto: Tesseract para los impresos limpios y PaddleOCR para las fotos y los manuscritos.
2. **En el audio pesan más la jerga y las voces superpuestas que el ruido de fondo.** Los clips con la TV encendida tuvieron el menor WER (0,33), mientras que la conversación de trabajo, con nombres de sistemas y siglas, fue la más difícil (0,45). Whisper y Qwen quedaron prácticamente empatados (0,42 frente a 0,40), pero Whisper es el doble de rápido y entrega tiempos y puntuación. El LLM acertó en 19 de 20 extracciones, y su único error vino de una palabra mal transcrita ("a Zaire" en vez de "ASAI").

## Limitaciones
1. **Muestra pequeña y referencias de una sola persona:** 10 documentos y 10 clips no bastan para afirmar que una diferencia de 2 puntos de WER sea real, y el CER depende de cómo se ordenó la referencia en las páginas de dos columnas.
2. **Hardware y servicios:** todo corrió en una CPU de 2 núcleos, sin GPU. PaddleOCR tardaba hasta 13 minutos por foto, hasta que se desactivó oneDNN (error de PaddlePaddle) y se limitó la detección a 1600 px; Qwen3-ASR tarda el doble que la duración del audio. La diarización con k-means necesita saber cuántas personas hablan, y con voces superpuestas reparte a una misma persona en dos marcas. Además, la API gratuita de Gemini falló por saturación y cuota agotada, así que se usó la API de pago de Claude (menos de US$ 1).

## Cómo ejecutarlo en local
Dashboard (solo necesita los CSV de `datos/`):
```bash
cd tarea_2
pip install -r requirements.txt
streamlit run app.py