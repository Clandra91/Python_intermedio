"""Gráficos y mapas para el reel, con los colores del video (fondo oscuro).

Se ejecuta con el entorno de tarea_3 (tiene plotly y kaleido), desde la carpeta tarea_3:
    uv run python reel/imagenes.py
Guarda los PNG en reel/imagenes/.
"""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px

AQUI = Path(__file__).resolve().parent
DATOS = AQUI.parent / "datos"
SALIDA = AQUI / "imagenes"
SALIDA.mkdir(exist_ok=True)

# Colores del reel (los mismos de reel.py)
FONDO, TEXTO, SUAVE, ACENTO, CAJA = "#1C1A17", "#F7F3EC", "#B8AE9F", "#F08A4B", "#2A2723"
ANCHO, ALTO = 900, 600   # el ancho útil del video es 1080 - 2 x 90 de margen

renamu = pd.read_csv(DATOS / "procesados" / "renamu_indicadores_2024_2026.csv", dtype={"Ubigeo": str})
renamu["cod_dep"] = renamu["Ubigeo"].str[:2]
with open(DATOS / "geo" / "peru_departamental_simple.geojson", encoding="utf-8") as archivo:
    mapa = json.load(archivo)


def estilo(fig):
    """Fondo oscuro, letras grandes y sin elementos que distraigan en un celular."""
    fig.update_layout(paper_bgcolor=FONDO, plot_bgcolor=FONDO, font=dict(family="Arial", size=24, color=TEXTO),
                      margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    fig.update_xaxes(showgrid=False, linecolor=SUAVE, tickfont=dict(color=SUAVE, size=30), title=None)
    fig.update_yaxes(visible=False)
    return fig


def guardar(fig, nombre, ancho=ANCHO, alto=ALTO):
    fig.write_image(SALIDA / nombre, width=ancho, height=alto, scale=2)   # scale=2: más nítida
    print("ok", nombre)


def mapa_departamentos(por_dep, columna, escala, nombre):
    fig = px.choropleth(por_dep, geojson=mapa, locations="cod_dep", featureidkey="properties.FIRST_IDDP",
                        color=columna, color_continuous_scale=escala)
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor=FONDO)
    fig.update_traces(marker_line_color=FONDO, marker_line_width=1.5)
    fig.update_layout(paper_bgcolor=FONDO, margin=dict(l=0, r=0, t=0, b=0), coloraxis_showscale=False)
    guardar(fig, nombre, ancho=640, alto=720)   # casi cuadrado: el Perú es más alto que ancho


# 1. Dónde están las municipalidades: cantidad por departamento
cantidad = renamu[renamu["anio"] == 2026].groupby("cod_dep").size().rename("municipalidades").reset_index()
mapa_departamentos(cantidad, "municipalidades", [CAJA, SUAVE], "1_mapa_municipalidades.png")

# 2. % que requiere apoyo por año (barras: "alguna de las dos")
por_anio = (renamu.groupby("anio")["requiere_alguna"].mean() * 100).round(1).reset_index()
por_anio["anio"] = por_anio["anio"].astype(str)
por_anio["texto"] = por_anio["requiere_alguna"].map(lambda x: f"{x:.1f} %".replace(".", ","))
fig = px.bar(por_anio, x="anio", y="requiere_alguna", text="texto", color_discrete_sequence=[ACENTO])
fig.update_traces(textposition="outside", textfont_size=34, width=0.6)
fig.update_yaxes(range=[0, 100])
guardar(estilo(fig), "2_por_anio.png")

# 3. En cuántas de las 3 ediciones pidió apoyo cada municipalidad
veces = (renamu.groupby("Ubigeo")["requiere_alguna"].sum().value_counts(normalize=True).sort_index() * 100).round(1)
veces = veces.reset_index()
veces.columns = ["ediciones", "pct"]
veces["etiqueta"] = veces["ediciones"].map({0: "Ninguna", 1: "1 edición", 2: "2 ediciones", 3: "Las 3"})
veces["texto"] = veces["pct"].map(lambda x: f"{x:.1f} %".replace(".", ","))
veces["color"] = (veces["ediciones"] == 3).map({True: "destacado", False: "resto"})
fig = px.bar(veces, x="etiqueta", y="pct", text="texto", color="color",
             color_discrete_map={"destacado": ACENTO, "resto": SUAVE})
fig.update_traces(textposition="outside", textfont_size=32, width=0.65)
fig.update_yaxes(range=[0, 70])
guardar(estilo(fig), "3_ediciones.png")

# 4. % que requiere apoyo según nivel de capacidad (2024-2026)
por_nivel = (renamu.groupby("nivel_capacidad")["requiere_alguna"].mean() * 100).round(1).reindex(["Baja", "Media", "Alta"])
por_nivel = por_nivel.reset_index()
por_nivel.columns = ["nivel", "pct"]
por_nivel["nivel"] = "Capacidad " + por_nivel["nivel"].str.lower()
por_nivel["texto"] = por_nivel["pct"].map(lambda x: f"{x:.1f} %".replace(".", ","))
fig = px.bar(por_nivel, x="nivel", y="pct", text="texto", color_discrete_sequence=[ACENTO])
fig.update_traces(textposition="outside", textfont_size=34, width=0.6)
fig.update_yaxes(range=[0, 100])
guardar(estilo(fig), "4_por_nivel.png")

# 5. Mapa: % que requiere apoyo por departamento (promedio 2024-2026)
por_dep = (renamu.groupby("cod_dep")["requiere_alguna"].mean() * 100).rename("requiere").reset_index()
mapa_departamentos(por_dep, "requiere", [CAJA, ACENTO], "5_mapa_requiere.png")
