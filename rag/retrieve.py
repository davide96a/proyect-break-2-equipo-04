"""Retrieval: dada una pregunta, recupera los top-k chunks más relevantes."""

import time

from .config import EMBEDDING_MODEL, TOP_K
from .embed import embeddear_consulta
from .index import obtener_coleccion
from .logging_utils import log_query


def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """Devuelve los top-k chunks (texto + source + score) más relevantes para la query."""
    inicio = time.time()

    vector = embeddear_consulta(query)
    coleccion = obtener_coleccion()

    resultados = coleccion.query(
        query_embeddings=[vector],
        n_results=k,
    )

    chunks = []
    for texto, metadata, distancia in zip(
        resultados["documents"][0],
        resultados["metadatas"][0],
        resultados["distances"][0],
    ):
        chunks.append({
            "text": texto,
            "source": metadata.get("source"),
            "metadata": metadata,
            "score": 1 - distancia,  # distancia coseno -> similitud
        })

    tiempo = time.time() - inicio
    log_query(query, k, len(chunks), tiempo, EMBEDDING_MODEL)

    return chunks