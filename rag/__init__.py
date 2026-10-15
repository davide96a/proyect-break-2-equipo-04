"""RAG del PB1 (Deporte municipal) empaquetado para el agente."""


def responder(pregunta: str, k: int | None = None) -> dict:
    """Import diferido: el modelo de embeddings y Chroma solo se cargan al usarlo."""
    from .logic import responder as _responder

    return _responder(pregunta, k=k)
