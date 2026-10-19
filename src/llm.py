"""Acceso al LLM del grafo (Gemini vía LangChain).

Usar un chat model de LangChain permite cambiarlo por FakeListChatModel en los tests.
`invocar()` nunca lanza: si no hay clave, no hay red o el modelo falla, devuelve None
y quien lo llama usa su fallback determinista en Python.
"""

from config import GOOGLE_API_KEY, LLM_MODEL, TEMPERATURE


def get_llm():
    """Devuelve el modelo de Gemini, o None si no hay GOOGLE_API_KEY."""
    if not GOOGLE_API_KEY:
        return None
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=TEMPERATURE, google_api_key=GOOGLE_API_KEY)


def invocar(llm, prompt: str) -> str | None:
    """Texto de la respuesta del LLM, o None si no hay LLM o algo falla."""
    if llm is None:
        return None
    try:
        contenido = llm.invoke(prompt).content
    except Exception:  # noqa: BLE001 — cualquier fallo del LLM activa el fallback
        return None
    if isinstance(contenido, list):  # algunos modelos devuelven bloques
        contenido = " ".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in contenido)
    return (contenido or "").strip() or None
