"""Punto de entrada — RAG Deporte municipal.

Uso:
  python -m rag --index
  python -m rag --query "¿Cuánto cuesta el abono de piscina?"
  python -m rag --ask "¿Cuánto cuesta la entrada a la piscina de verano para adultos?"
  python -m rag --ask "..." --k 5
  python -m rag --eval
  python -m rag --eval --k 5
  streamlit run app.py
"""

import argparse


def _cmd_ask(pregunta: str, k: int | None) -> None:
    from .logic import responder

    resultado = responder(pregunta, k=k)
    if resultado["error"]:
        print(f"\nERROR: {resultado['error']}")
        return

    print(f"\n{resultado['respuesta']}")
    if resultado["abstencion"]:
        print("\n(El sistema se ha abstenido: no hay evidencia suficiente en los documentos.)")
    else:
        print("\nFuentes:")
        for fuente in resultado["fuentes"]:
            print(f"  - {fuente}")


def _cmd_eval(k: int | None) -> None:
    from .eval_generation import ejecutar_evaluacion

    ejecutar_evaluacion(k=k)


def main():
    parser = argparse.ArgumentParser(description="RAG CLI - Deporte municipal")
    parser.add_argument("--index", action="store_true", help="Indexar el corpus")
    parser.add_argument("--query", type=str, help="Solo retrieval: mostrar chunks recuperados")
    parser.add_argument("--ask", type=str, help="Pregunta RAG completa (retrieval + generación)")
    parser.add_argument("--eval", action="store_true", help="Evaluar las respuestas con el set de queries/")
    parser.add_argument("--k", type=int, default=None, help="Override de TOP_K")

    args = parser.parse_args()

    if args.index:
        from .load import cargar_documentos
        from .chunk import fragmentar_documentos
        from .embed import ejecutar_embeddings
        from .index import construir_indice

        docs = cargar_documentos()
        chunks = fragmentar_documentos(docs)
        ejecutar_embeddings(chunks)
        construir_indice()

    elif args.query:
        from .retrieve import retrieve
        from .config import TOP_K

        k = args.k or TOP_K
        resultados = retrieve(args.query, k=k)
        for i, r in enumerate(resultados, 1):
            print(f"\n--- Chunk {i} (source: {r['source']}, score: {r['score']:.3f}) ---")
            print(r["text"][:300])

    elif args.ask:
        _cmd_ask(args.ask, args.k)

    elif args.eval:
        _cmd_eval(args.k)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()