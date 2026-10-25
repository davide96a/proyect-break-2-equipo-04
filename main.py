"""CLI del agente — Deporte municipal de Madrid.

Uso:
  python main.py                       # chat interactivo: escribe 'aprobar' o 'rechazar' cuando haya plan
  python main.py --demo                # demo: rechazo + aprobación en el mismo thread
  python main.py --demo --auto-aprobar # demo aprobando todo
"""

import argparse

from src.agent import aprobar_plan, nuevo_thread_id, procesar_turno, run_demo


def mostrar(r: dict) -> None:
    if r["error"]:
        print(f"\n[aviso] {r['error']}")
    for linea in r["log"]:
        print(f"  · {linea}")
    for t in r["traza_tools"]:
        print(f"  · tool {t['tool']:<17} {t['status']:<10} {t['preview'][:70]}")
    if r["respuesta"]:
        print(f"\n{r['respuesta']}")
    if r["plan"] and r["pendiente_hitl"]:
        print("\nPLAN PROPUESTO:")
        for p in r["plan"]:
            print(f"  - {p}")
    print(f"\n[thread {r['thread_id']} · pendiente_hitl={r['pendiente_hitl']} · done={r['done']}]")


def interactivo() -> None:
    thread_id = nuevo_thread_id()
    print(f"Conversación {thread_id}. Comandos: 'aprobar', 'rechazar', 'nueva', 'salir'.")
    while True:
        texto = input("\nTú: ").strip()
        orden = texto.lower()
        if orden in ("salir", "exit"):
            break
        if orden == "nueva":
            thread_id = nuevo_thread_id()
            print(f"Nueva conversación {thread_id}.")
        elif orden in ("aprobar", "rechazar"):
            mostrar(aprobar_plan(thread_id, orden == "aprobar"))
        else:
            mostrar(procesar_turno(texto, thread_id))


def demo(auto_aprobar: bool) -> None:
    for etiqueta, r in run_demo(auto_aprobar):
        print(f"\n{'=' * 70}\n>>> {etiqueta}")
        mostrar(r)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente Deporte municipal (LangGraph + HITL)")
    parser.add_argument("--demo", action="store_true", help="Ejecuta el guion de demo")
    parser.add_argument("--auto-aprobar", action="store_true", help="En la demo, aprueba todos los planes")
    args = parser.parse_args()
    demo(args.auto_aprobar) if args.demo else interactivo()
