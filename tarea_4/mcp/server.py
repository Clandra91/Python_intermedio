"""Servidor MCP del BCRP: busca, descarga, resume y grafica las series oficiales del Banco Central de Reserva del Perú.

    uv run pytest -q                                           # las 8 pruebas del curso y las 2 propias
    uv run mcp/server.py                                       # el servidor, por stdio
    claude mcp add --scope project bcrp -- uv run mcp/server.py # conectarlo a Claude Code

Las cuentas las hace Python, no el modelo: así cada cifra sale de una llamada que se puede repetir.
Base: el proyecto de la sesión 04 (buscar_series ya venía hecho); los TODO 1 a 5 se completaron con apoyo de Claude.
"""
import re
import time
import unicodedata
from datetime import date
from functools import cache
from pathlib import Path

import httpx
import matplotlib
matplotlib.use("Agg")  # sin ventanas: el servidor solo guarda el PNG
import matplotlib.pyplot as plt
import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

AQUI = Path(__file__).parent
CATALOGO = AQUI / "datos" / "catalogo_bcrp.csv"
FIGURAS = AQUI.parent / "figuras"
URL_CATALOGO = "https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
WEB = "https://estadisticas.bcrp.gob.pe/estadisticas/series"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}

MESES = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
         "Jul": 7, "Ago": 8, "Set": 9, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}
CARPETA_WEB = {"Diaria": "diarias", "Mensual": "mensuales", "Trimestral": "trimestrales", "Anual": "anuales"}
# Las series que más se consultan, para el recurso bcrp://series/frecuentes
FRECUENTES = ["PN01273PM", "PN01271PM", "PN01728AM", "PD04722MM", "PD04638PD", "PN01652XM"]

mcp = FastMCP("bcrp", instructions=(
    "Series oficiales del Banco Central de Reserva del Perú (BCRP). Primero busca el código con buscar_series; "
    "luego usa resumen para variaciones, promedios y extremos, serie para los datos y graficar_serie para una "
    "figura. No calcules a mano: cita siempre el código de la serie, el periodo y la fuente."))


def _sin_tildes(s):
    return unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode()


@cache
def catalogo():
    """El catálogo oficial: 17 mil series en unos 7 MB. Se baja una vez y queda en datos/."""
    if not CATALOGO.exists():
        CATALOGO.parent.mkdir(exist_ok=True)
        r = httpx.get(URL_CATALOGO, timeout=120)
        r.raise_for_status()
        CATALOGO.write_text(r.content.decode("latin-1"), encoding="utf-8")
    df = pd.read_csv(CATALOGO, sep=";", dtype=str).fillna("")
    df = df.rename(columns={"Código de serie": "codigo", "Categoría de serie": "categoria", "Grupo de serie": "grupo",
                            "Nombre de serie": "nombre", "Frecuencia": "frecuencia",
                            "Fecha de actualización": "actualizada", "Fecha de inicio": "inicio"})
    df["texto"] = (df.categoria + " " + df.grupo + " " + df.nombre).map(_sin_tildes)
    return df


def _ficha(codigo):
    fila = catalogo().query("codigo == @codigo")
    if fila.empty:
        raise ToolError(f"No existe el código de serie {codigo!r}. Búsquenlo con buscar_series.")
    f = fila.iloc[0]
    return {"codigo": f.codigo, "nombre": f"{f.grupo} - {f.nombre}", "categoria": f.categoria,
            "frecuencia": f.frecuencia, "inicio": f.inicio, "actualizada": f.actualizada}


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_series(texto: str, frecuencia: str | None = None, limite: int = 10) -> list[dict]:
    """Busca series del BCRP por palabras: todas deben aparecer en la categoría, el grupo o el nombre.

    Ejemplos: "ipc 12 meses", "tipo de cambio interbancario venta", "reservas internacionales netas",
    "tasa de referencia", "cobre precio". frecuencia: "Diaria", "Mensual", "Trimestral" o "Anual".
    Devuelve el código, el nombre completo, la frecuencia y desde cuándo hay datos. Si no hay resultados,
    prueben con menos palabras.
    """
    df = catalogo()
    m = pd.Series(True, index=df.index)
    for palabra in _sin_tildes(texto).split():
        m &= df.texto.str.contains(re.escape(palabra))
    if frecuencia:
        m &= df.frecuencia.str.lower() == frecuencia.lower()
    # primero las series vigentes y, entre ellas, las de nombre más corto (las más generales)
    sel = df[m]
    orden = sel.assign(vieja=sel.actualizada < "2025", largo=(sel.grupo + sel.nombre).str.len())
    return [_ficha(c) for c in orden.sort_values(["vieja", "largo"]).head(limite).codigo]


# --- Fechas: lo que recibe la herramienta, lo que pide la API y lo que devuelve -------------------------------

def _fecha_api(fecha, frecuencia, final=False):
    """Pasa "2025-01", "2025-T1" o "2026-10-15" al formato que pide la API: 2025-1, 2025-1, 2026-10-15 o 2025.

    Si falta el mes o el día, se completa con el primero (desde) o el último (hasta) del periodo.
    """
    numeros = [int(n) for n in re.findall(r"\d+", str(fecha))]
    if not numeros:
        raise ToolError(f"No entiendo la fecha {fecha!r}. Usen 2025, 2025-01, 2025-T1 o 2025-01-15.")
    anio = numeros[0]
    if frecuencia == "Anual":
        return f"{anio}"
    if frecuencia == "Trimestral":
        if len(numeros) == 1:
            return f"{anio}-{4 if final else 1}"
        trimestre = numeros[1] if "T" in str(fecha).upper() else (numeros[1] + 2) // 3  # un mes pasa a su trimestre
        return f"{anio}-{trimestre}"
    mes = numeros[1] if len(numeros) > 1 else (12 if final else 1)
    if frecuencia == "Mensual":
        return f"{anio}-{mes}"
    ultimo_dia = pd.Period(f"{anio}-{mes:02d}", freq="M").days_in_month
    dia = numeros[2] if len(numeros) > 2 else (ultimo_dia if final else 1)
    return f"{anio}-{mes:02d}-{dia:02d}"


def _anio(texto):
    """Los años de dos cifras (26, 97) pasan a cuatro: 2026, 1997."""
    anio = int(texto)
    if anio < 100:
        anio += 2000 if anio <= date.today().year % 100 else 1900
    return anio


def _periodo(nombre):
    """Pasa el periodo de la API a un formato ordenable: Ene.2025 → 2025-01, 01.Oct.26 → 2026-10-01,
    T1.25 → 2025-T1 y 2025 → 2025."""
    partes = nombre.split(".")
    if len(partes) == 3:                                    # diaria
        dia, mes, anio = partes
        return f"{_anio(anio)}-{MESES[mes]:02d}-{int(dia):02d}"
    if len(partes) == 2 and partes[0] in MESES:             # mensual
        return f"{_anio(partes[1])}-{MESES[partes[0]]:02d}"
    if len(partes) == 2 and partes[0].startswith("T"):      # trimestral
        return f"{_anio(partes[1])}-{partes[0]}"
    return nombre                                           # anual


@cache
def _pedir(codigo, desde, hasta):
    """Llama a la API. Si responde una página HTML (por pedidos seguidos), espera y reintenta hasta 3 veces.

    @cache guarda lo que ya se bajó: la misma consulta no se vuelve a pedir mientras el servidor esté abierto.
    """
    url = f"{API}/{codigo}/json/{desde}/{hasta}"
    for espera in (0, 3, 6):
        time.sleep(espera)
        try:
            return url, httpx.get(url, timeout=60).json()
        except (httpx.HTTPError, ValueError):               # ValueError: llegó HTML en vez de JSON
            continue
    raise ToolError(f"El BCRP no respondió con datos para {codigo}. Esperen unos segundos y reintenten.")


def _serie(codigo, desde, hasta):
    ficha = _ficha(codigo)                                  # si el código no existe, aquí sale el ToolError
    frecuencia = ficha["frecuencia"]
    api_desde, api_hasta = _fecha_api(desde, frecuencia), _fecha_api(hasta, frecuencia, final=True)
    url, respuesta = _pedir(codigo, api_desde, api_hasta)
    decimales = int(respuesta["config"]["series"][0].get("dec", 4))  # los mismos que publica el BCRP en su web
    datos = [{"periodo": _periodo(p["name"]), "valor": round(float(p["values"][0]), decimales)}
             for p in respuesta.get("periods", []) if p["values"][0] != "n.d."]
    if not datos:
        raise ToolError(f"La serie {codigo} no tiene datos entre {desde} y {hasta}. Hay datos desde {ficha['inicio']}.")
    return {"codigo": codigo, "nombre": ficha["nombre"], "frecuencia": frecuencia, "datos": datos, "fuente": url,
            "tabla_web": f"{WEB}/{CARPETA_WEB.get(frecuencia, 'mensuales')}/resultados/{codigo}/html/"
                         f"{api_desde}/{api_hasta}/"}


def _resumen(codigo, desde, hasta):
    s = _serie(codigo, desde, hasta)
    d = pd.DataFrame(s["datos"])
    primero, ultimo = d.iloc[0], d.iloc[-1]

    def punto(fila):
        return {"periodo": fila.periodo, "valor": float(fila.valor)}

    return {"codigo": codigo, "nombre": s["nombre"], "frecuencia": s["frecuencia"], "n_datos": len(d),
            "primero": punto(primero), "ultimo": punto(ultimo),
            "cambio": round(float(ultimo.valor - primero.valor), 4),
            "variacion_pct": round(float((ultimo.valor / primero.valor - 1) * 100), 2) if primero.valor else None,
            "promedio": round(float(d.valor.mean()), 4),
            "maximo": punto(d.loc[d.valor.idxmax()]), "minimo": punto(d.loc[d.valor.idxmin()]),
            "fuente": s["fuente"], "tabla_web": s["tabla_web"]}


# TODO 1 · serie
@mcp.tool(annotations=SOLO_LECTURA)
def serie(codigo: str, desde: str, hasta: str) -> dict:
    """Descarga los datos de una serie del BCRP entre dos fechas, tal como los publica el banco.

    Úsenla cuando necesiten los valores periodo por periodo. Para variaciones, promedios o extremos usen resumen.
    Fechas según la frecuencia de la serie: "2025-01" (mensual), "2025-T1" (trimestral), "2025" (anual) o
    "2026-10-15" (diaria). Ejemplo: codigo="PN01273PM", desde="2025-01", hasta="2025-12".
    Devuelve los datos como [{"periodo", "valor"}], la URL de la API (fuente) y la tabla en la web del BCRP.
    """
    return _serie(codigo, desde, hasta)


# TODO 2 · resumen
@mcp.tool(annotations=SOLO_LECTURA)
def resumen(codigo: str, desde: str, hasta: str) -> dict:
    """Calcula con Python el primer y el último valor, el cambio, la variación %, el promedio, el máximo y el mínimo.

    Úsenla siempre que haya que comparar o resumir una serie, para no hacer cuentas a mano.
    "cambio" está en las unidades de la serie: si la serie ya es una tasa (inflación, PBI), son puntos porcentuales.
    "variacion_pct" es la variación porcentual entre el primer y el último valor; sirve para índices, montos y
    precios (tipo de cambio, cobre), no para tasas. Mismas fechas que serie. Ejemplo: codigo="PN01273PM",
    desde="2025-12", hasta="2026-09".
    """
    return _resumen(codigo, desde, hasta)


# TODO 3 · herramienta propia
@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True,
                       "openWorldHint": True})
def graficar_serie(codigo: str, desde: str, hasta: str, titulo: str | None = None) -> dict:
    """Grafica una serie del BCRP y guarda el PNG en la carpeta figuras/ del proyecto, listo para un informe.

    Úsenla cuando pidan un gráfico, una figura o ver la evolución de un indicador en el tiempo.
    Dibuja la serie con su promedio y marca el máximo y el mínimo; esas cifras salen de resumen, no del modelo.
    titulo es opcional (por defecto, el nombre de la serie). Mismas fechas que serie.
    Ejemplo: codigo="PN01273PM", desde="2021-01", hasta="2026-09".
    Devuelve la ruta del PNG, las cifras marcadas en el gráfico y la fuente.
    """
    s, r = _serie(codigo, desde, hasta), _resumen(codigo, desde, hasta)
    d = pd.DataFrame(s["datos"])
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    ax.plot(d.periodo, d.valor, color="#2a78d6", linewidth=1.8)
    ax.axhline(r["promedio"], color="#8a8985", linewidth=1, linestyle="--")
    ax.annotate(f"promedio {r['promedio']:.2f}", (d.periodo.iloc[0], r["promedio"]), xytext=(0, 4),
                textcoords="offset points", fontsize=8, color="#52514e",
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    for extremo, nombre, abajo in ((r["maximo"], "máx.", False), (r["minimo"], "mín.", True)):
        ax.plot(extremo["periodo"], extremo["valor"], "o", color="#2a78d6", markersize=5)
        ax.annotate(f"{nombre} {extremo['valor']} ({extremo['periodo']})", (extremo["periodo"], extremo["valor"]),
                    xytext=(0, -12 if abajo else 6), textcoords="offset points", ha="center", fontsize=8,
                    color="#0b0b0b")
    ax.set_title(titulo or s["nombre"], loc="left", fontsize=11, color="#0b0b0b")
    paso = -(-len(d) // 6)                                  # división hacia arriba: unas 6 fechas en el eje x
    ax.set_xticks(d.periodo[::paso])
    ax.margins(x=0.02, y=0.15)                              # aire arriba y abajo para las etiquetas
    ax.tick_params(colors="#52514e", labelsize=8)
    ax.grid(axis="y", color="#e5e4e0", linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    fig.text(0.01, 0.01, f"Fuente: BCRP, serie {codigo} ({d.periodo.iloc[0]} a {d.periodo.iloc[-1]}).",
             fontsize=7, color="#52514e")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    FIGURAS.mkdir(exist_ok=True)
    ruta = FIGURAS / f"bcrp_{codigo}_{d.periodo.iloc[0]}_{d.periodo.iloc[-1]}.png"
    fig.savefig(ruta)
    plt.close(fig)                                          # libera la memoria del gráfico
    return {"archivo": str(ruta), "codigo": codigo, "nombre": s["nombre"], "n_datos": r["n_datos"],
            "promedio": r["promedio"], "maximo": r["maximo"], "minimo": r["minimo"],
            "fuente": s["fuente"], "tabla_web": s["tabla_web"]}


# TODO 4 · recursos: la ficha de cualquier serie y la lista de las más usadas
@mcp.resource("bcrp://serie/{codigo}")
def ficha_serie(codigo: str) -> dict:
    """La ficha de una serie del BCRP: nombre, categoría, frecuencia, desde cuándo hay datos y su actualización."""
    return _ficha(codigo)


@mcp.resource("bcrp://series/frecuentes")
def series_frecuentes() -> list[dict]:
    """Las fichas de las series más consultadas: inflación, PBI, tasa de referencia, tipo de cambio y cobre."""
    return [_ficha(c) for c in FRECUENTES]


# TODO 5 · prompt
@mcp.prompt
def informe(tema: str, periodo: str = "los últimos cinco años con datos") -> str:
    """Plantilla para un informe breve sobre un indicador económico del Perú, con cada cifra citada."""
    return (f"Escribe un informe breve sobre {tema} en el Perú para {periodo}, con series oficiales del BCRP.\n"
            "1. Busca las series con buscar_series, elige la más adecuada y explica por qué.\n"
            "2. Calcula con resumen el cambio, el promedio y los extremos; usa serie si necesitas los datos. "
            "No hagas cuentas a mano.\n"
            "3. Haz un gráfico con graficar_serie.\n"
            "4. Cada cifra va con el código de la serie, el periodo y la fuente (tabla_web).\n"
            "Estructura: resumen en tres líneas, tabla de cifras clave, interpretación y fuentes.")


if __name__ == "__main__":
    mcp.run()
