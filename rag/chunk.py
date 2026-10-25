"""Fragmentación (chunking) de documentos.

Parámetros en config.py: CHUNK_SIZE, CHUNK_OVERLAP.
"""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import CHUNK_OVERLAP, CHUNK_SIZE


def _crear_splitter() -> RecursiveCharacterTextSplitter:
    """Splitter de LangChain: respeta CHUNK_SIZE y CHUNK_OVERLAP."""
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )


def fragmentar_documentos(documentos: list[Document]) -> list[Document]:
    """Parte cada documento en chunks y añade metadata útil para depurar."""
    if not documentos:
        return []

    splitter = _crear_splitter()
    chunks = splitter.split_documents(documentos)

    # Enriquecemos metadata: posición del chunk y longitud del texto
    enriquecidos: list[Document] = []
    for i, chunk in enumerate(chunks):
        meta = dict(chunk.metadata)
        meta["chunk_index"] = i
        meta["chunk_size"] = len(chunk.page_content)
        enriquecidos.append(
            Document(page_content=chunk.page_content, metadata=meta)
        )
    return enriquecidos
