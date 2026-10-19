"""Grafo LangGraph: supervisor → especialistas → sintetizar → [pausa HITL] → aplicar.

START → supervisor ─┬─> especialista_tarifas ───────┐
                    ├─> especialista_instalaciones ──┤ (vuelven al supervisor)
                    └─> sintetizar → (interrupt_before) → aplicar → END

Reglas (las aplica Python, nunca el LLM):
- El supervisor pregunta al LLM el siguiente paso; si la respuesta no es válida,
  decide un fallback determinista. Con MAX_ITER vueltas se va a sintetizar sí o sí.
- Cada especialista: el LLM elige QUÉ tools usar; Python construye los argumentos,
  corta en MAX_STEPS y ejecuta con ejecutar_tool(..., permitidas=sus tools).
- `done` lo pone `aplicar`, y solo si el humano aprobó.
"""

from datetime import datetime

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from config import IMAGEN_DEMO, MAX_ITER, MAX_STEPS, SALIDAS_DIR, USE_MOCKS
from src.llm import invocar
from src.state import EstadoGrafo

if USE_MOCKS:
    from src.mocks.tools_fake import ejecutar_tool
else:
    from src.tools import ejecutar_tool

ESPECIALISTAS = {
    "especialista_tarifas": {
        "rol": "tarifas, abonos, descuentos, normas y datos de los centros (documentos oficiales)",
        "tools": ["rag_ask", "hora_actual"],
    },
    "especialista_instalaciones": {
        "rol": "actividades y eventos en las instalaciones (agenda en vivo) e imágenes adjuntas",
        "tools": ["api_deporte", "hora_actual", "describir_imagen"],
    },
}

PAL_INSTALACIONES = ("actividad", "evento", "agenda", "curso", "torneo", "clase",
                     "imagen", "foto", "cartel", "infografía", "folleto")
PAL_TIEMPO = ("hoy", "ahora", "mañana", "fin de semana", "abierto", "esta semana")
PAL_IMAGEN = ("imagen", "foto", "cartel", "infografía", "folleto")


def _contiene(texto: str, palabras) -> bool:
    texto = texto.lower()
    return any(p in texto for p in palabras)


def construir_grafo(llm=None):
    """Compila el grafo. `llm` puede ser Gemini, un FakeListChatModel (tests) o None (solo fallbacks)."""

    # ------------------------------------------------------------ supervisor
    def _fallback_supervisor(consulta: str, hechos: set) -> str:
        if "especialista_tarifas" not in hechos:
            return "especialista_tarifas"  # el RAG del PB1 es el núcleo: siempre primero
        if "especialista_instalaciones" not in hechos and _contiene(consulta, PAL_INSTALACIONES):
            return "especialista_instalaciones"
        return "sintetizar"

    def supervisor(state: EstadoGrafo) -> dict:
        it = state.get("iter", 0) + 1
        hechos = set(state.get("notas", {}))
        pendientes = [e for e in ESPECIALISTAS if e not in hechos]
        opciones = pendientes + ["sintetizar"]

        if it > MAX_ITER:  # límite duro: no se pregunta al LLM
            siguiente, origen = "sintetizar", "MAX_ITER"
        else:
            roles = "\n".join(f"- {e}: {ESPECIALISTAS[e]['rol']}" for e in pendientes)
            respuesta = invocar(llm, (
                "Eres el supervisor de un asistente sobre el deporte municipal de Madrid.\n"
                f"Pregunta: {state['consulta']}\n"
                f"Especialistas que aún no han trabajado:\n{roles or '- (ninguno)'}\n"
                f"Responde SOLO con una palabra de esta lista: {', '.join(opciones)}. "
                "Usa 'sintetizar' cuando ya haya información suficiente."
            ))
            eleccion = (respuesta or "").strip().strip(".'\"` ").lower()
            if eleccion == "finish":
                eleccion = "sintetizar"
            if eleccion in opciones and not (eleccion == "sintetizar" and not hechos):
                siguiente, origen = eleccion, "llm"
            else:  # sin LLM, respuesta inventada o sintetizar sin datos → Python decide
                siguiente, origen = _fallback_supervisor(state["consulta"], hechos), "fallback"

        log = state.get("log", []) + [f"supervisor → {siguiente} ({origen}, iter {it})"]
        return {"iter": it, "siguiente": siguiente, "log": log}

    # --------------------------------------------------------- especialistas
    def _args(tool: str, consulta: str) -> dict:
        """Python construye los argumentos: el LLM solo elige nombres de tools."""
        if tool in ("rag_ask", "api_deporte"):
            return {"consulta": consulta}
        if tool == "describir_imagen":
            return {"ruta": str(IMAGEN_DEMO), "pregunta": consulta}
        return {}

    def _fallback_tools(nombre: str, consulta: str) -> list[str]:
        if nombre == "especialista_tarifas":
            tools = ["rag_ask"]
        else:
            tools = ["api_deporte"] + (["describir_imagen"] if _contiene(consulta, PAL_IMAGEN) else [])
        return tools + (["hora_actual"] if _contiene(consulta, PAL_TIEMPO) else [])

    def _especialista(nombre: str):
        def nodo(state: EstadoGrafo) -> dict:
            consulta = state["consulta"]
            respuesta = invocar(llm, (
                f"Eres el especialista en {ESPECIALISTAS[nombre]['rol']}.\n"
                f"Pregunta: {consulta}\n"
                f"Tools disponibles: {', '.join(ESPECIALISTAS[nombre]['tools'])}.\n"
                f"Responde SOLO con los nombres de las tools que usarías (máximo {MAX_STEPS}), separados por comas."
            ))
            elegidas = [t.strip().strip(".'\"` ") for t in (respuesta or "").split(",") if t.strip()]
            origen = "llm" if elegidas else "fallback"
            elegidas = elegidas or _fallback_tools(nombre, consulta)

            trazas = []
            for tool in list(dict.fromkeys(elegidas))[:MAX_STEPS]:  # sin repetidas y con límite duro
                entrada = ejecutar_tool(tool, _args(tool, consulta), permitidas=ESPECIALISTAS[nombre]["tools"])
                trazas.append({**entrada, "especialista": nombre})

            nota = "\n".join(f"[{t['tool']} · {t['status']}] {t['resultado'].get('texto', '')}" for t in trazas)
            log = state.get("log", []) + [f"{nombre} → tools {[t['tool'] for t in trazas]} ({origen})"]
            return {"notas": {**state.get("notas", {}), nombre: nota or "Sin resultados."},
                    "traza_tools": state.get("traza_tools", []) + trazas, "log": log}

        nodo.__name__ = nombre
        return nodo

    # ------------------------------------------------------------ sintetizar
    def sintetizar(state: EstadoGrafo) -> dict:
        notas = "\n\n".join(f"## {k}\n{v}" for k, v in state.get("notas", {}).items())
        historial = "\n".join(f"{m['role']}: {m['content'][:300]}" for m in state.get("messages", [])[-6:])
        texto = invocar(llm, (
            "Redacta la respuesta para el usuario sobre el deporte municipal de Madrid usando SOLO las notas.\n"
            "Si falta información o una tool falló, dilo. No inventes precios ni horarios. Cita las fuentes.\n"
            "Formato: primero la respuesta (máximo 6 líneas); después una línea 'PLAN:' y de 2 a 4 viñetas "
            "'- ' con los pasos que el usuario debería seguir.\n\n"
            f"Conversación reciente:\n{historial}\n\nNotas de los especialistas:\n{notas}"
        ))
        if texto and "PLAN:" in texto:
            respuesta, bloque = texto.split("PLAN:", 1)
            plan = [l.strip("-•* ").strip() for l in bloque.splitlines() if l.strip("-•* ").strip()]
            origen = "llm"
        else:  # fallback: las notas tal cual y un plan mínimo
            respuesta = texto or f"Esto es lo que han encontrado los especialistas:\n\n{notas}"
            plan = [f"Revisar la información de {k.replace('especialista_', '')}" for k in state.get("notas", {})]
            origen = "fallback"
        log = state.get("log", []) + [f"sintetizar → plan con {len(plan)} viñetas ({origen})", "pausa HITL antes de aplicar"]
        return {"respuesta": respuesta.strip(), "plan": plan, "log": log}

    # --------------------------------------------------------- aplicar (HITL)
    def aplicar(state: EstadoGrafo) -> dict:
        """Solo se ejecuta tras la decisión humana. Sin aprobación explícita no hay efecto."""
        if state.get("aprobado") is True:
            SALIDAS_DIR.mkdir(exist_ok=True)
            ruta = SALIDAS_DIR / f"plan_{datetime.now():%Y%m%d_%H%M%S}.md"
            vinetas = "\n".join(f"- {p}" for p in state["plan"])
            ruta.write_text(f"# {state['consulta']}\n\n{state['respuesta']}\n\n## Plan\n{vinetas}\n", encoding="utf-8")
            texto = f"✅ Plan aprobado y guardado en salidas/{ruta.name}."
            return {"done": True, "messages": [{"role": "assistant", "content": f"{state['respuesta']}\n\n{texto}"}],
                    "log": state.get("log", []) + ["aplicar → aprobado"],
                    "respuesta": f"{state['respuesta']}\n\n{texto}"}

        texto = "Plan rechazado. Dime qué quieres cambiar y lo preparo de nuevo."
        return {"done": False, "messages": [{"role": "assistant", "content": texto}],
                "log": state.get("log", []) + ["aplicar → rechazado"], "respuesta": texto}

    # ----------------------------------------------------------------- grafo
    g = StateGraph(EstadoGrafo)
    g.add_node("supervisor", supervisor)
    for nombre in ESPECIALISTAS:
        g.add_node(nombre, _especialista(nombre))
        g.add_edge(nombre, "supervisor")
    g.add_node("sintetizar", sintetizar)
    g.add_node("aplicar", aplicar)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", lambda s: s["siguiente"],
                            {**{n: n for n in ESPECIALISTAS}, "sintetizar": "sintetizar"})
    g.add_edge("sintetizar", "aplicar")
    g.add_edge("aplicar", END)
    return g.compile(checkpointer=MemorySaver(), interrupt_before=["aplicar"])
