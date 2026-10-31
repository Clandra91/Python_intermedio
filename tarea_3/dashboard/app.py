"""Dashboard: capacidades municipales y necesidad de apoyo sobre el SISFOH (RENAMU 2024-2026).

Ejecutar desde la carpeta tarea_3:
    uv run streamlit run dashboard/app.py
"""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Carpeta de datos: tarea_3/datos (un nivel arriba de dashboard/)
DATOS = Path(__file__).resolve().parent.parent / "datos"

# Tipos de apoyo que puede elegir quien usa el dashboard
APOYO = {
    "Capacitación o asistencia técnica": "requiere_alguna",
    "Capacitación": "requiere_capacitacion",
    "Asistencia técnica": "requiere_asistencia",
}
COMPONENTES = {"cap_conexion": "Conexión fija", "cap_equipos": "Equipos", "cap_personal": "Personal estable"}
NIVELES = ["Baja", "Media", "Alta"]
COLORES = {"Baja": "#E4572E", "Media": "#F3A712", "Alta": "#29335C"}


def pct(valor):
    """Porcentaje con coma decimal, por ejemplo 79,2 %."""
    return "—" if pd.isna(valor) else f"{valor:.1f} %".replace(".", ",")


@st.cache_data
def cargar_datos():
    renamu = pd.read_csv(DATOS / "procesados" / "renamu_indicadores_2024_2026.csv", dtype={"Ubigeo": str})
    renamu["cod_dep"] = renamu["Ubigeo"].str[:2]   # los 2 primeros dígitos del ubigeo = departamento
    return renamu


@st.cache_data
def cargar_mapa():
    with open(DATOS / "geo" / "peru_departamental_simple.geojson", encoding="utf-8") as archivo:
        return json.load(archivo)


st.set_page_config(page_title="Municipalidades y SISFOH", page_icon=":material/map:", layout="wide")
renamu = cargar_datos()
mapa_departamentos = cargar_mapa()




# ---------------------------------------------------------------- Controles
with st.sidebar:
    st.header("Filtros")
    anios = st.pills("Edición del RENAMU", [2024, 2025, 2026], selection_mode="multi", default=[2024, 2025, 2026])
    tipo = st.segmented_control("Tipo de municipalidad", ["Todas", "Provincial", "Distrital"],
                                default="Todas", required=True)
    apoyo = st.selectbox("Apoyo que requiere sobre el SISFOH", list(APOYO))

    # Ubicación
    st.subheader("Ubicación")

    # Búsqueda por ubigeo: 2 dígitos = departamento, 4 = provincia, 6 = distrito
    ubigeo = st.text_input("Buscar por ubigeo", max_chars=6, placeholder="Ej.: 160101",
                           help="Escribe 2, 4 o 6 dígitos: departamento, provincia o distrito.").strip()
    if ubigeo and not ubigeo.isdigit():
        st.error("El ubigeo solo debe tener números.", icon=":material/error:")
        ubigeo = ""
    elif ubigeo:
        encontrados = renamu[renamu["Ubigeo"].str.startswith(ubigeo)].drop_duplicates("Ubigeo")
        if encontrados.empty:
            st.warning("No se encontró ese ubigeo.", icon=":material/search_off:")
        elif len(encontrados) == 1:
            fila = encontrados.iloc[0]
            st.caption(f"{fila['Distrito']} · {fila['Provincia']} · {fila['Departamento']}")
        else:
            st.caption(f"{len(encontrados)} municipalidades empiezan con {ubigeo}.")

    # Listas en cascada: cada una muestra solo las opciones dentro de lo elegido en la anterior.
    # Se puede escribir en cada lista para buscar (filter_mode="contains": encuentra el texto en cualquier parte).
    departamentos = st.multiselect("Departamento", sorted(renamu["Departamento"].unique()),
                                   placeholder="Escribe o elige un departamento",
                                   filter_mode="contains", select_all=False)
    en_departamentos = renamu[renamu["Departamento"].isin(departamentos)] if departamentos else renamu

    provincias = st.multiselect("Provincia", sorted(en_departamentos["Provincia"].unique()),
                                placeholder="Escribe o elige una provincia",
                                filter_mode="contains", select_all=False)
    en_provincias = en_departamentos[en_departamentos["Provincia"].isin(provincias)] if provincias else en_departamentos

    # Distritos: se usa el ubigeo, que es único. Se muestra solo el nombre del distrito; si hay dos
    # distritos con el mismo nombre en la lista (p. ej., SANTA ROSA), se agrega la provincia para distinguirlos.
    opciones = en_provincias.drop_duplicates("Ubigeo")
    repetido = opciones["Distrito"].duplicated(keep=False)
    nombres = opciones["Distrito"].where(~repetido, opciones["Distrito"] + " (" + opciones["Provincia"] + ")")
    nombre_distrito = dict(zip(opciones["Ubigeo"], nombres))
    distritos = st.multiselect("Distrito", sorted(nombre_distrito, key=nombre_distrito.get),
                               format_func=nombre_distrito.get, placeholder="Escribe o elige un distrito",
                               filter_mode="contains", select_all=False)
    st.caption("Todos los gráficos y cifras se actualizan con estos filtros.")

# Se aplican los filtros
filtro = renamu["anio"].isin(anios)
if tipo != "Todas":
    filtro = filtro & (renamu["tipo_municipalidad"] == tipo)
if departamentos:
    filtro = filtro & renamu["Departamento"].isin(departamentos)
if provincias:
    filtro = filtro & renamu["Provincia"].isin(provincias)
if distritos:
    filtro = filtro & renamu["Ubigeo"].isin(distritos)    
if ubigeo:
    filtro = filtro & renamu["Ubigeo"].str.startswith(ubigeo)
datos = renamu[filtro]
columna = APOYO[apoyo]

# ---------------------------------------------------------------- Encabezado
st.title("¿Las municipalidades con menos capacidades piden más capacitaciones y soporte técnico sobre el SISFOH?")
st.caption("Municipalidades del Perú, RENAMU 2024–2026 (INEI). Análisis personal con datos públicos; "
           "no representa la posición del MIDIS.")

if datos.empty:
    st.warning("No hay datos para esta combinación de filtros. Revisa la edición, el ubigeo o la ubicación elegida.",
               icon=":material/info:")
    st.stop()

panel, hallazgos, tabla = st.tabs(["Panel", "Hallazgos y metodología", "Datos"])

with panel:
    # ------------------------------------------------------------ KPIs
    tasa_nivel = datos.groupby("nivel_capacidad")[columna].mean() * 100
    diferencia = tasa_nivel.get("Baja") - tasa_nivel.get("Alta") if {"Baja", "Alta"} <= set(tasa_nivel.index) else None

    with st.container(horizontal=True):
        st.metric("Municipalidades", f"{datos['Ubigeo'].nunique():,}".replace(",", " "), border=True,
                  help=f"{len(datos):,} registros (municipalidad × año)".replace(",", " "))
        st.metric(f"Requieren {apoyo.lower()}", pct(datos[columna].mean() * 100), border=True,
                  help="% de registros que declaran requerir ese apoyo sobre el SISFOH (pregunta 22 del RENAMU).")
        st.metric("Diferencia capacidad baja − alta", "—" if diferencia is None else f"{diferencia:+.1f} pp".replace(".", ","),
                  border=True, help="Puntos porcentuales: % que requiere apoyo con capacidad baja menos % con capacidad alta. "
                                    "Un valor positivo significa que las de baja capacidad piden más apoyo.")
        st.metric("Con conexión fija a internet", pct(datos["conexion_fija"].mean() * 100), border=True,
                  help="Wi-Fi, ADSL/DSL o fibra óptica como conexión principal.")
        st.metric("Con mayoría de personal estable", pct(datos["cap_personal"].mean() * 100), border=True,
                  help="Al menos 50 % de nombrados (D. Leg. 276) o del D. Leg. 728. Sin información en 307 registros.")

    # ------------------------------------------------------------ Mapa y ranking por departamento
    por_departamento = (
        datos.groupby(["cod_dep", "Departamento"])
        .agg(requiere=(columna, "mean"), municipalidades=("Ubigeo", "nunique"))
        .reset_index()
    )
    por_departamento["requiere"] = (por_departamento["requiere"] * 100).round(1)

    col_mapa, col_ranking = st.columns([3, 2])
    with col_mapa, st.container(border=True):
        st.subheader("Mapa: % que requiere apoyo por departamento")
        fig = px.choropleth(
            por_departamento, geojson=mapa_departamentos, locations="cod_dep",
            featureidkey="properties.FIRST_IDDP", color="requiere", hover_name="Departamento",
            hover_data={"cod_dep": False, "requiere": ":.1f", "municipalidades": True},
            color_continuous_scale="Oranges",
            labels={"requiere": "% requiere", "municipalidades": "Municipalidades"},
        )
        fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
        fig.update_layout(height=620, margin=dict(l=0, r=0, t=0, b=0),
                          coloraxis_colorbar=dict(orientation="h", y=-0.02, thickness=12, title="% requiere"))
        st.plotly_chart(fig, alt="Mapa del Perú con el porcentaje de municipalidades que requiere apoyo, por departamento")

    with col_ranking, st.container(border=True):
        st.subheader("Ranking de departamentos")
        ranking = por_departamento.sort_values("requiere")
        fig = px.bar(ranking, x="requiere", y="Departamento", orientation="h", text="requiere",
                     labels={"requiere": "% que requiere apoyo", "Departamento": ""})
        fig.update_traces(textposition="outside", textangle=0, cliponaxis=False)
        fig.update_xaxes(range=[0, 105])
        fig.update_layout(height=max(300, 22 * len(ranking) + 80), margin=dict(l=0, r=10, t=10, b=0))
        st.plotly_chart(fig, alt="Barras horizontales con el porcentaje que requiere apoyo en cada departamento")

    # ------------------------------------------------------------ Evolución y nivel de capacidad
    col_anio, col_nivel = st.columns(2)
    with col_anio, st.container(border=True):
        st.subheader("Evolución por tipo de apoyo")
        por_anio = (datos.groupby("anio")[list(APOYO.values())].mean() * 100).round(1)
        por_anio = por_anio.rename(columns={v: k for k, v in APOYO.items()})
        por_anio.index = por_anio.index.astype(str)
        fig = px.bar(por_anio, barmode="group", text_auto=True,
                     color_discrete_sequence=["#1F4E79", "#5B9BD5", "#A9C9EC"],
                     labels={"anio": "Edición del RENAMU", "value": "% de municipalidades", "variable": ""})
        fig.update_yaxes(range=[0, 100])
        fig.update_layout(legend=dict(orientation="h", y=-0.25), margin=dict(t=10))
        st.plotly_chart(fig, alt="Barras agrupadas por año con el porcentaje que requiere cada tipo de apoyo")

    with col_nivel, st.container(border=True):
        st.subheader("Según nivel de capacidad")
        por_nivel = (datos.groupby(["anio", "nivel_capacidad"])[columna].mean() * 100).round(1).reset_index()
        por_nivel["anio"] = por_nivel["anio"].astype(str)
        fig = px.bar(por_nivel, x="anio", y=columna, color="nivel_capacidad", barmode="group", text_auto=True,
                     category_orders={"nivel_capacidad": NIVELES}, color_discrete_map=COLORES,
                     labels={"anio": "Edición del RENAMU", columna: "% que requiere apoyo",
                             "nivel_capacidad": "Capacidad"})
        fig.update_yaxes(range=[0, 100])
        fig.update_layout(legend=dict(orientation="h", y=-0.25), margin=dict(t=10))
        st.plotly_chart(fig, alt="Barras por año y nivel de capacidad con el porcentaje que requiere apoyo")

    # ------------------------------------------------------------ Componentes del índice
    with st.container(border=True):
        st.subheader("Según cada componente de la capacidad")
        largo = datos.melt(id_vars=[columna], value_vars=list(COMPONENTES), var_name="componente",
                           value_name="cumple").dropna()
        por_componente = (largo.groupby(["componente", "cumple"])[columna].mean() * 100).round(1).reset_index()
        por_componente["componente"] = por_componente["componente"].map(COMPONENTES)
        por_componente["cumple"] = por_componente["cumple"].map({0: "No cumple", 1: "Cumple"})
        fig = px.bar(por_componente, x="componente", y=columna, color="cumple", barmode="group", text_auto=True,
                     color_discrete_map={"No cumple": "#E4572E", "Cumple": "#29335C"},
                     labels={"componente": "", columna: "% que requiere apoyo", "cumple": ""})
        fig.update_yaxes(range=[0, 100])
        fig.update_layout(height=380, margin=dict(t=10))
        st.plotly_chart(fig, alt="Barras con el porcentaje que requiere apoyo según si cumple o no cada componente")

with hallazgos:
    st.header("Hallazgos")
    st.markdown(
        "1. **La necesidad es generalizada y persistente.** Cerca de 8 de cada 10 municipalidades declaran "
        "requerir capacitación o asistencia técnica sobre el SISFOH (79,2 % en 2024, 80,4 % en 2025 y 77,0 % en 2026). "
        "El 53,9 % lo declaró en las tres ediciones y solo el 2,8 % en ninguna.\n"
        "2. **El nivel de capacidad no marca la diferencia.** En todos los niveles y años, entre 74 % y 82 % requiere "
        "apoyo, sin un patrón claro. Tener o no conexión fija, suficientes computadoras o mayoría de personal estable "
        "cambia la necesidad en menos de 3 puntos.\n"
        "3. **El territorio pesa más que la capacidad.** Entre departamentos, la necesidad va de 72,3 % (Áncash) "
        "a 88,4 % (Ayacucho) en el promedio 2024–2026.\n\n"
        "**Respuesta:** no. Las municipalidades con menos capacidades no requieren más apoyo que las demás; "
        "la necesidad es alta en todos los niveles."
    )

    st.header("Metodología")
    st.markdown(
        "- **Fuente:** Registro Nacional de Municipalidades (RENAMU) 2024, 2025 y 2026, Formulario 01, del INEI "
        "(portal de microdatos, descargado el 27/10/2026). 1 891 municipalidades por edición; se excluye Santa Rosa "
        "(Loreto), que solo aparece en 2026.\n"
        "- **Resultado:** pregunta 22, asistencia técnica (`P22_AT23`) y capacitación (`P22_C23`) que la municipalidad "
        "requiere sobre el Sistema de Focalización de Hogares.\n"
        "- **Índice de capacidad (0 a 3):** suma de tres componentes: (1) conexión fija a internet; (2) al menos 0,5 "
        "computadoras por trabajador; (3) al menos 50 % de personal estable (nombrados del D. Leg. 276 y D. Leg. 728). "
        "Capacidad **baja** (0–1), **media** (2) o **alta** (3).\n"
        "- **Mapa:** límites departamentales del INEI (versión simplificada usada en la sesión 06 del curso)."
    )

    st.header("Limitaciones")
    st.markdown(
        "- Es una **necesidad declarada**: no mide el desempeño de la municipalidad en el SISFOH.\n"
        "- Las capacidades son de **toda la municipalidad**, no de la Unidad Local de Empadronamiento (ULE).\n"
        "- **Personal estable** es una aproximación: excluye al CAS e incluye a todo el D. Leg. 728.\n"
        "- 307 registros (5,4 %) **no tienen información de personal** y no reciben índice.\n"
        "- Los umbrales del índice son decisiones de la autora; el resultado se mantiene por componente.\n"
        "- Es un análisis **descriptivo**: muestra asociación, no causalidad.\n"
        "- En departamentos con pocas municipalidades (Callao 7, Madre de Dios 11, Tumbes 13) los porcentajes "
        "cambian mucho con pocos casos."
    )

with tabla:
    st.subheader("Datos filtrados")
    st.dataframe(datos.drop(columns="cod_dep"), hide_index=True, alt="Tabla con los registros filtrados")
    st.download_button("Descargar CSV", datos.drop(columns="cod_dep").to_csv(index=False).encode("utf-8-sig"),
                       file_name="renamu_sisfoh_filtrado.csv", mime="text/csv", icon=":material/download:")

st.caption("Fuente: INEI, RENAMU 2024–2026. Elaboración propia. "
           "Código: [github.com/Clandra91/Python_intermedio](https://github.com/Clandra91/Python_intermedio)")