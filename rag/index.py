"""Construcción y gestión del índice ChromaDB persistente.

Lee output/embeddings.json (generado por embed.ejecutar_embeddings) y
crea/actualiza una colección ChromaDB persistente en CHROMA_DIR, lista
para consultar desde retrieve.py.
"""

import json
from pathlib import Path

import chromadb

from .config import CHROMA_DIR, EMBEDDINGS_JSON

NOMBRE_COLECCION = "deporte_municipal"


def _cargar_embeddings(ruta: str | Path = EMBEDDINGS_JSON) -> dict:
    """Lee el embeddings.json generado por embed.py."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Ejecuta primero la generación de embeddings (embed.ejecutar_embeddings)."
        )
    return json.loads(ruta.read_text(encoding="utf-8"))


def _limpiar_metadata(metadata: dict) -> dict:
    """ChromaDB no acepta None como valor de metadata; se eliminan esas claves."""
    return {k: v for k, v in metadata.items() if v is not None}


def construir_indice(recrear: bool = True) -> chromadb.Collection:
    """Crea (o recrea) la colección ChromaDB a partir de embeddings.json.

    recrear=True borra la colección existente antes de reconstruirla —
    necesario si cambia el modelo de embeddings o el corpus (--recreate-index).
    """
    payload = _cargar_embeddings()
    items = payload["items"]

    client = chromadb.PersistentClient(path=CHROMA_DIR)

    if recrear:
        try:
            client.delete_collection(NOMBRE_COLECCION)
        except Exception:
            pass

    coleccion = client.get_or_create_collection(
        name=NOMBRE_COLECCION,
        metadata={"hnsw:space": "cosine"},  # los vectores ya vienen normalizados (ver embed.py)
    )

    coleccion.add(
        ids=[str(i) for i in range(len(items))],
        embeddings=[item["vector"] for item in items],
        documents=[item["text"] for item in items],
        metadatas=[_limpiar_metadata(item["metadata"]) for item in items],
    )

    print(f"Índice construido: {len(items)} chunks en la colección '{NOMBRE_COLECCION}' ({CHROMA_DIR})")
    return coleccion


def obtener_coleccion() -> chromadb.Collection:
    """Abre la colección existente sin reconstruirla (para retrieve.py)."""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_collection(NOMBRE_COLECCION)