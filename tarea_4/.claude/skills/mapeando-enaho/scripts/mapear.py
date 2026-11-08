"""Mapa coroplético de la pobreza monetaria por departamento con la ENAHO 2024, ponderada con facpob07.

Uso, desde la carpeta tarea_4:
    uv run .claude/skills/mapeando-enaho/scripts/mapear.py

Entra: salidas/personas_2024.parquet (la base de la skill limpiando-enaho) y, dentro de esta skill,
       geo/peru_departamental_simple.geojson y referencias/pobreza_departamento_2024.csv (de la sesión 16).
Sale:  mapas/pobreza_departamento_2024.png, a 200 dpi, y salidas/comparacion_referencia.csv.
La unión es por código, ubigeo[:2] con FIRST_IDDP, nunca por nombre: "APURIMAC" no es "Apurímac".
Escrito con apoyo de Claude.
"""
import math
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")  # sin ventanas: solo se guarda el PNG
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

SKILL = Path(__file__).resolve().parents[1]
RAIZ = Path(__file__).resolve().parents[4]  # scripts -> mapeando-enaho -> skills -> .claude -> tarea_4
BASE = RAIZ / "salidas" / "personas_2024.parquet"
GEOJSON = SKILL / "geo" / "peru_departamental_simple.geojson"
REFERENCIA = SKILL / "referencias" / "pobreza_departamento_2024.csv"
MAPA = RAIZ / "mapas" / "pobreza_departamento_2024.png"
COMPARACION = RAIZ / "salidas" / "comparacion_referencia.csv"

# Una diferencia mayor con la referencia indica una unión o una ponderación equivocada, no un redondeo
LIMITE_DIFERENCIA = 1.0
LIMA, CALLAO = "15", "07"

# Un solo color, de claro (poca pobreza) a oscuro (mucha), desde 0; nunca arcoíris
AZULES = LinearSegmentedColormap.from_list(
    "azules", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
TEXTO, TEXTO_SUAVE, FONDO = "#0b0b0b", "#52514e", "#fcfcfb"
FUENTE = ("Fuente: INEI, ENAHO 2024, módulos 34 y 02. Residentes habituales; estimaciones ponderadas con facpob07.\n"
          "Unión con los límites departamentales por código: ubigeo[:2] = FIRST_IDDP.")


def pobreza_por_departamento(base):
    """Porcentaje de personas pobres en cada departamento, ponderado con facpob07."""
    base = base.assign(peso=base["facpob07"].astype(float))
    base["peso_pobre"] = base["peso"] * base["pobre"]
    tabla = base.groupby(["departamento", "nombre_departamento"])[["peso_pobre", "peso"]].sum().reset_index()
    tabla["pobreza_pct"] = 100 * tabla["peso_pobre"] / tabla["peso"]
    return tabla[["departamento", "nombre_departamento", "pobreza_pct"]]


def unir(tabla):
    """Une las cifras con las geometrías por código y exige 25 departamentos, todos con dato."""
    geo = gpd.read_file(GEOJSON)
    geo["FIRST_IDDP"] = geo["FIRST_IDDP"].astype(str).str.zfill(2)  # el código como texto de dos dígitos
    mapa = geo.merge(tabla, left_on="FIRST_IDDP", right_on="departamento", how="left", validate="1:1")
    sin_dato = mapa.loc[mapa["pobreza_pct"].isna(), "NOMBDEP"].tolist()
    if len(mapa) != 25 or sin_dato:
        sys.exit(f"ERROR: el mapa debe tener 25 departamentos con dato; tiene {len(mapa)} y sin dato: {sin_dato}")
    return mapa


def comparar(tabla):
    """Compara cada departamento con la referencia de la sesión 16 y guarda la tabla en salidas/."""
    ref = pd.read_csv(REFERENCIA, dtype={"ccdd": str})  # dtype=str conserva el cero de "01"
    ref = ref.rename(columns={"ccdd": "codigo", "pobreza_pct": "pobreza_referencia"})[["codigo", "pobreza_referencia"]]
    comp = tabla.rename(columns={"departamento": "codigo", "pobreza_pct": "pobreza_calculada"})
    comp = comp.merge(ref, on="codigo", how="outer", validate="1:1", indicator=True)
    if (comp["_merge"] != "both").any():
        sys.exit(f"ERROR: estos códigos no están en los dos archivos: {comp.loc[comp['_merge'] != 'both', 'codigo'].tolist()}")
    comp["diferencia"] = comp["pobreza_calculada"] - comp["pobreza_referencia"]
    comp = comp.drop(columns="_merge")
    comp.round(2).to_csv(COMPARACION, index=False)
    return comp


def dibujar(mapa):
    """Dibuja el mapa, con el valor del departamento más pobre, del menos pobre, de Lima y del Callao."""
    alto, bajo = mapa.loc[mapa["pobreza_pct"].idxmax()], mapa.loc[mapa["pobreza_pct"].idxmin()]
    fig, ax = plt.subplots(figsize=(8, 8.6), facecolor=FONDO)
    tope = math.ceil(mapa["pobreza_pct"].max() / 10) * 10  # la escala va de 0 a la decena siguiente
    mapa.plot(column="pobreza_pct", cmap=AZULES, vmin=0, vmax=tope, edgecolor="white", linewidth=0.6, ax=ax,
              legend=True, legend_kwds={"label": "Pobreza monetaria (% de personas)", "shrink": 0.5, "pad": 0.01})
    ax.set_axis_off()

    # etiquetas sobre el mar, a la izquierda, con una línea hasta cada departamento
    x_texto = mapa.total_bounds[0] - 0.4
    for codigo in dict.fromkeys([alto["FIRST_IDDP"], LIMA, CALLAO, bajo["FIRST_IDDP"]]):
        fila = mapa.set_index("FIRST_IDDP").loc[codigo]
        punto = fila.geometry.representative_point()
        y_texto = punto.y + {LIMA: 0.35, CALLAO: -0.35}.get(codigo, 0)  # Lima y Callao están muy cerca
        ax.annotate(f"{fila['nombre_departamento']}  {fila['pobreza_pct']:.1f} %", xy=(punto.x, punto.y),
                    xytext=(x_texto, y_texto), ha="right", va="center", fontsize=8.5, color=TEXTO,
                    arrowprops={"arrowstyle": "-", "color": TEXTO_SUAVE, "linewidth": 0.6})
    minx, miny, maxx, maxy = mapa.total_bounds
    ax.set_xlim(minx - 5, maxx + 0.3)
    ax.set_ylim(miny - 0.3, maxy + 0.3)

    fig.text(0.04, 0.972, f"La pobreza monetaria va de {bajo['pobreza_pct']:.1f} % en {bajo['nombre_departamento']} "
             f"a {alto['pobreza_pct']:.1f} % en {alto['nombre_departamento']}",
             fontsize=13, fontweight="bold", color=TEXTO, va="top")
    fig.text(0.04, 0.938, "Pobreza monetaria por departamento, Perú 2024 (% de personas). Lima y Callao por separado.",
             fontsize=9.5, color=TEXTO_SUAVE, va="top")
    fig.text(0.04, 0.015, FUENTE, fontsize=7.5, color=TEXTO_SUAVE, va="bottom", linespacing=1.4)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.07)
    MAPA.parent.mkdir(exist_ok=True)
    fig.savefig(MAPA, dpi=200, facecolor=FONDO)
    plt.close(fig)


def main():
    if not BASE.exists():
        sys.exit("ERROR: no existe salidas/personas_2024.parquet. Usa primero la skill limpiando-enaho "
                 "(uv run .claude/skills/limpiando-enaho/scripts/limpiar.py) y vuelve a correr este script.")
    tabla = pobreza_por_departamento(pd.read_parquet(BASE))
    mapa = unir(tabla)
    comp = comparar(tabla)

    mayor = comp.loc[comp["diferencia"].abs().idxmax()]
    print(f"Unión por código: 25 de 25 departamentos con dato; Lima ({LIMA}) y Callao ({CALLAO}) por separado.")
    print(f"Comparación con la referencia de la sesión 16 (salidas/{COMPARACION.name}):")
    iguales = (comp["pobreza_calculada"].round(1) - comp["pobreza_referencia"]).abs().lt(0.01).sum()
    print(f"  {iguales} de 25 iguales al redondear a un decimal; {comp['diferencia'].abs().le(0.5).sum()} de 25 a "
          f"0.5 puntos o menos; diferencia máxima {mayor['diferencia']:+.2f} puntos en {mayor['nombre_departamento']}.")
    if comp["diferencia"].abs().max() > LIMITE_DIFERENCIA:
        sys.exit(f"ERROR: un departamento difiere más de {LIMITE_DIFERENCIA} punto de la referencia. "
                 "Revisa la unión y la ponderación antes de hacer el mapa.")
    print("  La referencia se calculó con la sumaria (factor07 x mieperho); esta base, con los residentes "
          "habituales. Ver salidas/validacion.txt.")

    dibujar(mapa)
    print(f"\nmapas/{MAPA.name}")
    for _, fila in comp.sort_values("pobreza_calculada", ascending=False).iterrows():
        print(f"  {fila['codigo']} {fila['nombre_departamento']:<14} {fila['pobreza_calculada']:5.1f} %"
              f"   (referencia {fila['pobreza_referencia']:.1f} %)")


if __name__ == "__main__":
    main()
