"""Interfaz Streamlit: solo cliente de src/agent.py.

  streamlit run app.py
"""

import streamlit as st

from src.agent import nuevo_thread_id, procesar_turno

st.set_page_config(page_title="Agente · Deporte municipal", page_icon="🏊", layout="centered")

SALUDO = (
    "Hola. Soy un **agente multiagente** del deporte municipal de Madrid: "
    "tarifas, abonos, normas, instalaciones y actividades. "
    "Cuando prepare un plan, podrás aprobarlo o rechazarlo antes de cerrarlo."
)


def _reset() -> None:
    """Conversación nueva: saludo, thread_id nuevo y sin resultado previo."""
    st.session_state.messages = [{"role": "assistant", "content": SALUDO}]
    st.session_state.thread_id = nuevo_thread_id()
    st.session_state.resultado = {}


def _texto_respuesta(resultado: dict) -> str:
    """Respuesta del agente + plan en viñetas (si lo hay)."""
    texto = resultado.get("respuesta") or "(Sin respuesta)"
    plan = resultado.get("plan") or []
    if plan:
        etiqueta = "Plan (pendiente de aprobación)" if resultado.get("pendiente_hitl") else "Plan"
        texto += f"\n\n**{etiqueta}:**\n" + "\n".join(f"- {p}" for p in plan)
    return texto


if "messages" not in st.session_state:
    _reset()

with st.sidebar:
    st.caption(f"thread_id: `{st.session_state.thread_id}`")

st.title("Asistente de Deporte Municipal")
st.caption("Supervisor + especialistas + tools (RAG, API, hora, imagen) · MemorySaver · HITL")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Tu pregunta sobre deporte municipal..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando a los especialistas..."):
            resultado = procesar_turno(prompt, st.session_state.thread_id)
        st.session_state.resultado = resultado
        texto = _texto_respuesta(resultado)
        st.markdown(texto)
    st.session_state.messages.append({"role": "assistant", "content": texto})
