"""Estado compartido del grafo (TypedDict).

- `messages` se ACUMULA entre turnos (reducer operator.add): es la memoria del thread_id.
- El resto se reinicia en cada turno desde agent.procesar_turno().
"""

import operator
from typing import Annotated, TypedDict


class EstadoGrafo(TypedDict, total=False):
    messages: Annotated[list[dict], operator.add]  # [{"role": "user"|"assistant", "content": str}]
    consulta: str            # pregunta del turno (completada con el historial si hace falta)
    turnos: int              # turnos de usuario en este thread_id (≤ MAX_TURNS)
    iter: int                # vueltas del supervisor en este turno (≤ MAX_ITER)
    siguiente: str           # nodo que eligió el supervisor
    notas: dict[str, str]    # resultado de cada especialista
    log: list[str]           # "supervisor → especialista_tarifas (llm)", ...
    traza_tools: list[dict]  # entradas de ejecutar_tool
    respuesta: str           # propuesta redactada por sintetizar
    plan: list[str]          # viñetas que el humano aprueba o rechaza
    sin_datos: bool          # ninguna tool devolvió datos → respuesta directa, sin HITL
    aprobado: bool | None    # decisión humana (la escribe aprobar_plan)
    done: bool               # True solo si el plan se aprobó y se aplicó (lo decide Python)
