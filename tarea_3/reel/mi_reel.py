"""Reel de la Tarea 3: guion.json -> voz clonada -> video 1080x1920 con imágenes, subtítulos y música.

Usa reel.py de la sesión 15 del curso (Data-Science-Python) y le agrega:
  - una imagen (gráfico o mapa) debajo de la cifra de cada escena,
  - subtítulos que escriben SISFOH aunque en el guion se escriba "sisfo" para que la voz lo pronuncie bien,
  - música de fondo con licencia, más baja que la voz,
  - la narración guardada, para volver a armar el video sin generar la voz otra vez (--solo-video).

Desde la carpeta tarea_3/reel:
    .venv\\Scripts\\python.exe mi_reel.py               # todo: voz (~25 min) + video
    .venv\\Scripts\\python.exe mi_reel.py --solo-video  # solo el video, con la narración ya guardada
"""
import argparse
import json
import re
import subprocess
import time

import numpy as np
import soundfile as sf
from PIL import Image, ImageChops, ImageDraw

import reel

# ---------------------------------------------------------------- Datos del video (editar aquí)
AUTORA = "Claudia Pérez"
FUENTE = "RENAMU 2024–2026, INEI"
MUSICA = reel.AQUI / "musica.mp3"
CREDITO_MUSICA = "Música: «Inspirational - Inspirational Music» de NastelBom (Pixabay)"
VOZ = reel.AQUI / "mi_voz.m4a"
TTS = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"   # el modelo pequeño: el de 1.7B no entra en 8 GB de RAM
SALIDAS = reel.AQUI / "salidas"

# "sisfo", "Sisfo", "CISFO", "SIFO"...: como lo escriba Whisper, en los subtítulos se lee SISFOH
SISFOH = re.compile(r"(?i)\b[cs]i?s?f[oó]h?\b")
_escena_original = reel._escena


def escena_con_imagen(e):
    """Cifra y etiqueta arriba, imagen debajo. Si la escena no tiene imagen, se usa el diseño original."""
    ruta = reel.AQUI / e["imagen"] if e.get("imagen") else None
    if ruta is None or not ruta.exists():
        return _escena_original(e)

    capa = Image.new("RGBA", (reel.ANCHO, reel.ALTO), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    ancho = reel.ANCHO - 2 * reel.MARGEN
    y = 420                                   # debajo del aviso "VOZ GENERADA CON IA"
    if e.get("cifra"):
        f = reel._ajustar(d, e["cifra"], "Oswald", 700, ancho, 170, 90)
        d.text((reel.MARGEN, y), e["cifra"], font=f, fill=reel.TEXTO, anchor="lt")
        y = d.textbbox((reel.MARGEN, y), e["cifra"], font=f, anchor="lt")[3] + 24
        fe, color = reel._fuente("PublicSans", 46, 600), reel.SUAVE
    else:
        fe, color = reel._fuente("Oswald", 72, 600), reel.TEXTO
    for linea in reel._envolver(d, e["etiqueta"], fe, ancho):
        d.text((reel.MARGEN, y), linea, font=fe, fill=color, anchor="lt")
        y += int(fe.size * 1.3)

    imagen = Image.open(ruta).convert("RGBA")
    # Se recortan los bordes del mismo color del fondo, para que el gráfico o mapa ocupe todo el espacio
    borde = ImageChops.difference(imagen.convert("RGB"), Image.new("RGB", imagen.size, reel.FONDO)).getbbox()
    if borde:
        imagen = imagen.crop(borde)
    imagen.thumbnail((ancho, 1245 - (y + 20)))   # hasta 1245: debajo van los subtítulos
    capa.paste(imagen, (reel.MARGEN + (ancho - imagen.width) // 2, y + 20), imagen)
    return capa


def subtitulos_con_sisfoh(narracion, guion):
    """Whisper recibe el guion con "SISFOH" como contexto y, por si acaso, se corrige cada palabra."""
    contexto = {"escenas": [{"frase": SISFOH.sub("SISFOH", e["frase"])} for e in guion["escenas"]]}
    reel.subtitulos(narracion, contexto)
    # En el silencio final, Whisper a veces "inventa" palabras: se quitan las que empiezan después de la narración
    fin_narracion = narracion.escenas[-1][1] + 0.3
    narracion.palabras = [(ini, fin, SISFOH.sub("SISFOH", p).replace("Ancash", "Áncash"))
                          for ini, fin, p in narracion.palabras if ini < fin_narracion]

    # Signos de pregunta: Whisper no escribe el "¿" y, si la voz no sube el tono, pone punto en vez de "?"
    for (inicio, fin_escena), e in zip(narracion.escenas, guion["escenas"]):
        en_escena = [i for i, (ini, _, _) in enumerate(narracion.palabras) if inicio - 0.3 <= ini <= fin_escena]
        if not en_escena:
            continue
        primera = en_escena[0]
        if e["frase"].startswith("¿") and not narracion.palabras[primera][2].startswith("¿"):
            ini, fin, p = narracion.palabras[primera]
            narracion.palabras[primera] = (ini, fin, "¿" + p)
        for antes in re.findall(r"(\w+)\?", e["frase"]):   # palabra que va antes de cada "?" en el guion
            for i in en_escena:
                ini, fin, p = narracion.palabras[i]
                if p.rstrip(".,").lower() == antes.lower():
                    narracion.palabras[i] = (ini, fin, p.rstrip(".,?") + "?")
                    break


def agregar_musica(video, musica, salida, duracion):
    """Mezcla la música (en bucle, a -30 LUFS) debajo de la voz (-14 LUFS), con entrada y salida suaves."""
    filtro = (f"[1:a]loudnorm=I=-30:TP=-3,afade=t=in:d=1.5,afade=t=out:st={max(duracion - 2.5, 0):.2f}:d=2.5[m];"
              "[0:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.9[a]")
    subprocess.run([reel.FFMPEG, "-y", "-v", "error", "-i", str(video), "-stream_loop", "-1", "-i", str(musica),
                    "-filter_complex", filtro, "-map", "0:v", "-map", "[a]", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest", "-movflags", "+faststart",
                    str(salida)], check=True)


def guardar_narracion(narracion):
    sf.write(SALIDAS / "narracion.wav", narracion.audio, narracion.sr)
    (SALIDAS / "narracion.json").write_text(json.dumps({"sr": narracion.sr, "escenas": narracion.escenas}))


def cargar_narracion():
    info = json.loads((SALIDAS / "narracion.json").read_text())
    audio, sr = sf.read(SALIDAS / "narracion.wav", dtype="float32")
    return reel.Narracion(np.asarray(audio, np.float32), sr, [tuple(x) for x in info["escenas"]])


def hacer_video(guion, narracion, t0):
    reel._escena = escena_con_imagen          # reel.video() y reel.portada() dibujan ahora las escenas con imagen
    subtitulos_con_sisfoh(narracion, guion)
    reel.a_srt(narracion, SALIDAS / "reel.srt")
    reel._reloj(f"subtítulos: {len(narracion.palabras)} palabras", t0)

    creditos = f"{FUENTE} · {CREDITO_MUSICA}"
    reel.portada(guion, narracion, SALIDAS / "portada.png", creditos, AUTORA)
    reel.video(guion, narracion, SALIDAS / "reel_sin_musica.mp4", creditos, AUTORA)
    reel._reloj("video sin música listo", t0)

    if MUSICA.exists():
        agregar_musica(SALIDAS / "reel_sin_musica.mp4", MUSICA, SALIDAS / "reel.mp4", narracion.duracion)
        reel._reloj(f"listo: {SALIDAS / 'reel.mp4'} ({narracion.duracion:.1f} s)", t0)
    else:
        print(f"¡Ojo! No se encontró {MUSICA.name}: el video quedó sin música (reel_sin_musica.mp4).")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--solo-video", action="store_true", help="usa la narración guardada en salidas/")
    a = p.parse_args()

    t0 = time.time()
    SALIDAS.mkdir(exist_ok=True)
    guion = json.loads((reel.AQUI / "guion.json").read_text(encoding="utf-8"))

    if a.solo_video:
        narracion = cargar_narracion()
    else:
        voz = reel.Voz(VOZ, modelo=TTS)
        reel._reloj(f"voz cargada; referencia: «{voz.texto_ref}»", t0)
        narracion = reel.narrar(voz, guion)
        guardar_narracion(narracion)
        (SALIDAS / "guion_con_wer.json").write_text(json.dumps(guion, ensure_ascii=False, indent=2), encoding="utf-8")
        reel._reloj(f"narración: {narracion.duracion:.1f} s; WER por escena: "
                    + ", ".join(f"{e['wer']:.2f}" for e in guion["escenas"]), t0)

    hacer_video(guion, narracion, t0)
