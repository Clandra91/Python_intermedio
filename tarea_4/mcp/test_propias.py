"""Las 2 pruebas propias, para la herramienta graficar_serie. Van aparte para no tocar test_server.py.

    uv run pytest -q          # desde tarea_4: corre las 8 del curso y estas 2 (10 passed)

Usan la misma función llamar() de test_server.py, que llama al servidor como lo haría Claude Code.
"""
import server
from test_server import llamar

PNG = b"\x89PNG"  # los primeros bytes de todo archivo PNG


def test_graficar_serie_guarda_un_png(tmp_path, monkeypatch):
    # tmp_path es una carpeta temporal de pytest: así la prueba no llena figuras/ con gráficos de prueba
    monkeypatch.setattr(server, "FIGURAS", tmp_path)
    r = llamar("graficar_serie", codigo="PN01273PM", desde="2025-12", hasta="2026-09")
    archivo = tmp_path / "bcrp_PN01273PM_2025-12_2026-09.png"
    assert r["archivo"] == str(archivo)
    assert archivo.read_bytes()[:4] == PNG
    assert r["fuente"].startswith("https://estadisticas.bcrp.gob.pe")


def test_graficar_serie_usa_las_cifras_de_resumen(tmp_path, monkeypatch):
    # lo que marca el gráfico debe coincidir con resumen: las cifras salen de Python, no del modelo
    monkeypatch.setattr(server, "FIGURAS", tmp_path)
    g = llamar("graficar_serie", codigo="PD04638PD", desde="2026-10-01", hasta="2026-10-15")
    r = llamar("resumen", codigo="PD04638PD", desde="2026-10-01", hasta="2026-10-15")
    assert g["n_datos"] == r["n_datos"] == len(llamar("serie", codigo="PD04638PD", desde="2026-10-01",
                                                      hasta="2026-10-15")["datos"])
    assert g["maximo"] == r["maximo"]
    assert g["minimo"] == r["minimo"]
    assert g["promedio"] == r["promedio"]
