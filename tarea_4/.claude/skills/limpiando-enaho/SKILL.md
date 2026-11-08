---
name: limpiando-enaho
description: Limpia y une los módulos 34 (sumaria) y 02 (miembros del hogar) de la ENAHO 2024 del INEI, filtra a los residentes habituales y arma una base de personas con pobreza monetaria, departamento, área, sexo, edad y factor de expansión, validada contra las cifras oficiales. Úsala cuando pidan limpiar, preparar o unir la ENAHO, calcular la pobreza del Perú (nacional, urbana, rural, por departamento, sexo o edad) o cuando otra skill necesite salidas/personas_2024.parquet y no exista.
---

# Limpiar la ENAHO 2024

Sale `salidas/personas_2024.parquet`: una fila por residente habitual (108,664), con la pobreza de su hogar y su
factor de expansión `facpob07`.

## Pasos

1. Revisa que existan `datos/966-Modulo34.zip` y `datos/966-Modulo02.zip`. Si falta alguno, detente y pide al
   usuario bajarlo del INEI (966 es el código de la ENAHO 2024) y guardarlo en `datos/` sin descomprimir:
   - https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip
   - https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip
2. Desde la carpeta del proyecto, corre exactamente:
   ```
   uv run .claude/skills/limpiando-enaho/scripts/limpiar.py
   ```
   No reescribas la limpieza ni la hagas a mano: las llaves, el filtro, la unión y las validaciones están en el script.
3. Lee `salidas/validacion.txt`. Si el script terminó con ERROR o una verificación esencial dice FALLIDA, detente,
   di cuál falló y no entregues cifras. Nunca cambies datos ni tolerancias para que coincidan con la referencia.
4. Para responder, toma las cifras de `salidas/indicadores.csv` (nacional, área, sexo, grupo de edad y departamento).
   Si piden otro corte, calcúlalo sobre el parquet ponderando con `facpob07`; nunca con un promedio simple.
5. Al dar una cifra, di el periodo (2024), la unidad (% de personas), que está ponderada con `facpob07` y la fuente
   (INEI, ENAHO 2024). Si la comparan con la cifra oficial del INEI, explica la diferencia de unas décimas con la
   nota final de `validacion.txt`.
6. Antes de usar una variable que no está en la base, lee [reference.md](reference.md).
