"""Punto de entrada para Streamlit Community Cloud.

Community Cloud instala las dependencias del primer archivo que encuentra en la carpeta del punto de entrada,
y en tarea_2/ ese archivo sería uv.lock (el entorno completo de los notebooks, con PaddleOCR y torch).
Por eso el despliegue arranca desde esta carpeta, que solo tiene el requirements.txt de la app,
y ejecuta tarea_2/app.py tal cual.
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent.parent / "app.py"), run_name="__main__")