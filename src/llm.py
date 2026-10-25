"""Acceso al LLM del grafo (Gemini vía LangChain).

Usar un chat model de LangChain permite cambiarlo por FakeListChatModel en los tests.
Nunca lanza: si no hay clave, no hay red o el modelo falla, devuelve None y el MOTIVO,
y quien lo llama usa su fallback determinista en Python y lo deja en el log.
"""

from config import GOOGLE_API_KEY, LLM_MODEL, TEMPERATURE


def get_llm():
    """Devuelve el modelo de Gemini, o None si no hay GOOGLE_API_KEY."""
    if not GOOGLE_API_KEY:
        return None
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=TEMPERATURE, google_api_key=GOOGLE_API_KEY)


def invocar_detalle(llm, prompt: str) -> tuple[str | None, str | None]:
    """(texto, motivo). Si hay texto, motivo es None; si no, motivo explica por qué."""
    if llm is None:
        return None, "sin LLM"
    try:
        contenido = llm.invoke(prompt).content
    except Exception as e:  # noqa: BLE001 — 503, cuota, red... → fallback
        return None, f"error LLM: {type(e).__name__}: {str(e)[:60]}"
    if isinstance(contenido, list):  # algunos modelos devuelven bloques
        contenido = " ".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in contenido)
    contenido = (contenido or "").strip()
    return (contenido, None) if contenido else (None, "respuesta vacía del LLM")


def invocar(llm, prompt: str) -> str | None:
    """Solo el texto (None si no hay)."""
    return invocar_detalle(llm, prompt)[0]
