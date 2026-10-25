"""Tests del grafo y del agente: HITL, memoria, fallback, límites y allowlist.

Sin red, sin índice y sin Gemini: tools falsas (src/mocks) y LLM falso (FakeListChatModel).
Ejecutar desde la raíz:  python -m pytest -q
"""

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

import src.agent as agent
import src.graph as graph_mod
from config import MAX_STEPS
from src.mocks import tools_fake

CLAVES_CONTRATO = {"respuesta", "plan", "pendiente_hitl", "done", "log", "traza_tools", "thread_id", "error"}

# Orden de llamadas al LLM en un turno normal: supervisor → especialista → supervisor → sintetizar
RESPUESTAS_OK = [
    "especialista_tarifas",
    "rag_ask",
    "sintetizar",
    "La entrada de adulto cuesta 4,50 € (300083-10-deportes-tarifas.xlsx).\nPLAN:\n- Ir a la piscina\n- Pagar en taquilla",
]


class LLMRoto:
    """LLM que siempre falla: obliga a usar todos los fallbacks."""

    def invoke(self, prompt):
        raise RuntimeError("Gemini caído (simulado)")


@pytest.fixture(autouse=True)
def entorno(monkeypatch, tmp_path):
    monkeypatch.setattr(graph_mod, "ejecutar_tool", tools_fake.ejecutar_tool)  # tools falsas
    monkeypatch.setattr(graph_mod, "SALIDAS_DIR", tmp_path)                      # no ensuciar salidas/


def _usar_llm(monkeypatch, llm):
    monkeypatch.setattr(agent, "_grafo", graph_mod.construir_grafo(llm))


# ------------------------------------------------------------------ HITL
def test_pausa_antes_de_aplicar_y_aprobar(monkeypatch, tmp_path):
    _usar_llm(monkeypatch, FakeListChatModel(responses=RESPUESTAS_OK))
    tid = agent.nuevo_thread_id()

    r = agent.procesar_turno("¿Cuánto cuesta la piscina de verano para adultos?", tid)
    assert set(r) == CLAVES_CONTRATO
    assert r["pendiente_hitl"] and not r["done"] and r["error"] is None
    assert r["plan"] == ["Ir a la piscina", "Pagar en taquilla"]
    assert any("(llm" in linea for linea in r["log"])

    r = agent.aprobar_plan(tid, True)
    assert r["done"] and not r["pendiente_hitl"]
    assert len(list(tmp_path.glob("plan_*.md"))) == 1  # el efecto solo ocurre tras aprobar


def test_rechazar_no_aplica_y_se_puede_seguir_en_el_mismo_thread(monkeypatch, tmp_path):
    _usar_llm(monkeypatch, FakeListChatModel(responses=RESPUESTAS_OK))
    tid = agent.nuevo_thread_id()

    agent.procesar_turno("¿Cuánto cuesta la piscina de verano?", tid)
    r = agent.aprobar_plan(tid, False)
    assert not r["done"] and not r["pendiente_hitl"]
    assert list(tmp_path.glob("plan_*.md")) == []

    r = agent.procesar_turno("¿y para jubilados?", tid)  # mismo thread_id: memoria
    assert r["pendiente_hitl"]
    estado = agent._grafo.get_state({"configurable": {"thread_id": tid}}).values
    assert estado["turnos"] == 2
    assert "piscina de verano" in estado["consulta"]  # la pregunta corta se completó con el historial


def test_no_acepta_mensaje_con_plan_pendiente(monkeypatch):
    _usar_llm(monkeypatch, FakeListChatModel(responses=RESPUESTAS_OK))
    tid = agent.nuevo_thread_id()
    agent.procesar_turno("precio piscina", tid)
    assert "pendiente" in agent.procesar_turno("otra pregunta", tid)["error"]


def test_aprobar_sin_plan_pendiente_da_error(monkeypatch):
    _usar_llm(monkeypatch, None)
    assert agent.aprobar_plan(agent.nuevo_thread_id(), True)["error"]


# --------------------------------------------------- fallback y límites
def test_fallback_si_el_llm_falla_y_el_log_dice_por_que(monkeypatch):
    _usar_llm(monkeypatch, LLMRoto())
    r = agent.procesar_turno("¿Qué actividades hay hoy en el polideportivo?", agent.nuevo_thread_id())
    assert r["pendiente_hitl"] and r["error"] is None
    assert "fallback: error LLM: RuntimeError" in r["log"][0]
    # pregunta de actividades → instalaciones, sin pasar por tarifas
    assert r["log"][0].startswith("supervisor → especialista_instalaciones")
    assert {t["tool"] for t in r["traza_tools"]} == {"api_deporte", "hora_actual"}


def test_fallback_pregunta_mixta_consulta_los_dos_especialistas(monkeypatch):
    _usar_llm(monkeypatch, LLMRoto())
    r = agent.procesar_turno("¿Cuánto cuesta el abono y qué actividades hay?", agent.nuevo_thread_id())
    assert {t["especialista"] for t in r["traza_tools"]} == {"especialista_tarifas", "especialista_instalaciones"}


def test_ninguna_no_se_ejecuta_como_tool(monkeypatch):
    llm = FakeListChatModel(responses=["especialista_tarifas", "Ninguna", "sintetizar", "Resumen\nPLAN:\n- a"])
    _usar_llm(monkeypatch, llm)
    r = agent.procesar_turno("precio piscina", agent.nuevo_thread_id())
    assert [t["tool"] for t in r["traza_tools"]] == ["rag_ask"]  # usa el fallback, no "ninguna"
    assert any("el LLM no eligió ninguna tool" in linea for linea in r["log"])


def test_si_todas_las_tools_fallan_no_hay_plan_ni_hitl(monkeypatch):
    def rota(consulta):
        raise RuntimeError("503 simulado")
    monkeypatch.setitem(tools_fake.TOOLS_PERMITIDAS, "rag_ask", rota)
    _usar_llm(monkeypatch, FakeListChatModel(responses=RESPUESTAS_OK))
    r = agent.procesar_turno("precio piscina", agent.nuevo_thread_id())
    assert not r["pendiente_hitl"] and not r["done"] and r["plan"] == []
    assert "no puedo consultar" in r["respuesta"] and "503" not in r["respuesta"]


def test_abstencion_responde_sin_plan(monkeypatch):
    _usar_llm(monkeypatch, None)
    r = agent.procesar_turno("¿Cuál es la capital de Francia?", agent.nuevo_thread_id())
    assert not r["pendiente_hitl"] and "No tengo información suficiente" in r["respuesta"]


def test_el_plan_no_lleva_la_fuente(monkeypatch):
    llm = FakeListChatModel(responses=["especialista_tarifas", "rag_ask", "sintetizar",
                                       "Cuesta 4,50 €.\nPLAN:\n- Ir a la piscina\n- Fuente: especialista_tarifas"])
    _usar_llm(monkeypatch, llm)
    r = agent.procesar_turno("precio piscina", agent.nuevo_thread_id())
    assert r["plan"] == ["Ir a la piscina"]


def test_respuesta_inventada_del_supervisor_usa_fallback(monkeypatch):
    _usar_llm(monkeypatch, FakeListChatModel(responses=["especialista_hacker"]))
    r = agent.procesar_turno("precio piscina", agent.nuevo_thread_id())
    assert "supervisor → especialista_tarifas (fallback" in r["log"][0]


def test_max_iter_lo_decide_python(monkeypatch):
    monkeypatch.setattr(graph_mod, "MAX_ITER", 0)
    _usar_llm(monkeypatch, FakeListChatModel(responses=RESPUESTAS_OK))
    r = agent.procesar_turno("precio piscina", agent.nuevo_thread_id())
    assert "supervisor → sintetizar (MAX_ITER" in r["log"][0]
    assert r["traza_tools"] == []


def test_max_steps_por_especialista(monkeypatch):
    llm = FakeListChatModel(responses=["especialista_instalaciones",
                                       "api_deporte, hora_actual, describir_imagen, api_deporte, rag_ask",
                                       "sintetizar", "Resumen\nPLAN:\n- a"])
    _usar_llm(monkeypatch, llm)
    r = agent.procesar_turno("actividades hoy", agent.nuevo_thread_id())
    assert len(r["traza_tools"]) == MAX_STEPS


def test_allowlist_bloquea_tools_ajenas_o_inventadas(monkeypatch):
    llm = FakeListChatModel(responses=["especialista_tarifas", "api_deporte, borrar_todo",
                                       "sintetizar", "Resumen\nPLAN:\n- a"])
    _usar_llm(monkeypatch, llm)
    r = agent.procesar_turno("precio piscina", agent.nuevo_thread_id())
    assert [t["status"] for t in r["traza_tools"]] == ["blocked", "blocked"]


def test_nueva_conversacion_empieza_sin_memoria(monkeypatch):
    _usar_llm(monkeypatch, FakeListChatModel(responses=RESPUESTAS_OK))
    agent.procesar_turno("precio piscina", "thread-a")
    assert agent._grafo.get_state({"configurable": {"thread_id": "thread-b"}}).values == {}
