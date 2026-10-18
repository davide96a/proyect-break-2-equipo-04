"""Tool RAG: envuelve rag.responder() del PB1 con status explícito (ok/abstencion/error)."""

from rag import responder


def rag_ask(consulta: str) -> dict:
    """Consulta los documentos oficiales del deporte municipal de Madrid
    (tarifas, descuentos, instalaciones, horarios y normas de uso).
    Si los documentos no contienen la respuesta, se abstiene.
    """
    consulta = (consulta or "").strip()
    if not consulta:
        return {"status": "error", "texto": "Error: la consulta no puede estar vacía.", "fuentes": []}

    r = responder(consulta)
    if r["error"]:
        return {"status": "error", "texto": f"Error: {r['error']}", "fuentes": []}

    abstencion = r["abstencion"]
    return {
        "status": "abstencion" if abstencion else "ok",
        "texto": r["respuesta"],
        "fuentes": [] if abstencion else r["fuentes"],
    }
