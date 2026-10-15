"""Prompt RAG: instrucciones + contexto recuperado + pregunta, con abstención si no hay evidencia."""

from pathlib import Path

from .config import MAX_CHUNKS

FRASE_ABSTENCION = "No tengo información suficiente en los documentos para responder a esa pregunta."

INSTRUCCIONES_RAG = f"""Eres un asistente sobre instalaciones, tarifas y normas del deporte municipal de Madrid.

Reglas:
- Responde ÚNICAMENTE con la información del contexto proporcionado.
- Si el contexto no contiene información suficiente para responder, responde exactamente: "{FRASE_ABSTENCION}" y no añadas nada más.
- Si la pregunta no tiene relación con el deporte municipal de Madrid, aplica también la regla anterior.
- No inventes precios, horarios, requisitos ni ningún dato que no aparezca en el contexto.
- Cuando cites un dato, menciona el fichero fuente indicado en el fragmento.
- Responde en español, de forma breve y clara.
"""


def formatear_contexto(chunks: list[dict]) -> str:
    """Convierte los chunks de retrieve() en bloques de texto numerados, con su fuente."""
    partes = []
    for i, chunk in enumerate(chunks[:MAX_CHUNKS], 1):
        fuente = Path(chunk["source"]).name if chunk.get("source") else "desconocida"
        partes.append(f"--- Fragmento {i} ---\nFuente: {fuente}\n{chunk['text'].strip()}")
    return "\n\n".join(partes)


def construir_prompt(contexto: str, pregunta: str) -> str:
    """Monta el prompt final con secciones delimitadas."""
    return (
        f"{INSTRUCCIONES_RAG}\n"
        f"--- CONTEXTO RECUPERADO ---\n{contexto.strip()}\n\n"
        f"--- PREGUNTA ---\n{pregunta.strip()}\n\n"
        f"--- RESPUESTA ---"
    )


def es_abstencion(respuesta: str) -> bool:
    """True si la respuesta del modelo es la frase de abstención."""
    return FRASE_ABSTENCION.lower() in respuesta.lower()
