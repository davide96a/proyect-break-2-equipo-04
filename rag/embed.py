"""Generación de embeddings LOCALES con sentence-transformers (Hugging Face).

Alternativa a la API de Gemini para el pipeline offline: corre en tu propia
máquina, sin llamadas a red ni límites de cuota (RPM/TPM/RPD). Se adoptó
tras topar con el límite de 1000 peticiones/día del free tier de Gemini
Embedding con un corpus de ~1700 chunks.

Guarda los mismos artefactos que consumirá index/retrieval:
  output/chunks.json      -> chunks con texto + metadata (sin vector)
  output/embeddings.json  -> texto + vector + metadata (lo que se indexa)

IMPORTANTE: si ya tenías un embeddings.json generado antes con Gemini
(vectores de 3072 dimensiones), BÓRRALO antes de ejecutar esto. Mezclar
vectores de distinta dimensión/modelo en el mismo índice rompe el retrieval.

Requiere: pip install sentence-transformers  (instala también torch)
La primera vez que se ejecuta, descarga el modelo (~470 MB) una sola vez;
las siguientes ejecuciones lo reutilizan desde caché local.
"""

import json
from pathlib import Path

from langchain_core.documents import Document
from sentence_transformers import SentenceTransformer

from .config import CHUNKS_JSON, EMBED_BATCH_SIZE, EMBEDDING_MODEL, EMBEDDINGS_JSON

_modelo_cache: SentenceTransformer | None = None


def _cargar_modelo() -> SentenceTransformer:
    """Carga el modelo una sola vez por proceso (evita recargarlo en cada llamada)."""
    global _modelo_cache
    if _modelo_cache is None:
        print(f"Cargando modelo local '{EMBEDDING_MODEL}' (la primera vez descarga ~470 MB)...")
        _modelo_cache = SentenceTransformer(EMBEDDING_MODEL)
    return _modelo_cache


def documentos_a_dicts(documentos: list[Document]) -> list[dict]:
    """Convierte Document de LangChain a dict serializable en JSON."""
    return [
        {"text": doc.page_content, "metadata": dict(doc.metadata)}
        for doc in documentos
    ]


def guardar_chunks_json(chunks: list[Document], ruta: str | Path) -> Path:
    """Escribe chunks.json (texto + metadata, sin vector) para depuración."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "total_chunks": len(chunks),
        "chunks": documentos_a_dicts(chunks),
    }
    ruta.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


def embeddear_textos(textos: list[str]) -> list[list[float]]:
    """Embeddea una lista de textos en local. Sin límites de cuota ni red."""
    if not textos:
        return []
    modelo = _cargar_modelo()
    vectores = modelo.encode(
        textos,
        batch_size=EMBED_BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,  # facilita similitud por coseno en Chroma
    )
    return [v.tolist() for v in vectores]


def embeddear_consulta(pregunta: str) -> list[float]:
    """Un vector para la pregunta (mismo modelo que el índice).

    Nota para Persona 2: a diferencia de la versión con Gemini, esta NO
    recibe un client (no hace falta autenticarse contra ninguna API).
    """
    return embeddear_textos([pregunta])[0]


def ejecutar_embeddings(chunks: list[Document]) -> tuple[list[dict], Path]:
    """Orquesta: chunks -> chunks.json -> vectores locales -> embeddings.json."""
    guardar_chunks_json(chunks, CHUNKS_JSON)

    textos = [c.page_content for c in chunks]
    print(f"Embeddeando {len(textos)} chunks en local con '{EMBEDDING_MODEL}'...")
    vectores = embeddear_textos(textos)

    items = [
        {"text": chunk.page_content, "vector": vector, "metadata": dict(chunk.metadata)}
        for chunk, vector in zip(chunks, vectores)
    ]

    payload = {
        "embedding_model": EMBEDDING_MODEL,
        "total": len(items),
        "dimensions": len(vectores[0]) if vectores else 0,
        "items": items,
    }

    ruta = Path(EMBEDDINGS_JSON)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Guardado: {ruta} ({payload['dimensions']} dimensiones, modelo local)")

    return items, ruta
