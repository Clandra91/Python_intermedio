"""Mueve las capturas de pantalla a evidencias_ia/ y las numera en orden (01.png, 02.png...).

Uso, desde la carpeta tarea_2:
    uv run python mover_capturas.py

Se puede ejecutar cada día: la numeración continúa desde la última captura guardada.
"""
import shutil
from pathlib import Path

ORIGEN = Path(r"C:\Users\LENOVO\Videos\Captures")
DESTINO = Path(__file__).parent / "evidencias_ia"
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
    mover_y_numerar(ORIGEN, DESTINO)
