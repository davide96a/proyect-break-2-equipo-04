"""Pipeline online completo (retrieval + prompt + generación), independiente de la UI."""

import time
from pathlib import Path

from .config import GENERATION_MODEL, MAX_CHUNKS, TOP_K
from .generate import generar_respuesta
from .logging_utils import log_generacion
from .prompts import construir_prompt, es_abstencion, formatear_contexto
from .retrieve import retrieve


def _extraer_fuentes(chunks: list[dict]) -> list[str]:
    fuentes: list[str] = []
    vistos: set[str] = set()
    for chunk in chunks:
        source = chunk.get("metadata", {}).get("source", "?")
        nombre = Path(str(source)).name
        if nombre not in vistos:
            vistos.add(nombre)
            fuentes.append(nombre)
    return fuentes


def responder(pregunta: str, k: int | None = None) -> dict:
    """Pipeline: retrieve → prompt → generate.

    No lanza excepciones: si algo falla, el mensaje queda en la clave 'error'.
    """
    inicio = time.perf_counter()
    pregunta = (pregunta or "").strip()
    k = min(k or TOP_K, MAX_CHUNKS)
    respuesta, contexto, chunks, error = "", "", [], None

    if not pregunta:
        error = "La pregunta no puede estar vacía."
    else:
        try:
            chunks = retrieve(pregunta, k=k)
            contexto = formatear_contexto(chunks)
            prompt = construir_prompt(contexto, pregunta)
            respuesta = generar_respuesta(prompt)
        except Exception as e:
            error = f"Error al procesar la pregunta: {e}"

    resultado = {
        "respuesta": respuesta,
        "abstencion": es_abstencion(respuesta),
        "contexto": contexto,
        "chunks": chunks,
        "fuentes": _extraer_fuentes(chunks),
        "k": k,
        "n_chunks": len(chunks),
        "tiempo_segundos": round(time.perf_counter() - inicio, 3),
        "modelo": GENERATION_MODEL,
        "error": error,
    }
    log_generacion(pregunta, resultado)
    return resultado


def rag_ask(consulta: str) -> str:
    """Versión simple de responder() que devuelve solo texto (para reutilizar como tool de un agente)."""
    resultado = responder(consulta)
    return resultado["error"] or resultado["respuesta"]
