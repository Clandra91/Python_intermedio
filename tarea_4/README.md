# Tarea 4 – Agente de investigación socioeconómica: MCP del BCRP y Skills de la ENAHO 2024

**Pregunta de investigación:** ¿Cómo evolucionó la inflación en el Perú entre 2020 y 2024, en especial la de alimentos y energía, y qué diferencias de pobreza monetaria presentaban las zonas urbanas y rurales y los departamentos al cierre de ese período?

**Informe final:** [informes/informe_final.md](informes/informe_final.md) · **Evaluación:** [evaluacion/comparacion.md](evaluacion/comparacion.md)

## 1. Objetivo

Construir un agente de investigación en Claude Code que responda preguntas sobre la realidad socioeconómica del Perú con datos oficiales y cifras verificables, en lugar de responder de memoria. El agente:

- consulta las series del **Banco Central de Reserva del Perú (BCRP)** con un servidor MCP propio;
- procesa los microdatos de la **ENAHO 2024 del INEI** con tres Skills (limpiar, graficar y mapear);
- combina las dos fuentes en un informe con gráficos, un mapa y cifras que se pueden rastrear hasta su origen.

También se evalúa si el MCP y las Skills mejoran las respuestas: las mismas 10 preguntas se hacen sin ellos (modo A) y con ellos (modo B).

## 2. Arquitectura general del agente

```text
Pregunta en lenguaje natural
        │
        ▼
Claude Code, abierto en tarea_4/ (el agente: planifica y elige las herramientas)
        │
        ├── Servidor MCP «bcrp» (mcp/server.py, conectado con .mcp.json)
        │     buscar_series · serie · resumen · graficar_serie  ──►  API del BCRP
        │     recursos bcrp://serie/{codigo} y bcrp://series/frecuentes · prompt informe
        │     └─► figuras/bcrp_*.png
        │
        └── Skills del proyecto (.claude/skills/)
              limpiando-enaho  ──►  salidas/personas_2024.parquet, indicadores.csv, validacion.txt
              graficando-enaho ──►  figuras/enaho_pobreza_por_*.png
              mapeando-enaho   ──►  mapas/pobreza_departamento_2024.png, salidas/comparacion_referencia.csv
              (graficando y mapeando usan primero limpiando-enaho si falta la base)
        │
        ▼
informes/informe_final.md (7 secciones, cada cifra con su fuente)
```

Las cuentas las hace Python, no el modelo: `resumen` calcula variaciones, promedios y extremos de las series, y los scripts de las Skills calculan la pobreza ponderada. Así, cada cifra sale de una llamada que se puede repetir.

```text
tarea_4/
├── README.md, pyproject.toml, uv.lock, .python-version, .gitignore
├── .mcp.json                     # conecta el servidor bcrp a Claude Code
├── mcp/
│   ├── server.py                 # servidor MCP del BCRP (FastMCP)
│   ├── test_server.py            # las 8 pruebas de la sesión 04, sin cambios
│   └── test_propias.py           # 2 pruebas propias de graficar_serie
├── .claude/skills/
│   ├── limpiando-enaho/          # SKILL.md, reference.md, scripts/limpiar.py
│   ├── graficando-enaho/         # SKILL.md, scripts/graficar.py
│   └── mapeando-enaho/           # SKILL.md, scripts/mapear.py, geo/ (GeoJSON) y referencias/
├── datos/                        # zip de la ENAHO 2024 (no se publican, ver sección 5)
├── salidas/                      # indicadores.csv, validacion.txt, comparacion_referencia.csv
├── figuras/                      # gráficos del BCRP y de la ENAHO
├── mapas/                        # mapa departamental de la pobreza
├── informes/informe_final.md     # informe que escribió el agente (Parte 3)
├── evaluacion/                   # preguntas.csv, evaluar.py, resultados.csv, comparacion.md
├── evidencias_ia/                # conversaciones con IA: mcp, skills, integracion, evaluacion
└── mover_capturas.py             # mueve y numera las capturas de pantalla
```

## 3. Herramientas MCP

El servidor `bcrp` (`mcp/server.py`) parte del proyecto de la sesión 04 del curso: `buscar_series` ya venía hecha, y el resto se completó con apoyo de Claude.

| Componente | Tipo | Qué hace |
|---|---|---|
| `buscar_series(texto, frecuencia, limite)` | herramienta | Busca códigos en el catálogo oficial del BCRP (unas 17 mil series), sin importar tildes ni mayúsculas. |
| `serie(codigo, desde, hasta)` | herramienta | Descarga los datos de una serie entre dos fechas, con la URL de la API y el enlace a la tabla de la web del BCRP (`tabla_web`) para verificarla a mano. |
| `resumen(codigo, desde, hasta)` | herramienta | Calcula con Python el primer y el último valor, el cambio, la variación %, el promedio, el máximo y el mínimo. |
| `graficar_serie(codigo, desde, hasta, titulo)` | herramienta propia | Grafica la serie con su promedio, el máximo y el mínimo, y guarda el PNG en `figuras/`. Las cifras del gráfico salen de `resumen`. |
| `bcrp://serie/{codigo}` | recurso | Ficha de una serie: nombre, categoría, frecuencia, inicio y última actualización. |
| `bcrp://series/frecuentes` | recurso | Fichas de las series más usadas: inflación, PBI, tasa de referencia, tipo de cambio y cobre. |
| `informe(tema, periodo)` | prompt | Plantilla de un informe breve con series del BCRP: buscar, resumir, graficar y citar cada cifra. |

Si un código no existe o el BCRP no responde con datos, las herramientas devuelven un error claro (`ToolError`) en lugar de inventar datos.

**Pruebas:** `uv run pytest -q` da **10 passed**: las 8 pruebas originales de la sesión 04 (`mcp/test_server.py`, sin cambios) y 2 propias (`mcp/test_propias.py`), que comprueban que `graficar_serie` guarda un PNG y que marca las mismas cifras que `resumen`.

## 4. Las tres Skills

| Skill | Cuándo se activa | Qué hace | Salidas |
|---|---|---|---|
| `limpiando-enaho` | Cuando piden limpiar o unir la ENAHO, o calcular la pobreza nacional, por área, sexo, edad o departamento | Lee los módulos 34 y 02 desde los zip, filtra a los residentes habituales, une personas y hogares y valida contra las cifras oficiales | `salidas/personas_2024.parquet`, `salidas/indicadores.csv`, `salidas/validacion.txt` |
| `graficando-enaho` | Cuando piden graficar o comparar la pobreza entre grupos o regiones | Gráficos de barras ponderados con `facpob07`, con título, unidad y fuente | `figuras/enaho_pobreza_por_{area,sexo,edad,departamento}_2024.png` |
| `mapeando-enaho` | Cuando piden un mapa o la distribución territorial de la pobreza | Une `ubigeo[:2]` con `FIRST_IDDP` (por código, no por nombre), exige 25 departamentos y compara con la referencia de la sesión 16 | `mapas/pobreza_departamento_2024.png`, `salidas/comparacion_referencia.csv` |

**Validación de la limpieza (13 de 13 aprobadas, `salidas/validacion.txt`):**

| Indicador | Resultado | Referencia |
|---|---:|---:|
| Pobreza monetaria nacional (residentes, `facpob07`) | 27.53 % | 27.6 % (±0.1) |
| Residentes habituales | 108,664 | 108,664 |
| Departamentos en el mapa | 25 | 25 |
| Pobreza urbana / rural (residentes) | 24.74 % / 39.44 % | 24.8 % / 39.3 % |
| Pobreza urbana / rural (método del INEI: sumaria, `factor07 × mieperho`) | 24.81 % / 39.30 % | 24.8 % / 39.3 % |

La diferencia de unas décimas entre los residentes y la sumaria se explica en `validacion.txt`: la sumaria cuenta a los 109,842 miembros del hogar y la base, a los 108,664 residentes habituales. No se forzó ninguna cifra.

**Coordinación:** si falta `salidas/personas_2024.parquet`, `graficando-enaho` y `mapeando-enaho` usan primero `limpiando-enaho` y siguen solo si su validación sale aprobada. Se probó borrando el parquet y pidiendo el mapa (capturas en `evidencias_ia/skills/`).

## 5. Fuentes y enlaces para descargar los datos

| Fuente | Datos | Enlace | Dónde va |
|---|---|---|---|
| INEI | ENAHO 2024, módulo 34 (sumaria) | [966-Modulo34.zip](https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip) | `datos/`, sin descomprimir |
| INEI | ENAHO 2024, módulo 02 (miembros del hogar) | [966-Modulo02.zip](https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip) | `datos/`, sin descomprimir |
| Repositorio del curso | Límites departamentales del Perú | [peru_departamental_simple.geojson](https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson) | ya incluido en `.claude/skills/mapeando-enaho/geo/` |
| Repositorio del curso | Pobreza por departamento 2024 (referencia) | [sesión 16](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/16-skills-enaho) | ya incluido en `.claude/skills/mapeando-enaho/referencias/` |
| BCRP | Series estadísticas (API) | [estadisticas.bcrp.gob.pe](https://estadisticas.bcrp.gob.pe/estadisticas/series/) | el servidor MCP las consulta en línea; el catálogo se descarga solo en `mcp/datos/` |

Los zip de la ENAHO y el catálogo del BCRP no se publican por su peso (están en `.gitignore`), igual que `salidas/personas_2024.parquet`, que se vuelve a generar con la limpieza.

## 6. Instalación con uv

Se necesita [uv](https://docs.astral.sh/uv/), [Claude Code](https://docs.claude.com/en/docs/claude-code) y git.

```bash
git clone https://github.com/Clandra91/Python_intermedio.git
cd Python_intermedio/tarea_4
uv sync              # crea .venv con Python 3.12 y las dependencias de uv.lock
```

Dependencias: fastmcp, httpx, pandas, pyarrow, geopandas y matplotlib; pytest en el grupo `dev`. Luego se descargan los dos zip de la ENAHO en `datos/` (sección 5).

## 7. Conectar el MCP a Claude Code

El archivo `.mcp.json` ya declara el servidor, así que basta con abrir Claude Code desde `tarea_4/`:

```bash
claude
```

La primera vez, Claude Code pregunta si se aprueba el servidor `bcrp` del proyecto: se acepta. Con `/mcp` se comprueba que aparece como conectado, con sus 4 herramientas. Si se quisiera crear la conexión desde cero, el comando es:

```bash
claude mcp add --scope project bcrp -- uv run mcp/server.py
```

Las Skills no necesitan configuración: Claude Code las lee de `.claude/skills/`. Se pueden llamar con `/limpiando-enaho`, `/graficando-enaho` o `/mapeando-enaho`, o pedirlas en lenguaje natural (por ejemplo, «haz un mapa de la pobreza por departamento»).

## 8. Comandos para reproducir el procesamiento y las pruebas

Todos se corren desde `tarea_4/`:

```bash
uv run pytest -q                                                      # 10 passed
uv run .claude/skills/limpiando-enaho/scripts/limpiar.py              # base, indicadores y validación
uv run .claude/skills/graficando-enaho/scripts/graficar.py --por todos   # 4 gráficos de la ENAHO
uv run .claude/skills/mapeando-enaho/scripts/mapear.py                # mapa y comparación con la referencia
uv run evaluacion/evaluar.py                                          # evaluación: 10 preguntas en los modos A y B
```

Para repetir la ejecución del agente de la Parte 3, se abre `claude` en `tarea_4/` y se pega el pedido de `evidencias_ia/integracion/pedido_agente.md`.

## 9. Resultados de la evaluación

Se hicieron las mismas 10 preguntas (4 del BCRP, 4 de la ENAHO y 2 que combinan ambas fuentes) en dos modos, con el mismo modelo (Claude Haiku), la misma instrucción y una sesión nueva de `claude -p` por pregunta. Las respuestas esperadas se verificaron antes, en la API del BCRP y en el procesamiento de la ENAHO contrastado con el INEI (`evaluacion/preguntas.csv`).

- **Modo A:** sin ninguna herramienta (ni MCP, ni Skills, ni archivos, ni terminal, ni web), desde una carpeta temporal fuera del proyecto.
- **Modo B:** con el MCP `bcrp`, las Skills, `Read` y la terminal solo para `uv run`; sin web y sin permiso para leer `evaluacion/`, `informes/` ni `evidencias_ia/`, donde ya están las respuestas.

| Modo | Correctas | Parciales | Incorrectas | No responde | Errores | Tiempo promedio |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| A: sin MCP ni Skills | **1/10** | 2 | 0 | 7 | 0 | 9.4 s |
| B: con MCP y Skills | **10/10** | 0 | 0 | 0 | 0 | 24.5 s |

- **Modo A:**
  - No inventó cifras: en 7 preguntas respondió `null`.
  - En las 2 mixtas solo acertó el sí o no, que no requiere datos.
  - Su único acierto (la inflación de diciembre de 2022) vino de su memoria, sin el código de la serie.
- **Modo B:**
  - Respondió bien las 10.
  - En las preguntas del BCRP siempre usó `buscar_series` y luego `serie`.
  - En las de la ENAHO casi siempre leyó las salidas validadas de las Skills, y solo una vez activó `limpiando-enaho`.
  - Tardó unas 2.6 veces más.

El detalle por pregunta, los errores y la conclusión están en [evaluacion/comparacion.md](evaluacion/comparacion.md). Las respuestas completas, con la fuente y las herramientas de cada una, están en [evaluacion/resultados.csv](evaluacion/resultados.csv).

## 10. Limitaciones y problemas encontrados

**De los datos**

- El BCRP no tiene inflación por departamento ni rural para 2020–2024: solo la de Lima Metropolitana. Por eso el informe no compara la inflación y la pobreza departamento por departamento, y no afirma ninguna relación causal entre ellas.
- La pobreza de 2024 es un solo dato anual: no muestra cómo cambió entre 2020 y 2024.
- Las cifras de los residentes habituales difieren en unas décimas de las del INEI, que usa la sumaria (sección 4).
- La ENAHO es una muestra: las cifras departamentales tienen más error que la nacional, y no se calcularon intervalos de confianza.

**Del desarrollo**

- `uv init` escribía el correo institucional en `pyproject.toml`; por eso el proyecto se creó con `uv init --bare`.
- En la computadora no está Node, así que no se usó el MCP Inspector: el servidor se probó con pytest y desde Claude Code.
- En la evaluación, al lanzar varias preguntas del modo B a la vez, uno de los servidores MCP no llegaba a conectarse. Por eso el modo B corre de a una pregunta.
- En la evaluación, Haiku a veces probó primero una herramienta equivocada (buscó «pobreza rural» en el MCP del BCRP) o una que no estaba habilitada (`Glob`, `Grep`). En la ENAHO prefirió leer las salidas de las Skills antes que invocarlas.
- En dos preguntas del modo B, el modelo intentó leer `informes/` y `evaluacion/preguntas.csv`, y la regla de `--disallowedTools` lo bloqueó. Sin esa regla, el modo B habría podido copiar las respuestas esperadas.
- La evaluación es pequeña: 10 preguntas, un modelo y una corrida por modo. Las respuestas de memoria cambian entre corridas.
- Algunas capturas mostraban una pestaña con el correo personal; se taparon antes de publicarlas.

## 11. Ejemplo de una ejecución completa

En la Parte 3 se abrió `claude` en `tarea_4/` y se pegó el pedido de [`evidencias_ia/integracion/pedido_agente.md`](evidencias_ia/integracion/pedido_agente.md). En una sola ejecución, el agente:

1. **Buscó las series** con `buscar_series` (7 búsquedas). Las búsquedas «ipc departamento», «ipc rural» e «inflación ciudades» no devolvieron ninguna serie, y el agente lo informó como limitación en lugar de inventar datos.
2. **Calculó** primeros y últimos valores, promedios y extremos con `resumen` (5 llamadas) y los valores de cada diciembre con `serie` (2 llamadas).
3. **Graficó** la inflación de alimentos y energía con `graficar_serie` → `figuras/bcrp_PN09819PM_2020-01_2024-12.png`.
4. **Usó las Skills** `graficando-enaho` (por área y por departamento) y `mapeando-enaho`. `limpiando-enaho` no hizo falta porque la base ya existía.
5. **Escribió** `informes/informe_final.md` con 7 secciones, 3 hallazgos, un gráfico del BCRP, uno de la ENAHO y el mapa.

Después se verificaron a mano 5 cifras del informe: 3 en la web del BCRP y 2 en las salidas de la ENAHO y la referencia del INEI. Las 5 coinciden (sección «Verificación manual» del informe). Las capturas de toda la ejecución están en `evidencias_ia/integracion/`.

## 12. Evidencias del uso de inteligencia artificial

Se usó Claude Code (en VS Code y en la terminal) en todas las partes. Las conversaciones están en [`evidencias_ia/`](evidencias_ia/) como capturas de pantalla numeradas en orden cronológico (opción A del enunciado), con los datos personales tapados:

| Carpeta | Contenido |
|---|---|
| [`evidencias_ia/mcp/`](evidencias_ia/mcp/) | Parte 1: desarrollo del servidor MCP, pruebas y demostración en Claude Code |
| [`evidencias_ia/skills/`](evidencias_ia/skills/) | Parte 2: las tres Skills, invocación directa, lenguaje natural y coordinación |
| [`evidencias_ia/integracion/`](evidencias_ia/integracion/) | Parte 3: pedido al agente, ejecución completa, informe y verificación manual |
| [`evidencias_ia/evaluacion/`](evidencias_ia/evaluacion/) | Parte 4: diseño de las preguntas, ejecución de la evaluación y documentación. En `registros/` está la conversación completa de cada una de las 20 llamadas a `claude -p` (un JSONL por pregunta y modo) |

Claude Code propuso, probó y explicó el código, las Skills y los textos. La autora:

- tomó las decisiones: la pregunta de investigación, la herramienta propia y el diseño de la evaluación;
- copió y ejecutó cada archivo en su computadora;
- hizo las capturas y tapó los datos personales;
- verificó a mano las cifras.
