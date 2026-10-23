"""Tests de la app Streamlit: HITL desde la barra lateral (Aprobar / Rechazar).

Sin red, sin índice y sin Gemini: tools falsas (src/mocks) y grafo sin LLM (fallback en Python).
Usa AppTest de Streamlit, que ejecuta app.py sin abrir el navegador.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import src.agent as agent
import src.graph as graph_mod
from src.mocks import tools_fake

APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.fixture(autouse=True)
def entorno(monkeypatch, tmp_path):
    monkeypatch.setattr(graph_mod, "ejecutar_tool", tools_fake.ejecutar_tool)   # tools falsas
    monkeypatch.setattr(graph_mod, "SALIDAS_DIR", tmp_path)                       # no ensuciar salidas/
    monkeypatch.setattr(agent, "_grafo", graph_mod.construir_grafo(None))         # sin LLM: fallback


def _botones(at: AppTest) -> list[str]:
    return [b.label for b in at.sidebar.button]


def _preguntar(at: AppTest, texto: str) -> AppTest:
    at.chat_input[0].set_value(texto).run()
    assert not at.exception
    return at


def test_aprobar_desde_la_barra_lateral():
    at = _preguntar(AppTest.from_file(APP).run(), "¿Cuánto cuesta la piscina de verano para adultos?")
    assert at.session_state["resultado"]["pendiente_hitl"]
    assert {"Aprobar", "Rechazar"} <= set(_botones(at))

    at.sidebar.button[0].click().run()  # Aprobar

    assert at.session_state["resultado"]["done"]
    assert "Aprobar" not in _botones(at)  # sin plan pendiente no hay botones HITL
    assert "Plan aprobado" in at.session_state["messages"][-1]["content"]


def test_rechazar_y_seguir_en_el_mismo_thread():
    at = _preguntar(AppTest.from_file(APP).run(), "¿Cuánto cuesta la piscina de verano para adultos?")
    thread_id = at.session_state["thread_id"]

    at.sidebar.button[1].click().run()  # Rechazar

    assert not at.session_state["resultado"]["done"]
    assert "Plan rechazado" in at.session_state["messages"][-1]["content"]
    _preguntar(at, "¿Y para jubilados?")
    assert at.session_state["thread_id"] == thread_id
    assert at.session_state["resultado"]["pendiente_hitl"]
