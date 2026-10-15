"""Evaluación de respuestas generadas: ejecuta el set de queries/ contra responder()."""

import json
import time
from pathlib import Path

from .config import BASE_DIR

from .logic import responder

RUTA_PREGUNTAS = (BASE_DIR / "queries/preguntas_eval.json")
PAUSA_SEGUNDOS = 4  # evita el límite de peticiones por minuto de la cuota gratuita de Gemini


def evaluar_pregunta(item: dict, k: int | None = None) -> dict:
    resultado = responder(item["texto"], k=k)
    return {
        "id": item["id"],
        "texto": item["texto"],
        "deberia_abstenerse": item["deberia_abstenerse"],
        "se_abstuvo": resultado["abstencion"],
        "respuesta": resultado["respuesta"],
        "fuentes": resultado["fuentes"],
        "error": resultado["error"],
        "fuente_esperada": item.get("fuente_esperada"),
        "respuesta_esperada": item.get("respuesta_esperada"),
        "notas": item.get("notas", ""),
    }


def ejecutar_evaluacion(k: int | None = None) -> None:
    preguntas = json.loads(RUTA_PREGUNTAS.read_text(encoding="utf-8"))["preguntas"]
    print(f"Evaluando {len(preguntas)} preguntas (k={k or 'por defecto'})...\n")

    for item in preguntas:
        r = evaluar_pregunta(item, k)
        print("=" * 60)
        print(f"[{r['id']}] {r['texto']}")
        print(f"  deberia_abstenerse={r['deberia_abstenerse']}  se_abstuvo={r['se_abstuvo']}")
        if r["error"]:
            print(f"  ERROR: {r['error']}")
        else:
            print(f"  respuesta: {r['respuesta'][:500]}")
            print(f"  fuentes: {r['fuentes']}")
        if r["respuesta_esperada"]:
            print(f"  esperada: {r['respuesta_esperada']} (fuente: {r['fuente_esperada']})")
        if r["notas"]:
            print(f"  notas: {r['notas']}")
        print()
        time.sleep(PAUSA_SEGUNDOS)
