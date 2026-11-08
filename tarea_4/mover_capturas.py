"""Mueve las capturas de pantalla a evidencias_ia/<carpeta>/ y las numera en orden (01.png, 02.png...).

Uso, desde la carpeta tarea_4:
    uv run python mover_capturas.py mcp            # Parte 1
    uv run python mover_capturas.py skills         # Parte 2
    uv run python mover_capturas.py integracion    # Parte 3
    uv run python mover_capturas.py evaluacion     # Parte 4

Se puede ejecutar varias veces: la numeración continúa desde la última captura guardada en esa carpeta.
Es el mover_capturas.py de la Tarea 2, adaptado para elegir la carpeta de cada parte.
"""
import shutil
import sys
from pathlib import Path

ORIGEN = Path(r"C:\Users\LENOVO\Videos\Captures")
EVIDENCIAS = Path(__file__).parent / "evidencias_ia"
CARPETAS = ["mcp", "skills", "integracion", "evaluacion"]
EXTENSIONES = {".png", ".jpg", ".jpeg"}


def ultimo_numero(carpeta):
    """Devuelve el número más alto ya usado en la carpeta (0 si todavía no hay capturas)."""
    numeros = [int(f.stem) for f in carpeta.iterdir() if f.stem.isdigit()]
    return max(numeros, default=0)


def capturas_en_orden(carpeta):
    """Lista las imágenes de la carpeta, de la más antigua a la más reciente."""
    imagenes = [f for f in carpeta.iterdir() if f.suffix.lower() in EXTENSIONES]
    return sorted(imagenes, key=lambda f: f.stat().st_mtime)


def mover_y_numerar(origen, destino):
    """Mueve las capturas al destino y las numera a continuación de las que ya existen."""
    destino.mkdir(parents=True, exist_ok=True)
    siguiente = ultimo_numero(destino) + 1
    capturas = capturas_en_orden(origen)
    for captura in capturas:
        nuevo = destino / f"{siguiente:02d}{captura.suffix.lower()}"
        shutil.move(captura, nuevo)
        print(f"{captura.name}  ->  {nuevo.name}")
        siguiente += 1
    print(f"Se movieron {len(capturas)} capturas a {destino}")


if __name__ == "__main__":
    # sys.argv[1] es la palabra que se escribe después del nombre del script
    if len(sys.argv) != 2 or sys.argv[1] not in CARPETAS:
        sys.exit(f"Falta la carpeta de destino: {', '.join(CARPETAS)}. Ejemplo: uv run python mover_capturas.py mcp")
    mover_y_numerar(ORIGEN, EVIDENCIAS / sys.argv[1])
