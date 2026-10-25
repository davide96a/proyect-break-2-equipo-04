"""Prueba cada tool fuera del grafo (sin LLM de por medio).

  python scripts/probar_tools.py                # todas (rag_ask y describir_imagen necesitan índice y clave)
  python scripts/probar_tools.py --sin-gemini   # solo las que no llaman a Gemini
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # para importar src/ y config
sys.stdout.reconfigure(encoding="utf-8")

from src.tools import ejecutar_tool  # noqa: E402

# (tool, args, estados esperados, ¿llama a Gemini?)
CASOS = [
    ("hora_actual", {}, {"ok"}, False),
    ("api_deporte", {"consulta": "ajedrez"}, {"ok", "abstencion"}, False),
    ("rag_ask", {"consulta": "cuanto cuesta la entrada a la piscina de verano para adultos"}, {"ok"}, True),
    ("rag_ask", {"consulta": "cual es la capital de francia"}, {"abstencion"}, True),
    ("describir_imagen", {"pregunta": "que pasos hay que seguir"}, {"ok"}, True),
    ("borrar_todo", {}, {"blocked"}, False),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba las tools fuera del grafo")
    parser.add_argument("--sin-gemini", action="store_true", help="omite las tools que llaman a Gemini")
    args = parser.parse_args()

    fallos = 0
    for tool, params, esperados, usa_gemini in CASOS:
        if usa_gemini and args.sin_gemini:
            continue
        r = ejecutar_tool(tool, params)
        bien = r["status"] in esperados
        fallos += not bien
        print(f"[{'OK' if bien else 'REVISAR'}] {tool} {params} -> {r['status']}")
        print(f"        {r['preview']}")

    if fallos:
        print(f"\n{fallos} caso(s) a revisar (¿503 de Gemini, sin índice o sin clave?)")
    else:
        print("\nTodo correcto")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
