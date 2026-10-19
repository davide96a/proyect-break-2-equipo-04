"""API del agente para la CLI y Streamlit (firmas de CONTRATOS.md).

    nuevo_thread_id()                     → id de conversación nuevo
    procesar_turno(mensaje, thread_id)    → corre el grafo hasta la pausa HITL
    aprobar_plan(thread_id, aprobado)     → update_state + invoke(None)
    run_demo(auto_aprobar=False)          → guion de demo: rechazo + aprobación

La UI no ve el grafo: siempre recibe el mismo dict (ver _resultado).
"""

import uuid

from config import MAX_TURNS
from src.graph import construir_grafo
from src.llm import get_llm

_grafo = None  # un único grafo (y su MemorySaver) para todo el proceso


def _get_grafo():
    global _grafo
    if _grafo is None:
        _grafo = construir_grafo(get_llm())
    return _grafo


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _resultado(thread_id: str, error: str | None = None) -> dict:
    """Formato común de CONTRATOS.md, leído del estado guardado del thread."""
    snapshot = _get_grafo().get_state(_config(thread_id))
    v = snapshot.values
    return {
        "respuesta": v.get("respuesta", ""),
        "plan": v.get("plan", []),
        "pendiente_hitl": snapshot.next == ("aplicar",),
        "done": v.get("done", False),
        "log": v.get("log", []),
        "traza_tools": v.get("traza_tools", []),
        "thread_id": thread_id,
        "error": error,
    }


def nuevo_thread_id() -> str:
    return uuid.uuid4().hex[:8]


def _consulta_con_historial(mensaje: str, mensajes: list[dict]) -> str:
    """Memoria del thread: '¿y para jubilados?' necesita la pregunta anterior para el RAG."""
    previas = [m["content"] for m in mensajes if m["role"] == "user"]
    if previas and len(mensaje.split()) <= 6:
        return f"{previas[-1]} {mensaje}"
    return mensaje


def procesar_turno(mensaje: str, thread_id: str) -> dict:
    mensaje = (mensaje or "").strip()
    grafo = _get_grafo()
    snapshot = grafo.get_state(_config(thread_id))
    turnos = snapshot.values.get("turnos", 0)

    if not mensaje:
        return _resultado(thread_id, "El mensaje está vacío.")
    if snapshot.next == ("aplicar",):
        return _resultado(thread_id, "Hay un plan pendiente: apruébalo o recházalo antes de seguir.")
    if turnos >= MAX_TURNS:
        return _resultado(thread_id, f"Límite de {MAX_TURNS} turnos alcanzado. Empieza una conversación nueva.")

    entrada = {  # todo lo que es "por turno" se reinicia aquí
        "messages": [{"role": "user", "content": mensaje}],
        "consulta": _consulta_con_historial(mensaje, snapshot.values.get("messages", [])),
        "turnos": turnos + 1, "iter": 0, "siguiente": "", "notas": {}, "log": [],
        "traza_tools": [], "respuesta": "", "plan": [], "aprobado": None, "done": False,
    }
    try:
        grafo.invoke(entrada, _config(thread_id))  # se detiene antes de "aplicar"
    except Exception as e:  # noqa: BLE001 — la UI nunca recibe una excepción
        return _resultado(thread_id, f"Error en el grafo: {e}")
    return _resultado(thread_id)


def aprobar_plan(thread_id: str, aprobado: bool) -> dict:
    grafo = _get_grafo()
    if grafo.get_state(_config(thread_id)).next != ("aplicar",):
        return _resultado(thread_id, "No hay ningún plan pendiente de aprobación.")
    try:
        grafo.update_state(_config(thread_id), {"aprobado": bool(aprobado)})
        grafo.invoke(None, _config(thread_id))  # reanuda: ejecuta "aplicar" y termina
    except Exception as e:  # noqa: BLE001
        return _resultado(thread_id, f"Error al aplicar el plan: {e}")
    return _resultado(thread_id)


def run_demo(auto_aprobar: bool = False) -> list[tuple[str, dict]]:
    """Guion de demo en un mismo thread: un rechazo y una aprobación (o dos aprobaciones)."""
    thread_id = nuevo_thread_id()
    pasos = [
        ("¿Cuánto cuesta la entrada a la piscina de verano para adultos?", auto_aprobar),
        ("¿Y qué actividades hay esta semana?", True),
    ]
    salida = []
    for mensaje, aprobar in pasos:
        salida.append((mensaje, procesar_turno(mensaje, thread_id)))
        salida.append(("aprobar" if aprobar else "rechazar", aprobar_plan(thread_id, aprobar)))
    return salida
