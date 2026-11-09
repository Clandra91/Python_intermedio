# Evaluación del agente: sin y con el MCP del BCRP y las Skills de la ENAHO

¿Mejoran el servidor MCP del BCRP y las Skills de la ENAHO las respuestas de Claude Code? Para responderlo, se hicieron las mismas 10 preguntas en dos modos y se compararon con respuestas verificadas de antemano.

## 1. Diseño del experimento

- **Preguntas** ([`preguntas.csv`](preguntas.csv)): 4 de indicadores del BCRP, 4 de la ENAHO 2024 y 2 que combinan ambas fuentes.
- **Respuestas esperadas:** se fijaron y se subieron a GitHub (commit `2dd8c8b`) **antes** de correr la evaluación, y no se cambiaron después.
  - Las del BCRP salen de la API del banco, consultada directamente el 8 de noviembre de 2026, y se revisaron a mano en las tablas de su web.
  - Las de la ENAHO salen del procesamiento de los microdatos (`salidas/indicadores.csv`), contrastado con las cifras oficiales del INEI y con la referencia departamental del curso.
- **Tolerancias**, definidas antes de correr:
  - BCRP: ±0.05 puntos, el redondeo a dos decimales (±0.01 en la tasa de referencia).
  - ENAHO: de ±0.1 a ±0.25 puntos. El rango cubre tanto la cifra propia (residentes habituales) como la oficial del INEI (sumaria). En la pobreza nacional se usa el ±0.1 que fija el enunciado.
- **Calificación:**
  - Preguntas simples: *correcta* si la cifra cae dentro de la tolerancia, *incorrecta* si cae fuera y *no responde* si el modelo devuelve `null`.
  - Preguntas mixtas: se califican la exactitud (las dos cifras) y la coherencia de la interpretación (una pregunta de sí o no). Son *correctas* si aciertan las tres partes y *parciales* si aciertan una o dos.

## 2. Condiciones de cada modo

Las 20 llamadas se hicieron el 8 de noviembre de 2026 con `uv run evaluacion/evaluar.py` ([`evaluar.py`](evaluar.py), adaptado de la sesión 04). En los dos modos se mantuvo lo mismo:

- el modelo: Claude Haiku (`claude-haiku-5-5`), con Claude Code 2.1.319;
- la instrucción: usar las herramientas si las hay, responder con cifras y poner `null` en lugar de estimar;
- una sesión nueva de `claude -p` por pregunta (`--no-session-persistence`), para que ninguna respuesta contamine a otra.

| | Modo A: sin MCP ni Skills | Modo B: con MCP y Skills |
|---|---|---|
| Herramientas habilitadas | Ninguna (`--tools ""`). Solo la salida estructurada para dar la respuesta | `Skill`, `Read`, `Bash` y `PowerShell`, y las 4 herramientas del MCP `bcrp` |
| MCP | Ninguno (`--strict-mcp-config`) | Solo `bcrp`, de `.mcp.json`. Se conectó en las 10 llamadas |
| Skills | Desactivadas (`--disable-slash-commands`) | Las 3 del proyecto, en `.claude/skills/` |
| Web | No | No |
| Carpeta de trabajo | Una carpeta temporal fuera del proyecto | `tarea_4/` |
| Acceso a las respuestas | Imposible: no tiene herramientas ni ve el proyecto | Prohibido leer `evaluacion/`, `informes/` y `evidencias_ia/` (`--disallowedTools`) |
| Terminal | No | Solo `uv run` sin pedir permiso; el resto, solo comandos de lectura simples |
| En paralelo | 4 preguntas a la vez | De a una (en paralelo, el MCP no siempre alcanzaba a conectarse) |

La conversación completa de cada llamada está en [`evidencias_ia/evaluacion/registros/`](../evidencias_ia/evaluacion/registros/), un JSONL por pregunta y modo. El primer mensaje de cada archivo lista las herramientas habilitadas y el estado del MCP. Las respuestas, las fuentes que citó el modelo y las herramientas que usó están en [`resultados.csv`](resultados.csv).

## 3. Resultados globales

| Modo | Correctas | Parciales | Incorrectas | No responde | Errores | Tiempo promedio | Turnos promedio |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| A: sin MCP ni Skills | **1** | 2 | 0 | 7 | 0 | 9.4 s | 2.0 |
| B: con MCP y Skills | **10** | 0 | 0 | 0 | 0 | 24.5 s | 6.6 |

En el modo B, el tiempo promedio fue de 16.6 s en las preguntas del BCRP, 28.5 s en las de la ENAHO y 32.1 s en las mixtas.

## 4. Resultados por pregunta

| # | Pregunta | Esperada | Modo A | Modo B | Herramientas usadas en B | Seg. B |
|---|---|---|---|---|---|---:|
| 1 | Inflación de Lima, dic-2022 | 8.46 | 8.46 · correcta, de memoria | 8.46 · correcta | `buscar_series` ×2, `serie` | 21.5 |
| 2 | Inflación de Lima, jun-2022 | 8.81 | null · no responde | 8.81 · correcta | `buscar_series`, `serie` | 15.4 |
| 3 | Inflación de alimentos y energía, jun-2022 | 13.48 | null · no responde | 13.48 · correcta | `buscar_series`, `serie` | 15.7 |
| 4 | Tasa de referencia, dic-2024 | 5.00 | null · no responde | 5 · correcta | `buscar_series`, `serie` | 13.9 |
| 5 | Pobreza nacional 2024 | 27.53 (±0.1) | null · no responde | 27.6 · correcta | `Bash`, `Read` de las salidas de `limpiando-enaho` | 28.6 |
| 6 | Pobreza rural 2024 | 39.44 (±0.2) | null · no responde | 39.3 · correcta | `buscar_series` (0 series), `Bash`, `Read` de las salidas | 20.1 |
| 7 | Pobreza en Cajamarca 2024 | 44.99 (±0.2) | null · no responde | 45 · correcta | `Bash`, `Read` de las salidas y de la referencia de `mapeando-enaho` | 30.2 |
| 8 | Pobreza en Ica 2024 | 5.91 (±0.15) | null · no responde | 5.91 · correcta | Skill `limpiando-enaho`, `limpiar.py`, cálculo ponderado sobre el parquet | 35.1 |
| 9 | Inflación dic-2024 + pobreza del departamento de Lima + ¿causalidad? | 1.97 · 26.89 · no | null · null · no → parcial | 1.97 · 26.89 · no · correcta | `buscar_series`, `serie`, cálculo ponderado sobre el parquet | 37.8 |
| 10 | Inflación de alimentos y energía dic-2024 + pobreza urbana + ¿solo Lima Metropolitana? | 1.23 · 24.74 · sí | null · null · sí → parcial | 1.23 · 24.8 · sí · correcta | `buscar_series` ×2, `serie`, `Bash` de las salidas | 26.3 |

**Preguntas que mejoraron:** 9 de 10 (de la 2 a la 10): pasaron de *no responde* o *parcial* a *correcta*. **Se mantuvo:** la 1, correcta en los dos modos. **Empeoraron:** ninguna.

## 5. Principales errores y comportamientos observados

**Modo A (sin herramientas)**

- **No inventó cifras, pero casi no respondió.** En 7 preguntas devolvió `null` y explicó que no podía consultar fuentes oficiales. No hubo respuestas incorrectas: el modelo respetó la instrucción de no estimar.
- **El único acierto no es verificable.** En la pregunta 1 dio 8.46 «de mi conocimiento previo, que coincide con el dato publicado por el INEI»: no dio el código de la serie y atribuyó la cifra a otra institución. Además, la respuesta de memoria no es estable: en una prueba del script hecha antes, en una copia del proyecto, respondió `null` en esa misma pregunta.
- **En las mixtas acertó solo la interpretación.** Respondió bien el sí o no, porque no necesita datos: dos cifras de un año no prueban una causa, y la serie se llama «Lima Metropolitana». Pero no dio ninguna de las cuatro cifras.

**Modo B (con MCP y Skills)**

- **BCRP: siempre la misma ruta.** Primero buscó el código con `buscar_series` y luego pidió el dato con `serie`. Las cuatro cifras coinciden con la API, y cada respuesta cita el código, el periodo y el enlace de la tabla web.
- **ENAHO: casi siempre leyó las salidas de las Skills, sin invocarlas.** Solo en la pregunta 8 activó `limpiando-enaho`, que volvió a correr `limpiar.py`. Por eso `salidas/validacion.txt` cambió solo en la fecha: otra vez 13 de 13 aprobadas y las mismas cifras. En las demás leyó directamente `salidas/indicadores.csv`, `validacion.txt` o `comparacion_referencia.csv`. Esto cuenta como usar las Skills, porque esos archivos son su resultado, pero muestra que Haiku prefiere leer un resultado ya calculado antes que seguir la Skill paso a paso.
- **En 4 preguntas dio la cifra oficial del INEI en vez de la calculada:** 27.6 en lugar de 27.53, 39.3 en lugar de 39.44, 45 en lugar de 44.99 y 24.8 en lugar de 24.74. Las tomó de la validación y de la referencia del proyecto, y en su explicación aclaró la diferencia entre los dos métodos. Están dentro de la tolerancia, que se definió para aceptar las dos cifras.
- **Herramienta equivocada al inicio.** En la pregunta 6 buscó «pobreza rural» en el MCP del BCRP, que no tiene datos de la ENAHO. Obtuvo 0 series y cambió a los archivos de la ENAHO.
- **Intentos bloqueados.** Intentó usar `Glob` y `Grep`, que no estaban habilitados. En las preguntas 5 y 7 armó comandos `grep` que incluían `informes/informe_final.md` y `evaluacion/preguntas.csv`, y Claude Code los rechazó por la regla de `--disallowedTools`. Ninguna respuesta salió de esos archivos: la protección del experimento funcionó.
- **Cálculos propios bien ponderados.** En las preguntas 8 y 9 calculó la pobreza de Ica y de Lima sobre `salidas/personas_2024.parquet`, ponderando con `facpob07`, y obtuvo lo mismo que `indicadores.csv` (5.91 y 26.89).
- **Más lento:** 24.5 s en promedio frente a 9.4 s, porque cada respuesta necesita entre 4 y 11 turnos para buscar, consultar y leer, frente a 2 del modo A.
- **Ningún error técnico:** el MCP se conectó en las 10 llamadas y no hubo tiempos agotados.

## 6. Conclusión

Con el MCP y las Skills, Claude Haiku pasó de 1 a 10 respuestas correctas de 10. Además, cada cifra del modo B se puede rastrear: tiene el código de la serie y el periodo del BCRP, o el archivo del procesamiento de la ENAHO. Sin herramientas, el modelo fue prudente (no inventó cifras), pero eso lo dejó casi sin respuestas, y su único acierto vino de una memoria que no cita la fuente correcta y que no repite el dato en todas las corridas. El costo de usar las herramientas fue el tiempo: unas 2.6 veces más.

Las herramientas no son infalibles. El modelo a veces probó primero la herramienta equivocada o una no habilitada, y en la ENAHO prefirió leer resultados ya calculados antes que seguir las Skills. Por eso importan dos cosas del diseño:

- que las Skills dejen salidas validadas (`indicadores.csv` y `validacion.txt`), porque de ahí sale la cifra aunque el modelo no siga todos los pasos;
- que el experimento impida leer las respuestas esperadas, como hizo `--disallowedTools` en las preguntas 5 y 7.

**Límites de esta evaluación:**

- Son 10 preguntas, con un solo modelo y una sola corrida por modo. Como las respuestas del modelo varían entre corridas (pregunta 1), un resultado más sólido exigiría repetir cada pregunta varias veces.
- Las preguntas de la ENAHO tienen respuesta en archivos que ya existían en el proyecto, así que miden sobre todo si el agente encuentra y cita bien el procesamiento. No miden si lo rehace desde los microdatos.

## 7. Cómo reproducirla

Desde `tarea_4/`, con Claude Code instalado y la sesión iniciada:

```bash
uv run evaluacion/evaluar.py                     # los 2 modos, 20 llamadas, unos 5 minutos
uv run evaluacion/evaluar.py --modelo sonnet     # el mismo experimento con otro modelo
uv run evaluacion/evaluar.py --ids enaho_ica --modos B   # una sola pregunta y un solo modo
```

Cada corrida reescribe `resultados.csv` y los registros de `evidencias_ia/evaluacion/registros/`.
