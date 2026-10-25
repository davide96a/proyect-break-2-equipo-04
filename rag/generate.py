"""Generación: llamada al LLM (Gemini). El pipeline completo está en logic.py."""

from google import genai

from .config import GENERATION_MODEL, GOOGLE_API_KEY, TEMPERATURE


def generar_respuesta(prompt: str) -> str:
    """Envía el prompt a Gemini y devuelve el texto de la respuesta."""
    client = genai.Client(api_key=GOOGLE_API_KEY)
    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt,
        config={"temperature": TEMPERATURE},
    )
    return (response.text or "").strip()
