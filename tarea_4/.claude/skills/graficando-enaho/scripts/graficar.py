"""Gráficos de barras de la pobreza monetaria de la ENAHO 2024, ponderados con facpob07.

Uso, desde la carpeta tarea_4:
    uv run .claude/skills/graficando-enaho/scripts/graficar.py --por area
    uv run .claude/skills/graficando-enaho/scripts/graficar.py --por todos     # area, sexo, edad y departamento

Entra: salidas/personas_2024.parquet, la base que arma la skill limpiando-enaho.
Sale:  figuras/enaho_pobreza_por_<corte>_2024.png, a 200 dpi, y la tabla con las cifras en pantalla.
Reglas de la sesión 16: barras desde cero y ordenadas, un solo color, el valor en cada barra, un título que dice
qué muestra y la fuente al pie. Escrito con apoyo de Claude.
"""
import argparse
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # sin ventanas: solo se guarda el PNG
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]  # scripts -> graficando-enaho -> skills -> .claude -> tarea_4
BASE = RAIZ / "salidas" / "personas_2024.parquet"
FIGURAS = RAIZ / "figuras"

# columna de la base, cómo se nombra en el subtítulo y si las barras se ordenan por valor
CORTES = {
    "area": ("area", "área de residencia", True),
    "sexo": ("sexo", "sexo", True),
    "edad": ("grupo_edad", "grupo de edad", False),  # la edad conserva su orden natural
    "departamento": ("nombre_departamento", "departamento", True),
}
# cómo se nombra cada grupo dentro del título
FRASES = {
    "Urbana": "el área urbana", "Rural": "el área rural", "Hombre": "los hombres", "Mujer": "las mujeres",
    "0 a 11 años": "las niñas y niños de 0 a 11 años", "12 a 17 años": "los adolescentes de 12 a 17 años",
    "18 a 29 años": "los jóvenes de 18 a 29 años", "30 a 59 años": "los adultos de 30 a 59 años",
    "60 años a más": "las personas de 60 años a más",
}
COLOR = "#2a78d6"
TEXTO, TEXTO_SUAVE, GRILLA, FONDO = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
FUENTE = ("Fuente: INEI, Encuesta Nacional de Hogares (ENAHO) 2024, módulos 34 y 02. Residentes habituales; "
          "estimaciones ponderadas con el factor de expansión facpob07.")


def pobreza_por(base, columna):
    """Porcentaje de personas pobres en cada grupo, ponderado con facpob07."""
    base = base.assign(peso=base["facpob07"].astype(float))
    base["peso_pobre"] = base["peso"] * base["pobre"]
    tabla = base.groupby(columna, observed=True)[["peso_pobre", "peso"]].sum()
    return (100 * tabla["peso_pobre"] / tabla["peso"]).rename("pobreza_pct")


def titulo(tabla, corte):
    """Una frase que dice qué muestra el gráfico, con las cifras calculadas (nunca escritas a mano)."""
    alto, bajo = tabla.idxmax(), tabla.idxmin()
    if corte == "departamento":
        y = "e" if bajo.startswith(("I", "Hi")) else "y"  # "e Ica", no "y Ica"
        return (f"{alto} tiene la pobreza más alta ({tabla[alto]:.1f} %) {y} {bajo} "
                f"la más baja ({tabla[bajo]:.1f} %)")
    brecha = tabla[alto] - tabla[bajo]
    if brecha < 1:
        return f"La pobreza es casi igual en {FRASES[alto]} ({tabla[alto]:.1f} %) y en {FRASES[bajo]} ({tabla[bajo]:.1f} %)"
    return (f"La pobreza es mayor en {FRASES[alto]} ({tabla[alto]:.1f} %) que en {FRASES[bajo]} "
            f"({tabla[bajo]:.1f} %): {brecha:.1f} puntos más")


def graficar(base, corte):
    """Hace el gráfico de un corte, lo guarda en figuras/ y devuelve la ruta y la tabla."""
    columna, nombre, ordenar = CORTES[corte]
    tabla = pobreza_por(base, columna)
    if ordenar:
        tabla = tabla.sort_values(ascending=False)
    nacional = pobreza_por(base.assign(todo="Perú"), "todo")["Perú"]

    # medidas en pulgadas: el título puede ocupar una o dos líneas y el alto crece con el número de barras
    lineas_titulo = textwrap.wrap(titulo(tabla, corte), width=78)
    arriba = 0.2 + 0.24 * len(lineas_titulo) + 0.3 + 0.32  # título, subtítulo y la etiqueta del promedio
    abajo = 0.68
    n = len(tabla)
    alto = arriba + abajo + 0.36 * n + 0.3
    fig, ax = plt.subplots(figsize=(9, alto), facecolor=FONDO)
    ax.set_facecolor(FONDO)
    posiciones = range(n)[::-1]  # la primera barra arriba
    ax.barh(list(posiciones), tabla.values, height=0.62, color=COLOR, zorder=2)
    fondo_etiqueta = {"facecolor": FONDO, "edgecolor": "none", "pad": 1.5}  # la línea del promedio pasa por detrás
    for y, valor in zip(posiciones, tabla.values):
        ax.text(valor + 0.6, y, f"{valor:.1f} %", va="center", fontsize=9, color=TEXTO, zorder=4, bbox=fondo_etiqueta)
    ax.set_yticks(list(posiciones), [str(c) for c in tabla.index], fontsize=9.5, color=TEXTO)

    # el promedio nacional como referencia para leer cada barra
    ax.axvline(nacional, color=TEXTO_SUAVE, linestyle="--", linewidth=1, zorder=3)
    ax.text(nacional, n - 0.45, f"Perú: {nacional:.1f} %", fontsize=8.5, color=TEXTO_SUAVE, va="bottom",
            ha="center", zorder=4, bbox=fondo_etiqueta)

    ax.set_xlim(0, max(tabla.max(), nacional) * 1.15)  # el eje empieza en cero
    ax.set_ylim(-0.6, n - 0.1)
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0f} %")
    ax.tick_params(axis="x", colors=TEXTO_SUAVE, labelsize=8.5, length=0)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRILLA, linewidth=0.8, zorder=0)
    for lado in ["top", "right", "left"]:
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(GRILLA)

    fig.text(0.02, 1 - 0.2 / alto, "\n".join(lineas_titulo), fontsize=12.5, fontweight="bold", color=TEXTO,
             va="top", linespacing=1.3)
    fig.text(0.02, 1 - (0.25 + 0.24 * len(lineas_titulo)) / alto,
             f"Pobreza monetaria por {nombre}, Perú 2024 (% de personas)", fontsize=10, color=TEXTO_SUAVE, va="top")
    fig.text(0.02, 0.12 / alto, FUENTE, fontsize=7.5, color=TEXTO_SUAVE, va="bottom")
    fig.subplots_adjust(left=0.2 if corte == "departamento" else 0.17, right=0.97,
                        top=1 - arriba / alto, bottom=abajo / alto)

    FIGURAS.mkdir(exist_ok=True)
    ruta = FIGURAS / f"enaho_pobreza_por_{corte}_2024.png"
    fig.savefig(ruta, dpi=200, facecolor=FONDO)
    plt.close(fig)
    return ruta, tabla, nacional


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--por", choices=list(CORTES) + ["todos"], required=True, help="el corte del gráfico")
    cortes = list(CORTES) if (por := parser.parse_args().por) == "todos" else [por]

    if not BASE.exists():
        sys.exit("ERROR: no existe salidas/personas_2024.parquet. Usa primero la skill limpiando-enaho "
                 "(uv run .claude/skills/limpiando-enaho/scripts/limpiar.py) y vuelve a correr este script.")
    base = pd.read_parquet(BASE)

    for corte in cortes:
        ruta, tabla, nacional = graficar(base, corte)
        print(f"\nfiguras/{ruta.name}")
        print(f"  {titulo(tabla, corte)}")
        for grupo, valor in tabla.items():
            print(f"  {grupo:<16} {valor:5.1f} %")
        print(f"  {'Perú':<16} {nacional:5.1f} %  (promedio nacional)")


if __name__ == "__main__":
    main()
