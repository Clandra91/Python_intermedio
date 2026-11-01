"""Vuelve a generar la voz de UNA escena y la reemplaza en la narración guardada (salidas/narracion.wav).

Sirve cuando solo cambió la frase de una escena en guion.json: tarda unos 10 minutos en vez de 30.
Desde la carpeta tarea_3/reel:
    .venv\\Scripts\\python.exe rehacer_escena.py 1       # número de la escena (1 = la primera)
    .venv\\Scripts\\python.exe mi_reel.py --solo-video   # después, para armar el video otra vez
"""
import json
import sys
import time

import numpy as np

import mi_reel
import reel

numero = int(sys.argv[1])
t0 = time.time()
guion = json.loads((reel.AQUI / "guion.json").read_text(encoding="utf-8"))
frase = guion["escenas"][numero - 1]["frase"]
anterior = mi_reel.cargar_narracion()
sr = anterior.sr

# Se separa la narración guardada en el audio de cada escena
partes = [anterior.audio[int(ini * sr):int(fin * sr)] for ini, fin in anterior.escenas]

# Nueva voz para la escena; si Whisper no la entiende bien (WER alto), se intenta otra vez y se queda la mejor
voz = reel.Voz(mi_reel.VOZ, modelo=mi_reel.TTS)
reel._reloj(f"voz cargada; escena {numero}: «{frase}»", t0)
mejor, mejor_wer = None, None
for intento in range(1, 4):
    audio = np.asarray(voz.decir([frase])[0], np.float32)
    wer = reel._wer(frase, reel._a16k(audio, voz.sr))
    reel._reloj(f"intento {intento}: WER {wer:.2f}", t0)
    if mejor_wer is None or wer < mejor_wer:
        mejor, mejor_wer = audio, wer
    if wer <= 0.1:
        break
assert voz.sr == sr, "la frecuencia de la voz nueva no coincide con la de la narración guardada"
partes[numero - 1] = mejor

# Se vuelve a unir todo con los mismos silencios que usa reel.narrar()
trozos, escenas, t = [np.zeros(int(reel.INICIO * sr), np.float32)], [], reel.INICIO
for parte in partes:
    escenas.append((t, t + len(parte) / sr))
    trozos += [parte, np.zeros(int(reel.PAUSA * sr), np.float32)]
    t += len(parte) / sr + reel.PAUSA
trozos.append(np.zeros(int(reel.FINAL * sr), np.float32))
narracion = reel.Narracion(np.concatenate(trozos), sr, escenas)
mi_reel.guardar_narracion(narracion)
reel._reloj(f"listo: narración de {narracion.duracion:.1f} s (WER de la escena {numero}: {mejor_wer:.2f}). "
            "Ahora: .venv\\Scripts\\python.exe mi_reel.py --solo-video", t0)
