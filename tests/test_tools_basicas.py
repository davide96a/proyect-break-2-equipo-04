import importlib
modulo_rag = importlib.import_module("src.tools.rag_ask")
from src.tools.hora_actual import hora_actual
from src.tools.rag_ask import rag_ask


def _falso(**cambios):
    base = {"respuesta": "", "abstencion": False, "fuentes": [], "error": None}
    base.update(cambios)
    return lambda pregunta: base


def test_hora_actual_devuelve_ok_y_hora_de_madrid():
    r = hora_actual()
    assert r["status"] == "ok"
    assert "Madrid" in r["texto"]
    assert r["iso"].endswith(("+01:00", "+02:00"))


def test_rag_ask_respuesta_con_fuentes(monkeypatch):
    monkeypatch.setattr(
        modulo_rag, "responder", _falso(respuesta="4,5 €", fuentes=["tarifas.xlsx"])
    )
    r = rag_ask("¿precio?")
    assert r["status"] == "ok"
    assert r["fuentes"] == ["tarifas.xlsx"]


def test_rag_ask_abstencion_sin_fuentes(monkeypatch):
    monkeypatch.setattr(
        modulo_rag,
        "responder",
        _falso(respuesta="No tengo información suficiente", abstencion=True, fuentes=["x.pdf"]),
    )
    r = rag_ask("¿capital de Francia?")
    assert r["status"] == "abstencion"
    assert r["fuentes"] == []


def test_rag_ask_error_del_rag(monkeypatch):
    monkeypatch.setattr(modulo_rag, "responder", _falso(error="sin cuota"))
    r = rag_ask("¿precio?")
    assert r["status"] == "error"
    assert "sin cuota" in r["texto"]


def test_rag_ask_consulta_vacia():
    assert rag_ask("   ")["status"] == "error"
