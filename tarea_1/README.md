# Tarea 1 – Noticias peruanas: del titular al clasificador

## 1. Pregunta del proyecto
¿Pueden convertir titulares peruanos en un clasificador de noticias? Para esta tarea, un clasificador de 
4 categorías (política, economía, deportes y ciencia_tecnologia)?

## 2. Medio y fechas de extracción
- **Medio:** La República (opción A), `https://larepublica.pe`.
- **Extracción:** 16 y 17 de octubre de 2026. Se usaron los RSS oficiales de política, economía, deportes
  y ciencia (59 noticias) y, como solo cubren unos 2 días, se completó siguiendo los enlaces entre notas
  (pausa de 1,5 s, tope de 100 por categoría). Tras la limpieza quedaron **399 noticias**.
- **Fechas de publicación:** 82 % de 2026 (sobre todo octubre); el resto, de 2019 a 2025.

## 3. Hallazgos
1. **El modelo entrenado de DistilBERT supera claramente al zero-shot.** DistilBERT fine-tuned obtuvo 
   F1 macro de **0,898** en test, frente a **0,56** del zero-shot. Gemini 3.8 Flash fue el más preciso (F1 0,949),
   pero es más lento y su plan gratuito permite solo 20 pedidos al día; por eso se elige DistilBERT.
2. **Los errores se concentran entre política, economía y deportes.** Ciencia y tecnología se
   clasificó perfecto (F1 1,00). Las noticias electorales se confunden con deportes por su las palabras "ganar", "lidera", y las económicas con política cuando mencionan a actores políticos como Keiko Fujimori o Municipalidad.

## 4. Limitación
1. **Datos pocos y de un solo medio.** Con 399 noticias (60 en test), las métricas varían según la
   muestra: zero-shot dio F1 0,56 con 40 titulares y 0,737 con los 60 del test.

## 5. Cómo ejecutar en local
Desde la carpeta `tarea_1`:

    uv sync
    uv run streamlit run app.py

O con pip:

    pip install -r requirements.txt
    streamlit run app.py

Antes, generar el modelo ejecutando `02_clasificacion.ipynb` (pasos 2.3 y 2.4), que lo guarda en
`modelo/`. Para el paso 2.2 (Gemini), crear un archivo `.env` con `GEMINI_API_KEY=tu_clave`.