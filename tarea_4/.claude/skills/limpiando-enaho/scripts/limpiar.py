"""Limpia los módulos 34 (sumaria) y 02 (miembros del hogar) de la ENAHO 2024 y arma una base de personas.

Uso, desde la carpeta tarea_4:
    uv run .claude/skills/limpiando-enaho/scripts/limpiar.py

Entra: datos/966-Modulo34.zip y datos/966-Modulo02.zip, tal como se bajan del INEI (no hace falta descomprimirlos).
Sale:
    salidas/personas_2024.parquet   una fila por residente habitual, con pobreza, departamento, área, sexo, edad y facpob07
    salidas/indicadores.csv         la pobreza ponderada nacional, por área, sexo, grupo de edad y departamento
    salidas/validacion.txt          cada verificación con APROBADA o FALLIDA
Si una verificación esencial falla, el script se detiene con un mensaje de error y no guarda la base ni los indicadores.
Pipeline de la sesión 16 (leer, normalizar, filtrar, unir, construir, validar y guardar), escrito con apoyo de Claude.
"""
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]  # scripts -> limpiando-enaho -> skills -> .claude -> tarea_4
DATOS = RAIZ / "datos"
SALIDAS = RAIZ / "salidas"
BASE = SALIDAS / "personas_2024.parquet"
INDICADORES = SALIDAS / "indicadores.csv"
VALIDACION = SALIDAS / "validacion.txt"

SUMARIA = ("966-Modulo34.zip", "966-Modulo34/sumaria-2024.dta")
MIEMBROS = ("966-Modulo02.zip", "966-Modulo02/enaho01-2024-200.dta")
URL_INEI = "https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/"

LLAVES_HOGAR = ["conglome", "vivienda", "hogar"]
LLAVES_PERSONA = LLAVES_HOGAR + ["codperso"]
# Ancho de cada llave: si se leyera como número, "010101" pasaría a 10101 y Amazonas se perdería
ANCHOS = {"conglome": 6, "vivienda": 3, "hogar": 2, "codperso": 2, "ubigeo": 6}

# Valores oficiales de la ENAHO 2024 que la limpieza debe reproducir
REF_POBREZA, REF_URBANA, REF_RURAL, TOLERANCIA = 27.6, 24.8, 39.3, 0.1
REF_RESIDENTES, REF_HOGARES = 108_664, 33_691

DEPARTAMENTOS = {
    "01": "Amazonas", "02": "Áncash", "03": "Apurímac", "04": "Arequipa", "05": "Ayacucho",
    "06": "Cajamarca", "07": "Callao", "08": "Cusco", "09": "Huancavelica", "10": "Huánuco",
    "11": "Ica", "12": "Junín", "13": "La Libertad", "14": "Lambayeque", "15": "Lima",
    "16": "Loreto", "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura",
    "21": "Puno", "22": "San Martín", "23": "Tacna", "24": "Tumbes", "25": "Ucayali",
}
GRUPOS_EDAD = [(0, 11, "0 a 11 años"), (12, 17, "12 a 17 años"), (18, 29, "18 a 29 años"),
               (30, 59, "30 a 59 años"), (60, 200, "60 años a más")]


def leer(zip_y_archivo):
    """Lee un .dta desde su zip, con los códigos como números y los nombres de columna en minúscula."""
    nombre_zip, archivo = zip_y_archivo
    ruta = DATOS / nombre_zip
    if not ruta.exists():
        sys.exit(f"ERROR: falta {ruta}. Bájalo del INEI ({URL_INEI}{nombre_zip}) y guárdalo en datos/ sin descomprimir.")
    with zipfile.ZipFile(ruta) as z, z.open(archivo) as f:
        df = pd.read_stata(f, convert_categoricals=False)
    df.columns = df.columns.str.lower()  # la columna del año llega como "aÑo"
    return df


def porcentaje(df, columna, factor="facpob07"):
    """Porcentaje de personas con columna == True, ponderado con el factor de expansión."""
    peso = df[factor].astype(float)  # el .dta lo trae en float32; en float64 la suma no pierde precisión
    return 100 * (df[columna] * peso).sum() / peso.sum()


def indicadores_por(base, columna, grupo):
    """Pobreza y pobreza extrema ponderadas para cada valor de una columna."""
    filas = []
    for valor, parte in base.groupby(columna, observed=True):
        filas.append({"grupo": grupo, "categoria": valor, "pobreza_pct": porcentaje(parte, "pobre"),
                      "pobreza_extrema_pct": porcentaje(parte, "pobre_extremo"),
                      "poblacion": round(parte["facpob07"].astype(float).sum()), "muestra": len(parte)})
    return filas


class Validacion:
    """Junta las verificaciones: nombre, resultado y detalle, separadas en esenciales y complementarias."""

    def __init__(self):
        self.filas = []

    def verificar(self, nombre, ok, detalle, esencial=True):
        self.filas.append((esencial, nombre, bool(ok), detalle))

    def fallidas_esenciales(self):
        return [nombre for esencial, nombre, ok, _ in self.filas if esencial and not ok]

    def escribir(self, notas):
        lineas = ["Validación de la limpieza de la ENAHO 2024 (módulos 34 y 02)",
                  f"Generado el {datetime.now():%Y-%m-%d %H:%M} con .claude/skills/limpiando-enaho/scripts/limpiar.py", ""]
        for esencial, titulo in [(True, "Verificaciones esenciales (si una falla, el proceso se detiene y no se guarda la base)"),
                                 (False, "Verificaciones complementarias (método oficial del INEI: sumaria con factor07 × mieperho)")]:
            lineas.append(titulo)
            for es, nombre, ok, detalle in self.filas:
                if es == esencial:
                    lineas.append(f"  [{'APROBADA' if ok else 'FALLIDA '}] {nombre}: {detalle}")
            lineas.append("")
        aprobadas = sum(ok for _, _, ok, _ in self.filas)
        lineas += notas + ["", f"Resultado: {aprobadas} de {len(self.filas)} verificaciones aprobadas."]
        SALIDAS.mkdir(exist_ok=True)
        VALIDACION.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main():
    v = Validacion()

    # 1. Leer y 2. normalizar los nombres de las columnas
    hogares = leer(SUMARIA)
    personas = leer(MIEMBROS)

    anchos = {llave: personas[llave].str.len().unique().tolist() for llave in ANCHOS}
    v.verificar("Llaves como texto, con sus ceros iniciales",
                all(anchos[llave] == [ancho] for llave, ancho in ANCHOS.items())
                and (hogares["ubigeo"].str.len() == 6).all(),
                ", ".join(f"{llave} {ancho} caracteres" for llave, ancho in ANCHOS.items()))
    v.verificar("Hogares únicos en la sumaria",
                len(hogares) == REF_HOGARES and not hogares.duplicated(LLAVES_HOGAR).any(),
                f"{len(hogares):,} hogares, {hogares.duplicated(LLAVES_HOGAR).sum()} repetidos")
    v.verificar("Personas únicas en el módulo 02", not personas.duplicated(LLAVES_PERSONA).any(),
                f"{len(personas):,} filas, {personas.duplicated(LLAVES_PERSONA).sum()} repetidas")

    # 3. Filtrar a los residentes habituales: miembros presentes o no miembros que viven ahí hace 30 días o más
    residente = (((personas["p204"] == 1) & (personas["p205"] == 2))
                 | ((personas["p204"] == 2) & (personas["p206"] == 1)))
    residentes = personas.loc[residente, LLAVES_PERSONA + ["p207", "p208a", "facpob07"]]
    v.verificar("Residentes habituales", len(residentes) == REF_RESIDENTES,
                f"{len(residentes):,} de {len(personas):,} filas (esperado {REF_RESIDENTES:,})")

    # 4. Unir personas (muchas) con su hogar (uno); validate="m:1" detiene la unión si un hogar se repite
    columnas_hogar = LLAVES_HOGAR + ["ubigeo", "dominio", "estrato", "pobreza", "factor07", "mieperho"]
    base = residentes.merge(hogares[columnas_hogar], on=LLAVES_HOGAR, how="left",
                            validate="m:1", indicator=True)
    sin_hogar = (base["_merge"] != "both").sum()
    v.verificar("Unión personas-hogares m:1 sin pérdidas ni duplicados",
                len(base) == len(residentes) and sin_hogar == 0,
                f"{len(residentes):,} filas antes y {len(base):,} después; {sin_hogar} personas sin hogar")

    # 5. Construir los indicadores
    base["departamento"] = base["ubigeo"].str[:2]
    base["nombre_departamento"] = base["departamento"].map(DEPARTAMENTOS)
    base["area"] = base["estrato"].le(5).map({True: "Urbana", False: "Rural"})  # estrato 1 a 5 es urbano
    base["sexo"] = base["p207"].map({1: "Hombre", 2: "Mujer"})
    base["edad"] = base["p208a"].astype(int)
    limites = [GRUPOS_EDAD[0][0] - 1] + [hasta for _, hasta, _ in GRUPOS_EDAD]
    base["grupo_edad"] = pd.cut(base["edad"], bins=limites, labels=[nombre for _, _, nombre in GRUPOS_EDAD])
    base["pobre"] = base["pobreza"] <= 2           # 1 pobre extremo, 2 pobre no extremo, 3 no pobre
    base["pobre_extremo"] = base["pobreza"] == 1

    codigos = sorted(base["departamento"].unique())
    v.verificar("25 departamentos (01 a 25)", codigos == sorted(DEPARTAMENTOS),
                f"{len(codigos)} códigos: {codigos[0]} a {codigos[-1]}")
    v.verificar("Sexo, edad y área sin vacíos", base[["sexo", "grupo_edad", "area"]].notna().all().all(),
                f"{base[['sexo', 'grupo_edad', 'area']].isna().sum().sum()} vacíos")

    # 6. Aplicar el factor de expansión (facpob07, el de cada persona)
    v.verificar("Factor de expansión facpob07 completo y positivo",
                base["facpob07"].notna().all() and (base["facpob07"] > 0).all(),
                f"{base['facpob07'].isna().sum()} vacíos; representa a {base['facpob07'].astype(float).sum():,.0f} personas")
    nacional = porcentaje(base, "pobre")
    v.verificar("Pobreza monetaria nacional, ponderada con facpob07",
                abs(nacional - REF_POBREZA) <= TOLERANCIA,
                f"{nacional:.2f} % (INEI {REF_POBREZA} %, diferencia {nacional - REF_POBREZA:+.2f}; máximo ±{TOLERANCIA})")

    # Control cruzado con el método oficial del INEI: hogares de la sumaria ponderados por factor07 × mieperho
    hogares["pobre"] = hogares["pobreza"] <= 2
    hogares["personas"] = hogares["factor07"] * hogares["mieperho"]
    urbano = hogares["estrato"] <= 5
    por_area = {fila["categoria"]: fila["pobreza_pct"] for fila in indicadores_por(base, "area", "Área")}
    diferencias = []
    for nombre, parte, ref, en_base in [("nacional", hogares, REF_POBREZA, nacional),
                                        ("urbana", hogares[urbano], REF_URBANA, por_area["Urbana"]),
                                        ("rural", hogares[~urbano], REF_RURAL, por_area["Rural"])]:
        oficial = porcentaje(parte, "pobre", factor="personas")
        v.verificar(f"Pobreza {nombre}", abs(oficial - ref) <= TOLERANCIA,
                    f"{oficial:.2f} % (INEI {ref} %, diferencia {oficial - ref:+.2f})", esencial=False)
        diferencias.append(f"{en_base - oficial:+.2f} en la {nombre}" if nombre != "nacional"
                           else f"{en_base - oficial:+.2f} puntos en la nacional")
    mismo_factor = (base["facpob07"] == base["factor07"]).all()
    v.verificar("El facpob07 de cada persona es el factor07 de su hogar", mismo_factor,
                f"sí, en las {len(base):,} filas" if mismo_factor else "no coinciden", esencial=False)

    sin_ponderar = 100 * base["pobre"].mean()
    notas = [
        "Cifras de la base de residentes (ponderadas con facpob07)",
        f"  Nacional {nacional:.2f} % · urbana {por_area['Urbana']:.2f} % · rural {por_area['Rural']:.2f} % · "
        f"pobreza extrema {porcentaje(base, 'pobre_extremo'):.2f} %",
        f"  Sin ponderar, el promedio simple da {sin_ponderar:.2f} %: {nacional - sin_ponderar:.1f} puntos menos. "
        "Por eso toda cifra se pondera.",
        "",
        "Por qué la base de residentes y la sumaria difieren en unas décimas",
        f"  La base cuenta a los {len(base):,} residentes habituales (el filtro que pide la tarea). La sumaria, con la que",
        f"  el INEI publica sus cifras, cuenta a los {hogares['mieperho'].sum():,} miembros del hogar (mieperho): incluye a los",
        "  miembros ausentes por más de 30 días y no incluye a los no miembros que viven en la vivienda. El factor es el",
        f"  mismo, así que la diferencia viene solo de a quiénes se cuenta: {', '.join(diferencias)}.",
        "  No se corrige nada para igualar la referencia.",
    ]
    v.escribir(notas)

    fallidas = v.fallidas_esenciales()
    if fallidas:
        sys.exit(f"ERROR: fallaron {len(fallidas)} verificaciones esenciales: {'; '.join(fallidas)}. "
                 f"No se guardó la base. Revisa salidas/validacion.txt.")

    # 7. Guardar la base y los indicadores
    columnas = LLAVES_PERSONA + ["ubigeo", "departamento", "nombre_departamento", "dominio", "estrato", "area",
                                 "sexo", "edad", "grupo_edad", "pobreza", "pobre", "pobre_extremo", "facpob07"]
    base[columnas].to_parquet(BASE, index=False)

    base["nacional"] = "Perú"
    filas = (indicadores_por(base, "nacional", "Nacional") + indicadores_por(base, "area", "Área")
             + indicadores_por(base, "sexo", "Sexo") + indicadores_por(base, "grupo_edad", "Grupo de edad"))
    for fila in indicadores_por(base, "departamento", "Departamento"):
        filas.append(fila | {"categoria": DEPARTAMENTOS[fila["categoria"]], "codigo": fila["categoria"]})
    tabla = pd.DataFrame(filas)[["grupo", "codigo", "categoria", "pobreza_pct", "pobreza_extrema_pct",
                                 "poblacion", "muestra"]]
    tabla.round({"pobreza_pct": 2, "pobreza_extrema_pct": 2}).to_csv(INDICADORES, index=False)

    print(VALIDACION.read_text(encoding="utf-8"))
    print(f"Base guardada en salidas/{BASE.name} ({len(base):,} personas) e indicadores en salidas/{INDICADORES.name}")


if __name__ == "__main__":
    main()
