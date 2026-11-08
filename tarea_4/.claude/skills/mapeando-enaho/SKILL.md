---
name: mapeando-enaho
description: Hace un mapa coroplético de la pobreza monetaria por departamento del Perú con la ENAHO 2024 del INEI, uniendo las cifras con los límites departamentales por código (ubigeo y FIRST_IDDP), y lo compara con la referencia de la sesión 16. Úsala cuando pidan un mapa, un coroplético o la distribución territorial de la pobreza por departamento o región con la ENAHO.
---

# Mapear la pobreza de la ENAHO 2024

1. Si no existe `salidas/personas_2024.parquet`, usa primero la skill `limpiando-enaho` y sigue solo si su
   validación sale aprobada.
2. Desde la carpeta del proyecto, corre exactamente:
   ```
   uv run .claude/skills/mapeando-enaho/scripts/mapear.py
   ```
3. Si el script termina con ERROR (faltan departamentos, hay alguno sin dato o uno difiere más de 1 punto de la
   referencia), detente y muestra el mensaje. No hagas el mapa de otra forma.
4. Responde con la ruta del mapa, el departamento con la pobreza más alta y el de la más baja, y el resumen de la
   comparación con `referencias/pobreza_departamento_2024.csv`. Explica que la referencia se calculó con la
   sumaria (`factor07 × mieperho`) y la base con los residentes habituales; por eso difieren en unas décimas.

## Reglas del mapa (el script ya las cumple; respétalas si te piden otro)

- Une por código: `ubigeo[:2]` con `FIRST_IDDP`, los dos como texto de dos dígitos. Nunca por nombre:
  «APURIMAC» no es «Apurímac».
- Exige 25 departamentos y ninguno sin dato. Lima (`15`) y Callao (`07`) van separados.
- Un solo color, de claro a oscuro, con la escala desde 0; nunca arcoíris.
- Leyenda con la unidad: % de personas. Título con las cifras calculadas y fuente al pie.
- PNG a 200 dpi en `mapas/pobreza_departamento_2024.png`; la comparación va a `salidas/comparacion_referencia.csv`.

## Archivos de esta skill

- `geo/peru_departamental_simple.geojson`: límites de los 25 departamentos (sesión 06 del curso), con `FIRST_IDDP`.
- `referencias/pobreza_departamento_2024.csv`: la pobreza de cada departamento según la sesión 16.
