"""Interfaz Streamlit: solo cliente de src/agent.py.

  streamlit run app.py
"""

import streamlit as st

from src.agent import aprobar_plan, nuevo_thread_id, procesar_turno

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


def _decidir(aprobado: bool) -> None:
    """HITL: el humano aprueba o rechaza el plan; la respuesta del agente va al chat."""
    st.session_state.resultado = aprobar_plan(st.session_state.thread_id, aprobado)
    texto = st.session_state.resultado.get("respuesta") or ("Plan aprobado." if aprobado else "Plan rechazado.")
    st.session_state.messages.append({"role": "assistant", "content": texto})


if "messages" not in st.session_state:
    _reset()

with st.sidebar:
    st.caption(f"thread_id: `{st.session_state.thread_id}`")

    resultado = st.session_state.resultado
    if resultado.get("pendiente_hitl"):
        st.divider()
        st.subheader("HITL — aprobar plan")
        for item in resultado.get("plan") or []:
            st.markdown(f"- {item}")
        c1, c2 = st.columns(2)
        if c1.button("Aprobar", use_container_width=True, type="primary"):
            _decidir(True)
            st.rerun()
        if c2.button("Rechazar", use_container_width=True):
            _decidir(False)
            st.rerun()

    st.divider()
    if st.button("Nueva conversación", use_container_width=True):
        _reset()
        st.rerun()

st.title("Asistente de Deporte Municipal")
st.caption("Supervisor + especialistas + tools (RAG, API, hora, imagen) · MemorySaver · HITL")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Con un plan pendiente el agente no acepta mensajes nuevos: se bloquea el chat
hitl_bloquea = bool(st.session_state.resultado.get("pendiente_hitl"))
if hitl_bloquea:
    st.warning("Plan pendiente de aprobación — usa los botones de la barra lateral.")

if prompt := st.chat_input("Tu pregunta sobre deporte municipal...", disabled=hitl_bloquea):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando a los especialistas..."):
            resultado = procesar_turno(prompt, st.session_state.thread_id)
        st.session_state.resultado = resultado
        if resultado.get("error"):  # p. ej. límite de turnos: la respuesta guardada sería la del turno anterior
            st.error(resultado["error"])
            texto = f"⚠️ {resultado['error']}"
        else:
            texto = _texto_respuesta(resultado)
            st.markdown(texto)
    st.session_state.messages.append({"role": "assistant", "content": texto})

    # La barra lateral ya se dibujó arriba: rerun para que aparezcan Aprobar / Rechazar
    if resultado.get("pendiente_hitl"):
        st.rerun()
