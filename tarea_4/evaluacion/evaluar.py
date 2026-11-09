"""¿Mejoran el MCP del BCRP y las Skills de la ENAHO las respuestas de Claude? Las mismas 10 preguntas en dos modos.

    uv run evaluacion/evaluar.py                          # modos A y B, con Haiku
    uv run evaluacion/evaluar.py --modelo sonnet
    uv run evaluacion/evaluar.py --ids bcrp_tasa_dic24 enaho_ica --modos B

Adaptado de sessions/04-mcp-claude-code/proyecto/evaluar.py. Cada pregunta va en una sesión nueva de claude -p
(no recuerda las anteriores), con la misma instrucción y el mismo modelo en los dos modos:
  A: sin ninguna herramienta (ni MCP, ni Skills, ni archivos, ni terminal, ni web), desde una carpeta temporal
     fuera del proyecto, para que no vea los archivos con las respuestas.
  B: con el MCP bcrp, las Skills del proyecto, Read y la terminal solo para «uv run»; sin web y sin poder leer
     evaluacion/, informes/ ni evidencias_ia/, donde ya están las respuestas.
Escribe evaluacion/resultados.csv y guarda cada conversación completa en evidencias_ia/evaluacion/registros/.
"""
import argparse
import json
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).parent
PROYECTO = AQUI.parent
REGISTROS = PROYECTO / "evidencias_ia" / "evaluacion" / "registros"
CARPETA_A = tempfile.mkdtemp(prefix="evaluacion_modo_A_")

SIMPLE = {"type": "object", "required": ["valor", "fuente"],
          "properties": {"valor": {"type": ["number", "null"]}, "unidad": {"type": "string"},
                         "fuente": {"type": "string"}}}
MIXTA = {"type": "object", "required": ["valor_bcrp", "valor_enaho", "si_no", "fuente", "explicacion"],
         "properties": {"valor_bcrp": {"type": ["number", "null"]}, "valor_enaho": {"type": ["number", "null"]},
                        "si_no": {"type": ["boolean", "null"]}, "fuente": {"type": "string"},
                        "explicacion": {"type": "string"}}}
INSTRUCCION = ("Si tienes herramientas o Skills para consultar las fuentes oficiales, úsalas antes de responder. "
               "Responde con cifras, en la unidad que pide la pregunta. Si no puedes saber una cifra con certeza, "
               "pon null: no estimes. En «fuente» di de dónde sale cada cifra.\n\n")
INSTRUCCION_MIXTA = ("Pon la cifra del BCRP en «valor_bcrp», la de la ENAHO en «valor_enaho» y la respuesta a la "
                     "pregunta de sí o no en «si_no» (true = sí); justifícala en «explicacion».\n\n")
MODOS = {
    "A": ["--tools", "", "--strict-mcp-config", "--disable-slash-commands"],
    "B": ["--tools", "Skill,Read,Bash,PowerShell", "--strict-mcp-config", "--mcp-config", str(PROYECTO / ".mcp.json"),
          "--allowedTools", "mcp__bcrp,Skill,Read,Bash(uv run *),PowerShell(uv run *)",
          "--disallowedTools", "Read(./evaluacion/**),Read(./informes/**),Read(./evidencias_ia/**)"],
}


def herramientas(mensajes):
    """Las que tenía la sesión (mensaje init) y las que usó de verdad; StructuredOutput es solo la forma de responder."""
    init = next((m for m in mensajes if m.get("subtype") == "init"), {})
    habilitadas = [t.replace("mcp__bcrp__", "bcrp.") for t in init.get("tools", []) if t != "StructuredOutput"]
    mcp = ", ".join(f"{s['name']} {s['status']}" for s in init.get("mcp_servers", [])) or "sin MCP"
    usadas = []
    for m in mensajes:
        if m.get("type") != "assistant":
            continue
        for b in m["message"]["content"]:
            if b.get("type") == "tool_use" and b["name"] != "StructuredOutput":
                nombre = b["name"].replace("mcp__bcrp__", "bcrp.")
                if nombre == "Skill":
                    nombre += ":" + b["input"].get("skill", "")
                usadas.append(nombre)
    return {"habilitadas": ", ".join(habilitadas) or "ninguna", "mcp": mcp, "herramientas": "; ".join(usadas) or "ninguna"}


def preguntar(q, modo, modelo):
    mixta = q.tipo == "mixta"
    cmd = ["claude", "-p", INSTRUCCION + (INSTRUCCION_MIXTA if mixta else "") + q.pregunta,
           "--output-format", "stream-json", "--verbose", "--json-schema", json.dumps(MIXTA if mixta else SIMPLE),
           "--no-session-persistence", "--model", modelo, *MODOS[modo]]
    t = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=600,
                              cwd=PROYECTO if modo == "B" else CARPETA_A)
        salida, aviso = proc.stdout, proc.stderr.strip()
    except subprocess.TimeoutExpired:
        salida, aviso = "", "tiempo agotado (600 s)"
    segundos = round(time.time() - t, 1)
    (REGISTROS / f"{modo}_{q.id}.jsonl").write_text(salida, encoding="utf-8")

    mensajes = [json.loads(linea) for linea in salida.splitlines() if linea.startswith("{")]
    final = next((m for m in mensajes if m.get("type") == "result"), {})
    r = final.get("structured_output") or {}
    error = "" if r else (aviso or str(final.get("result", "sin respuesta")))[-300:]
    return {**r, **herramientas(mensajes), "segundos": segundos, "turnos": final.get("num_turns"), "error": error}


def dentro(valor, esperada, tolerancia):
    return valor is not None and abs(valor - esperada) <= tolerancia


def calificar(q, r):
    """Simples: correcta si la cifra cae en la tolerancia. Mixtas: las dos cifras (exactitud) y el sí/no (coherencia)."""
    if q.tipo != "mixta":
        if r.get("valor") is None:
            return "error" if r["error"] else "no responde"
        return "correcta" if dentro(r["valor"], q.esperada, q.tolerancia) else "incorrecta"
    if all(r.get(k) is None for k in ("valor_bcrp", "valor_enaho", "si_no")):
        return "error" if r["error"] else "no responde"
    partes = [dentro(r.get("valor_bcrp"), q.esperada, q.tolerancia),
              dentro(r.get("valor_enaho"), q.esperada_2, q.tolerancia_2),
              r.get("si_no") is not None and r["si_no"] == (q.esperada_si_no == "sí")]
    return "correcta" if all(partes) else "parcial" if any(partes) else "incorrecta"


def texto(v):
    return "null" if v is None else "sí" if v is True else "no" if v is False else str(v)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--modos", nargs="+", default=["A", "B"], choices=list(MODOS))
    p.add_argument("--modelo", default="haiku")
    p.add_argument("--ids", nargs="+", help="solo estas preguntas (por defecto, las 10)")
    p.add_argument("--paralelo", type=int, default=4, help="preguntas a la vez en el modo A")
    a = p.parse_args()

    preguntas = pd.read_csv(AQUI / "preguntas.csv", dtype={"esperada_si_no": str})
    if a.ids:
        preguntas = preguntas[preguntas.id.isin(a.ids)]
    REGISTROS.mkdir(parents=True, exist_ok=True)
    casos, respuestas = [], []
    for m in a.modos:
        lote = [(q, m) for q in preguntas.itertuples()]
        # En el modo B van de a una: si arrancan varios servidores MCP a la vez, alguno no llega a conectarse
        n = a.paralelo if m == "A" else 1
        print(f"Modo {m}: {len(lote)} llamadas a claude -p con {a.modelo}, {n} a la vez...")
        with ThreadPoolExecutor(n) as ex:
            respuestas += list(ex.map(lambda c: preguntar(c[0], c[1], a.modelo), lote))
        casos += lote

    filas = []
    for (q, m), r in zip(casos, respuestas):
        if q.tipo == "mixta":
            esperada = f"{q.esperada} | {q.esperada_2} | {q.esperada_si_no}"
            generada = " | ".join(texto(r.get(k)) for k in ("valor_bcrp", "valor_enaho", "si_no"))
        else:
            esperada, generada = str(q.esperada), texto(r.get("valor"))
        filas.append({"id": q.id, "tipo": q.tipo, "modo": m, "modelo": a.modelo, "pregunta": q.pregunta,
                      "esperada": esperada, "generada": generada, "resultado": calificar(q, r),
                      "fuente": r.get("fuente", ""), "explicacion": r.get("explicacion", ""),
                      "herramientas": r["herramientas"], "habilitadas": r["habilitadas"], "mcp": r["mcp"],
                      "segundos": r["segundos"], "turnos": r["turnos"], "error": r["error"]})
    res = pd.DataFrame(filas)
    res.to_csv(AQUI / "resultados.csv", index=False, encoding="utf-8-sig")

    print("\n" + res.pivot(index="id", columns="modo", values="resultado").to_string())
    tabla = res.groupby("modo").resultado.value_counts().unstack(fill_value=0)
    tabla["segundos promedio"] = res.groupby("modo").segundos.mean().round(1)
    print("\n" + tabla.to_string())
