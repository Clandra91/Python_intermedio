"""Dashboard: clasificador de titulares de La República (Tarea 1, Python Intermedio).

Correr en local, desde la carpeta tarea_1:
    uv run streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from transformers import pipeline

# ------------------------------------------------------------------ configuración
st.set_page_config(page_title="Clasificador de noticias peruanas", layout="wide")

# Carpeta donde está este archivo: los datos y el modelo se buscan desde aquí
CARPETA = Path(__file__).parent

# Resultados obtenidos en 02_clasificacion.ipynb
F1_MACRO_TEST = 0.898
ACUERDO_LLM_HUMANO = 20 / 20


# ------------------------------------------------------------------ carga de datos y modelo
@st.cache_data
def cargar_noticias():
    """Lee las noticias una sola vez (y no cada vez que se mueve un filtro)."""
    return pd.read_csv(CARPETA / "datos" / "noticias.csv")


@st.cache_resource
def cargar_clasificador():
    """Carga el modelo entrenado (DistilBERT fine-tuned) una sola vez."""
    return pipeline("text-classification", model=str(CARPETA / "modelo"), top_k=None)


noticias = cargar_noticias()

# ------------------------------------------------------------------ encabezado
st.title("¿Se pueden clasificar automáticamente los titulares de noticias peruanas?")
st.markdown(
    "Se recolectaron **399 titulares** de *La República* (octubre de 2026) mediante sus RSS y los "
    "enlaces entre notas. Se compararon tres métodos: un modelo **zero-shot**, **Gemini** como "
    "etiquetador (supervisión débil) y **DistilBERT** entrenado con las noticias (fine-tuning). "
    "Las 4 categorías son: política, economía, deportes y ciencia y tecnología."
)

# ------------------------------------------------------------------ filtros (barra lateral)
st.sidebar.header("Filtros")
medios = sorted(noticias["medio"].unique())
medios_elegidos = st.sidebar.multiselect("Medio", medios, default=medios)

categorias = sorted(noticias["etiqueta"].unique())
categorias_elegidas = st.sidebar.multiselect("Categoría", categorias, default=categorias)

filtrado = noticias[
    noticias["medio"].isin(medios_elegidos) & noticias["etiqueta"].isin(categorias_elegidas)
]

# ------------------------------------------------------------------ métricas
col1, col2, col3 = st.columns(3)
col1.metric("Noticias (con los filtros)", len(filtrado))
col2.metric("F1 macro del modelo en test", f"{F1_MACRO_TEST:.3f}")
col3.metric("Acuerdo Gemini - auditoría humana", f"{ACUERDO_LLM_HUMANO:.0%}")

if filtrado.empty:
    st.warning("No hay noticias con esos filtros. Elige al menos un medio y una categoría.")
else:
    # -------------------------------------------------------------- gráfico
    por_categoria = filtrado["etiqueta"].value_counts().reset_index()
    fig = px.bar(por_categoria, x="etiqueta", y="count", text="count",
                 title="Distribución de noticias por categoría (según los filtros)",
                 labels={"etiqueta": "Categoría", "count": "Noticias"})
    st.plotly_chart(fig, width="stretch")

    # -------------------------------------------------------------- tabla + descarga
    st.subheader("Noticias filtradas")
    st.dataframe(filtrado[["fecha", "etiqueta", "titular", "bajada", "url"]], width="stretch")
    st.download_button("Descargar CSV", filtrado.to_csv(index=False).encode("utf-8-sig"),
                       file_name="noticias_filtradas.csv", mime="text/csv")

# ------------------------------------------------------------------ probador en vivo
st.subheader("Probador en vivo")
titular = st.text_input("Escribe o pega un titular:")
if st.button("Clasificar"):
    if titular.strip():
        resultados = cargar_clasificador()(titular)[0]  # lista de {label, score}, de mayor a menor
        mejor = resultados[0]
        st.success(f"Categoría predicha: **{mejor['label']}** (probabilidad: {mejor['score']:.1%})")
        probabilidades = pd.DataFrame(resultados).rename(columns={"label": "categoria", "score": "probabilidad"})
        st.bar_chart(probabilidades, x="categoria", y="probabilidad")
    else:
        st.info("Primero escribe un titular.")