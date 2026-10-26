"""Dashboard de la Tarea 2: documentos y audios peruanos convertidos en texto buscable.

Solo lee los CSV de datos/ (generados en 01_extraccion.ipynb y 02_evaluacion.ipynb):
no ejecuta OCR, ASR ni LLM en vivo.
"""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

CARPETA = Path(__file__).parent / "datos"
EJEMPLOS = CARPETA / "ejemplos"  # imágenes o audios con permiso de publicación (si existen)

st.set_page_config(page_title="Voces y documentos peruanos", page_icon="📄", layout="wide")


@st.cache_data
def cargar_datos():
    """Lee los CSV del proyecto y une a cada registro sus campos extraídos por el LLM."""
    documentos = pd.read_csv(CARPETA / "documentos.csv")
    clips = pd.read_csv(CARPETA / "transcripciones.csv")
    extraccion = pd.read_csv(CARPETA / "extraccion_llm.csv")
    extraccion["campos"] = extraccion["campos_json"].apply(json.loads)
    campos = dict(zip(extraccion["id"], extraccion["campos"]))
    tablas = {
        "documentos": documentos,
        "clips": clips,
        "campos": campos,
        "modelo_llm": extraccion["modelo_llm"].iloc[0],
        "auditoria": pd.read_csv(CARPETA / "auditoria_llm.csv"),
        "eval_ocr": pd.read_csv(CARPETA / "evaluacion_ocr.csv"),
        "eval_asr": pd.read_csv(CARPETA / "evaluacion_asr.csv"),
        "comparativa": pd.read_csv(CARPETA / "comparativa_modelos.csv"),
    }
    return tablas


def archivo_de_ejemplo(id_, extensiones):
    """Devuelve la ruta de un ejemplo publicable (imagen o audio) si existe en datos/ejemplos/."""
    for extension in extensiones:
        ruta = EJEMPLOS / f"{id_}{extension}"
        if ruta.exists():
            return ruta
    return None


def mostrar_campos_llm(campos):
    """Muestra en una tabla los campos extraídos por el LLM (sin repetir id ni modalidad)."""
    filas = [{"campo": k, "valor": ", ".join(v) if isinstance(v, list) else ("null" if v is None else str(v))}
             for k, v in campos.items() if k not in ("id", "modalidad")]
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")


datos = cargar_datos()
documentos, clips = datos["documentos"], datos["clips"]

# ----------------------------------------------------------------------------- encabezado
st.title("Voces y documentos peruanos: del archivo escaneado al texto buscable")
st.markdown("**¿Pueden convertirse documentos escaneados y entrevistas en audio en un archivo de texto "
            "estructurado y buscable?**")
with st.expander("Metodología (resumen)"):
    st.markdown(
        "- **Corpus A:** 25 documentos (8 impresos, 8 fotos con sombra o inclinación y 9 manuscritos), leídos con "
        "PaddleOCR 3.7.\n"
        "- **Corpus B:** 26 clips (37 minutos) de 3 conversaciones propias con consentimiento, transcritos con "
        "faster-whisper `small` + VAD y diarizados con WeSpeaker + k-means.\n"
        "- Los nombres reales se reemplazaron por seudónimos (`[PERSONA_n]`); los audios e imágenes originales no "
        "se publican.\n"
        "- **Evaluación:** CER y WER sobre 10 documentos y 10 clips con transcripción manual; OCR y ASR "
        "alternativos (Tesseract y Qwen3-ASR); extracción de campos con un LLM y auditoría humana de 20 casos.")

# ----------------------------------------------------------------------------- filtros
st.sidebar.header("Filtros")
busqueda = st.sidebar.text_input("Buscar palabra en los textos OCR y ASR", placeholder="Ej.: expediente")
tipos = st.sidebar.multiselect("Tipo de documento", ["impreso", "foto", "manuscrito"],
                               default=["impreso", "foto", "manuscrito"])
modelos_ocr = st.sidebar.multiselect("Modelo OCR", sorted(documentos["modelo_ocr"].unique()),
                                     default=sorted(documentos["modelo_ocr"].unique()))
fuentes = st.sidebar.multiselect("Fuente del audio", sorted(clips["fuente"].unique()),
                                 default=sorted(clips["fuente"].unique()))
duracion = st.sidebar.slider("Duración del clip (segundos)", 0, int(clips["duracion_seg"].max()) + 1,
                             (0, int(clips["duracion_seg"].max()) + 1))
modelos_eval = st.sidebar.multiselect(
    "Modelos en los gráficos de evaluación", ["PaddleOCR", "Tesseract", "faster-whisper", "Qwen3-ASR"],
    default=["PaddleOCR", "Tesseract", "faster-whisper", "Qwen3-ASR"])

docs_f = documentos[documentos["tipo"].isin(tipos) & documentos["modelo_ocr"].isin(modelos_ocr)]
clips_f = clips[clips["fuente"].isin(fuentes) & clips["duracion_seg"].between(*duracion)]
if busqueda:
    docs_f = docs_f[docs_f["texto_ocr"].str.contains(busqueda, case=False, regex=False)]
    clips_f = clips_f[clips_f["texto_asr"].str.contains(busqueda, case=False, regex=False)]

# ----------------------------------------------------------------------------- indicadores
comparativa = datos["comparativa"].set_index("modelo")["valor"]
cer = {m.split()[0]: v for m, v in comparativa.items() if m.startswith(("PaddleOCR", "Tesseract"))}
wer = {m.split()[0]: v for m, v in comparativa.items() if m.startswith(("faster-whisper", "Qwen3-ASR"))}
auditoria = datos["auditoria"]

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Documentos procesados", len(documentos), f"{len(docs_f)} con los filtros", delta_color="off")
col2.metric("Minutos de audio transcritos", f"{clips['duracion_seg'].sum() / 60:.1f}",
            f"{clips_f['duracion_seg'].sum() / 60:.1f} con los filtros", delta_color="off")
col3.metric("CER PaddleOCR (10 documentos)", f"{cer['PaddleOCR']:.3f}",
            f"Tesseract: {cer['Tesseract']:.3f}", delta_color="off")
col4.metric("WER faster-whisper (10 clips)", f"{wer['faster-whisper']:.3f}",
            f"Qwen3-ASR: {wer['Qwen3-ASR']:.3f}", delta_color="off")
col5.metric("Acuerdo LLM vs. auditoría", f"{auditoria['correcta'].mean():.0%}",
            f"{auditoria['correcta'].sum()}/{len(auditoria)} correctas", delta_color="off")

tab_resultados, tab_documentos, tab_audios = st.tabs(["📊 Resultados", "📄 Documentos", "🎧 Audios"])

# ----------------------------------------------------------------------------- resultados
with tab_resultados:
    # CER por tipo de documento y modelo (solo los tipos y modelos elegidos en los filtros)
    eval_ocr = datos["eval_ocr"][datos["eval_ocr"]["tipo"].isin(tipos)]
    cer_tipo = (eval_ocr.groupby("tipo")[["cer_paddle", "cer_tesseract"]].mean().reset_index()
                .rename(columns={"cer_paddle": "PaddleOCR", "cer_tesseract": "Tesseract"})
                .melt(id_vars="tipo", var_name="modelo", value_name="CER"))
    cer_tipo = cer_tipo[cer_tipo["modelo"].isin(modelos_eval)]
    fig = px.bar(cer_tipo, x="tipo", y="CER", color="modelo", barmode="group", text_auto=".2f",
                 title="Los impresos se leen casi sin errores; en los manuscritos PaddleOCR supera "
                       "ampliamente a Tesseract",
                 labels={"tipo": "Tipo de documento", "CER": "CER promedio (menor es mejor)"})
    st.plotly_chart(fig, width="stretch")

    # WER por fuente de audio y modelo
    eval_asr = datos["eval_asr"][datos["eval_asr"]["fuente"].isin(fuentes)]
    wer_fuente = (eval_asr.groupby("fuente")[["wer_whisper", "wer_qwen"]].mean().reset_index()
                  .rename(columns={"wer_whisper": "faster-whisper", "wer_qwen": "Qwen3-ASR"})
                  .melt(id_vars="fuente", var_name="modelo", value_name="WER"))
    wer_fuente = wer_fuente[wer_fuente["modelo"].isin(modelos_eval)]
    fig = px.bar(wer_fuente, x="fuente", y="WER", color="modelo", barmode="group", text_auto=".2f",
                 title="Los dos ASR quedan casi empatados; la conversación de trabajo (jerga y voces "
                       "superpuestas) es la más difícil",
                 labels={"fuente": "Fuente del audio", "WER": "WER promedio (menor es mejor)"})
    st.plotly_chart(fig, width="stretch")

    # Duración de los clips filtrados
    fig = px.bar(clips_f, x="id", y="duracion_seg", color="fuente",
                 title="La conversación familiar aporta casi la mitad de los minutos de audio",
                 labels={"id": "Clip", "duracion_seg": "Duración (segundos)", "fuente": "Fuente"})
    st.plotly_chart(fig, width="stretch")

    st.subheader("Tabla comparativa de modelos")
    st.dataframe(datos["comparativa"], hide_index=True, width="stretch")

# ----------------------------------------------------------------------------- documentos
with tab_documentos:
    st.subheader(f"Documentos ({len(docs_f)} de {len(documentos)})")
    columnas_doc = ["id", "tipo", "fuente", "caracteres", "confianza_ocr", "modelo_ocr", "texto_ocr"]
    st.dataframe(docs_f[columnas_doc], hide_index=True, width="stretch")
    st.download_button("Descargar CSV de documentos (filtrado)", docs_f[columnas_doc].to_csv(index=False),
                       "documentos_filtrados.csv", "text/csv")

    st.subheader("Explorador de documentos")
    if docs_f.empty:
        st.info("Ningún documento cumple los filtros.")
    else:
        id_doc = st.selectbox("Documento", docs_f["id"], key="doc")
        doc = documentos.set_index("id").loc[id_doc]
        izquierda, derecha = st.columns(2)
        with izquierda:
            st.markdown(f"**Tipo:** {doc['tipo']} · **Fuente:** {doc['fuente']}")
            imagen = archivo_de_ejemplo(id_doc, [".jpg", ".png"])
            if imagen:
                st.image(str(imagen), caption=f"{id_doc} (publicado con permiso de la autora)")
            else:
                st.caption("La imagen original no se publica; se muestra solo el texto extraído.")
            st.text_area("Texto OCR", doc["texto_ocr"], height=320)
        with derecha:
            st.markdown(f"**Campos extraídos por el LLM** (`{datos['modelo_llm']}`)")
            mostrar_campos_llm(datos["campos"][id_doc])
            evaluacion = datos["eval_ocr"].set_index("id")
            if id_doc in evaluacion.index:
                fila = evaluacion.loc[id_doc]
                st.markdown("**Documento de la muestra de evaluación**")
                c1, c2 = st.columns(2)
                c1.metric("CER PaddleOCR", f"{fila['cer_paddle']:.3f}")
                c2.metric("CER Tesseract", f"{fila['cer_tesseract']:.3f}")
                st.text_area("Texto de referencia (transcripción manual)", doc["texto_referencia"], height=200)

# ----------------------------------------------------------------------------- audios
with tab_audios:
    st.subheader(f"Clips de audio ({len(clips_f)} de {len(clips)})")
    columnas_audio = ["id", "fuente", "duracion_seg", "n_hablantes", "palabras", "modelo_asr", "texto_asr"]
    st.dataframe(clips_f[columnas_audio], hide_index=True, width="stretch")
    st.download_button("Descargar CSV de transcripciones (filtrado)", clips_f[columnas_audio].to_csv(index=False),
                       "transcripciones_filtradas.csv", "text/csv")

    st.subheader("Explorador de audios")
    if clips_f.empty:
        st.info("Ningún clip cumple los filtros.")
    else:
        id_clip = st.selectbox("Clip", clips_f["id"], key="clip")
        clip = clips.set_index("id").loc[id_clip]
        izquierda, derecha = st.columns(2)
        with izquierda:
            st.markdown(f"**Fuente:** {clip['fuente']} · **Duración:** {clip['duracion_seg']:.0f} s · "
                        f"**Hablantes:** {clip['n_hablantes']}")
            audio = archivo_de_ejemplo(id_clip, [".mp3", ".ogg", ".wav"])
            if audio:
                st.audio(str(audio))
            else:
                st.caption("Audio no publicado: las personas grabadas autorizaron la grabación, no su "
                           "publicación. Se muestra solo la transcripción seudonimizada.")
            # una línea por turno de habla, para leer quién dice qué
            st.text_area("Transcripción (faster-whisper small, con marcas de hablante)",
                         clip["texto_asr"].replace(" [HABLANTE_", "\n[HABLANTE_"), height=320)
        with derecha:
            st.markdown(f"**Campos extraídos por el LLM** (`{datos['modelo_llm']}`)")
            mostrar_campos_llm(datos["campos"][id_clip])
            evaluacion = datos["eval_asr"].set_index("id")
            if id_clip in evaluacion.index:
                fila = evaluacion.loc[id_clip]
                st.markdown("**Clip de la muestra de evaluación: comparación de los dos ASR**")
                c1, c2 = st.columns(2)
                c1.metric("WER faster-whisper", f"{fila['wer_whisper']:.2f}", f"RTF {fila['rtf_whisper']:.2f}",
                          delta_color="off")
                c2.metric("WER Qwen3-ASR", f"{fila['wer_qwen']:.2f}", f"RTF {fila['rtf_qwen']:.2f}",
                          delta_color="off")
                st.text_area("Texto de referencia (transcripción manual)", clip["texto_referencia"], height=200)

st.caption("Tarea 2 – Python Intermedio. Datos propios seudonimizados y publicación de SERVIR (2016). "
           "Los modelos se ejecutaron en los notebooks; esta app solo lee sus resultados.")