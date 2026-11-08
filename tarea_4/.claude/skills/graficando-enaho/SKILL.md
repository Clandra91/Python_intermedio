---
name: graficando-enaho
description: Hace gráficos de barras de la pobreza monetaria del Perú con la ENAHO 2024 del INEI, por área urbana y rural, sexo, grupo de edad o departamento, ponderados con el factor de expansión y guardados en figuras/. Úsala cuando pidan graficar, visualizar o comparar en un gráfico la pobreza entre grupos de personas o entre regiones con la ENAHO.
argument-hint: "[area|sexo|edad|departamento|todos]"
---

# Graficar la pobreza de la ENAHO 2024

1. Si no existe `salidas/personas_2024.parquet`, usa primero la skill `limpiando-enaho` y sigue solo si su
   validación sale aprobada.
2. Elige el corte según el pedido. Si lo invocan como `/graficando-enaho $ARGUMENTS`, usa ese corte.

   | Si piden | Corte |
   |---|---|
   | urbano y rural, área, ciudad y campo | `area` |
   | hombres y mujeres, sexo, género | `sexo` |
   | edad, niñas y niños, jóvenes, adultos mayores | `edad` |
   | departamentos, regiones, ranking territorial | `departamento` |
   | varios cortes o «todos los gráficos» | `todos` |

3. Desde la carpeta del proyecto, corre exactamente:
   ```
   uv run .claude/skills/graficando-enaho/scripts/graficar.py --por <corte>
   ```
4. Responde con la ruta del PNG y las cifras que imprime el script, sin recalcularlas. Di que son % de personas
   en 2024, ponderadas con `facpob07`, y que la fuente es INEI, ENAHO 2024. Describe las diferencias, sin decir
   que un grupo es pobre *por* ser de ese grupo: son asociaciones, no causas.

## Reglas de cada gráfico (el script ya las cumple; respétalas si te piden uno nuevo)

- Pondera siempre con `facpob07`; nunca un promedio simple.
- Barras que empiezan en cero, ordenadas de mayor a menor (la edad conserva su orden natural).
- Un solo color y el valor escrito al final de cada barra; la línea punteada marca el promedio nacional.
- El título dice qué muestra, con las cifras calculadas; el subtítulo da el indicador, el periodo y la unidad.
- Nota al pie: «Fuente: INEI, ENAHO 2024», con el factor usado.
- PNG a 200 dpi en `figuras/`, con nombre `enaho_pobreza_por_<corte>_2024.png`.
