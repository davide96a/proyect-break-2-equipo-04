"""Logging básico de cada consulta (pregunta, k, nº chunks, tiempo, modelo)."""

import json
import time
from pathlib import Path

from .config import BASE_DIR

RUTA_LOG = (BASE_DIR / "output/retrieval_log.jsonl")
RUTA_LOG_GENERACION = (BASE_DIR / "output/generacion_log.jsonl")


def _guardar(ruta: Path, entrada: dict):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")


def log_query(pregunta: str, k: int, n_chunks: int, tiempo: float, modelo: str):
    """Registra la consulta en consola y en output/retrieval_log.jsonl."""
    entrada = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pregunta": pregunta,
        "k": k,
        "n_chunks": n_chunks,
        "tiempo_segundos": round(tiempo, 3),
        "modelo": modelo,
    }
    print(f"[log] k={k} chunks={n_chunks} tiempo={tiempo:.2f}s modelo={modelo} | \"{pregunta}\"")

    _guardar(RUTA_LOG, entrada)


def log_generacion(pregunta: str, resultado: dict):
    """Registra en consola y en output/generacion_log.jsonl el resultado completo de responder()."""
    entrada = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pregunta": pregunta,
        "k": resultado["k"],
        "n_chunks": resultado["n_chunks"],
        "tiempo_segundos": resultado["tiempo_segundos"],
        "modelo": resultado["modelo"],
        "abstencion": resultado["abstencion"],
        "error": resultado["error"],
    }
    if resultado["error"]:
        estado = f"error={resultado['error']}"
    else:
        estado = f"abstencion={'sí' if resultado['abstencion'] else 'no'}"
    print(
        f"[log] generacion k={resultado['k']} chunks={resultado['n_chunks']} "
        f"tiempo={resultado['tiempo_segundos']:.2f}s modelo={resultado['modelo']} {estado} | \"{pregunta}\""
    )

    _guardar(RUTA_LOG_GENERACION, entrada)
