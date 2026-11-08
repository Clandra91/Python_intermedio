# Referencia de la ENAHO 2024

## Archivos

| Archivo | Una fila por | Filas | Llaves | Factor |
|---|---|---|---|---|
| `966-Modulo34.zip` → `966-Modulo34/sumaria-2024.dta` | hogar | 33,691 | `conglome`, `vivienda`, `hogar` | `factor07` |
| `966-Modulo02.zip` → `966-Modulo02/enaho01-2024-200.dta` | persona | 117,721 | las tres + `codperso` | `facpob07` |

El zip del módulo 34 trae también `sumaria-2024-12g.dta`, la versión con 12 grupos de gasto. La limpieza usa
`sumaria-2024.dta`.

## Variables de la base `salidas/personas_2024.parquet`

| Variable | Viene de | Qué es |
|---|---|---|
| `conglome`, `vivienda`, `hogar`, `codperso` | módulo 02 | Llaves, como texto: 6, 3, 2 y 2 caracteres |
| `ubigeo` | sumaria | Distrito, texto de 6 caracteres |
| `departamento` | `ubigeo[:2]` | Código del departamento, de `01` a `25`. Lima es `15` y Callao `07` |
| `nombre_departamento` | el script | Nombre con tildes, solo para etiquetas. Las uniones se hacen por código |
| `dominio` | sumaria | 1 a 3 costa, 4 a 6 sierra, 7 selva, 8 Lima Metropolitana |
| `estrato` | sumaria | Tamaño del centro poblado: 1 a 5 urbano, 6 a 8 rural |
| `area` | `estrato` | `Urbana` si `estrato <= 5`; si no, `Rural` |
| `sexo` | `p207` | 1 `Hombre`, 2 `Mujer` |
| `edad` | `p208a` | Años cumplidos |
| `grupo_edad` | `edad` | 0 a 11, 12 a 17, 18 a 29, 30 a 59 y 60 años a más |
| `pobreza` | sumaria | 1 pobre extremo, 2 pobre no extremo, 3 no pobre |
| `pobre` | `pobreza <= 2` | Verdadero si el hogar es pobre (extremo o no extremo) |
| `pobre_extremo` | `pobreza == 1` | Verdadero si el hogar es pobre extremo |
| `facpob07` | módulo 02 | Factor de expansión de cada persona: a cuántas personas del Perú representa |

## Reglas que el script ya aplica

- **Lectura:** `pd.read_stata(..., convert_categoricals=False)`, para recibir códigos y no etiquetas. Las llaves
  llegan como texto y se comprueba su ancho: leídas como número, `010101` pasaría a `10101`.
- **Nombres en minúscula:** la columna del año llega como `aÑo`.
- **Residentes habituales:** `((p204 == 1) & (p205 == 2)) | ((p204 == 2) & (p206 == 1))`. Son los miembros del
  hogar que no estuvieron ausentes 30 días o más, y los no miembros que viven ahí hace 30 días o más.
  - `p204`: ¿es miembro del hogar? (1 sí, 2 no)
  - `p205`: ¿estuvo ausente 30 días o más? (1 sí, 2 no)
  - `p206`: ¿está presente hace 30 días o más? (1 sí, 2 no)
- **Unión:** personas con hogares por `conglome`, `vivienda` y `hogar`, con `validate="m:1"`. Se comprueba que
  ninguna persona quede sin hogar y que no cambie el número de filas.
- **Ponderación:** toda tasa es `suma(facpob07 × pobre) / suma(facpob07)`. En 2024 el `facpob07` de cada persona
  es igual al `factor07` de su hogar.

## Cifras de referencia de 2024

| Cifra | INEI | Base de residentes |
|---|---|---|
| Pobreza monetaria nacional | 27.6 % | 27.53 % |
| Pobreza urbana / rural | 24.8 % / 39.3 % | 24.74 % / 39.44 % |
| Residentes habituales | 108,664 | 108,664 |

El INEI publica con la sumaria, ponderando cada hogar por `factor07 × mieperho`. `mieperho` cuenta a los
miembros del hogar, incluidos los ausentes, y deja fuera a los no miembros. La base usa el filtro de residentes
habituales, y por eso difiere en unas décimas. `validacion.txt` calcula las dos y explica la diferencia.

## Para agregar una variable

1. Búscala en el diccionario del INEI, `Diccionario2024.pdf`, dentro del mismo zip.
2. Si es de la persona (módulo 02), agrégala a la lista de columnas de `residentes` en `scripts/limpiar.py`. Si
   es del hogar (sumaria), agrégala a `columnas_hogar`.
3. Agrégala a la lista `columnas` que se guarda en el parquet, vuelve a correr el script y revisa que
   `validacion.txt` siga aprobada.
