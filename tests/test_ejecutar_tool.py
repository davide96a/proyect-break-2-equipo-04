from src import tools
from src.tools import ejecutar_tool


def test_tool_permitida_se_ejecuta():
    r = ejecutar_tool("hora_actual")
    assert r["tool"] == "hora_actual"
    assert r["status"] == "ok"
    assert "Madrid" in r["preview"]


def test_nombre_inventado_se_bloquea():
    r = ejecutar_tool("borrar_todo")
    assert r["status"] == "blocked"
    assert "no está permitida" in r["preview"]


def test_tool_fuera_de_la_lista_del_especialista_se_bloquea():
    r = ejecutar_tool("hora_actual", {}, permitidas=["rag_ask"])
    assert r["status"] == "blocked"


def test_tool_con_excepcion_devuelve_error_sin_lanzar(monkeypatch):
    def rota():
        raise RuntimeError("fallo simulado")

    monkeypatch.setitem(tools.TOOLS_PERMITIDAS, "rota", rota)
    r = ejecutar_tool("rota")
    assert r["status"] == "error"
    assert "fallo simulado" in r["preview"]


def test_argumentos_inesperados_no_rompen():
    r = ejecutar_tool("hora_actual", {"cosa": 1})
    assert r["status"] == "error"


def test_preview_se_recorta(monkeypatch):
    monkeypatch.setitem(
        tools.TOOLS_PERMITIDAS, "larga", lambda: {"status": "ok", "texto": "x" * 500}
    )
    r = ejecutar_tool("larga")
    assert len(r["preview"]) <= 200
