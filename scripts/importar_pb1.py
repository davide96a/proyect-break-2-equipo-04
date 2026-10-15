"""Copia el RAG del PB1 dentro de este repo como paquete `rag/` (se ejecuta UNA vez).

Uso:
  python scripts/importar_pb1.py ../proyect-break-1-equipo-06

Qué hace (y por qué):
  1. Copia src/*.py, config.py, main.py, data/ y queries/ del PB1 a rag/.
  2. Imports absolutos → relativos (`from config` → `from .config`, `from src.x` → `from .x`),
     porque este repo ya tiene su propio config.py y su propio src/ y chocarían.
  3. Rutas relativas al cwd ("data", "chroma", "output/...") → relativas a rag/,
     para que funcione igual desde main.py, desde Streamlit o desde un test.
  4. responder(): k acotado a MAX_CHUNKS.
Si algún reemplazo esperado no se encuentra, se para con error (nada a medias).
"""

import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "rag"


def reemplazar(texto: str, viejo: str, nuevo: str, fichero: str) -> str:
    if viejo not in texto:
        sys.exit(f"ERROR: no encuentro {viejo!r} en {fichero}; revisa el PB1 a mano.")
    return texto.replace(viejo, nuevo)


def imports_relativos(texto: str) -> str:
    texto = re.sub(r"^(\s*)from config import", r"\1from .config import", texto, flags=re.M)
    texto = re.sub(r"^(\s*)from src\.(\w+) import", r"\1from .\2 import", texto, flags=re.M)
    return texto


def main(origen: Path) -> None:
    if not (origen / "src" / "logic.py").exists():
        sys.exit(f"ERROR: {origen} no parece el repo del PB1 (falta src/logic.py)")
    if DESTINO.exists():
        sys.exit("ERROR: rag/ ya existe; bórralo si quieres reimportar.")
    DESTINO.mkdir()

    # 1) código
    for py in sorted((origen / "src").glob("*.py")):
        if py.name != "__init__.py":
            (DESTINO / py.name).write_text(imports_relativos(py.read_text(encoding="utf-8")), encoding="utf-8")
    main_txt = imports_relativos((origen / "main.py").read_text(encoding="utf-8"))
    (DESTINO / "__main__.py").write_text(main_txt.replace("python main.py", "python -m rag"), encoding="utf-8")

    # 2) config con rutas absolutas basadas en rag/
    cfg = (origen / "config.py").read_text(encoding="utf-8")
    cfg = reemplazar(cfg, "from dotenv import load_dotenv\n",
                     "from pathlib import Path\n\nfrom dotenv import load_dotenv\n", "config.py")
    cfg = reemplazar(cfg, "load_dotenv()",
                     "BASE_DIR = Path(__file__).resolve().parent\n"
                     "load_dotenv(BASE_DIR.parent / \".env\")  # el .env único está en la raíz del repo",
                     "config.py")
    for nombre, valor in {"DATA_DIR": "data", "CHROMA_DIR": "chroma", "OUTPUT_DIR": "output",
                          "CHUNKS_JSON": "output/chunks.json",
                          "EMBEDDINGS_JSON": "output/embeddings.json"}.items():
        cfg = reemplazar(cfg, f'{nombre} = "{valor}"', f'{nombre} = str(BASE_DIR / "{valor}")', "config.py")
    (DESTINO / "config.py").write_text(cfg, encoding="utf-8")

    # 3) rutas fijas dentro del código
    for fichero in ("logging_utils.py", "eval_generation.py"):
        ruta = DESTINO / fichero
        txt = ruta.read_text(encoding="utf-8")
        txt, n = re.subn(r'Path\("((?:output|queries)/[^"]+)"\)', r'(BASE_DIR / "\1")', txt)
        if n == 0:
            sys.exit(f"ERROR: no encuentro rutas relativas en {fichero}")
        txt = reemplazar(txt, "from pathlib import Path\n",
                         "from pathlib import Path\n\nfrom .config import BASE_DIR\n", fichero)
        ruta.write_text(txt, encoding="utf-8")

    # 4) k acotado en responder()
    ruta = DESTINO / "logic.py"
    txt = ruta.read_text(encoding="utf-8")
    txt = reemplazar(txt, "from .config import GENERATION_MODEL, TOP_K",
                     "from .config import GENERATION_MODEL, MAX_CHUNKS, TOP_K", "logic.py")
    txt = reemplazar(txt, "    k = k or TOP_K\n", "    k = min(k or TOP_K, MAX_CHUNKS)\n", "logic.py")
    ruta.write_text(txt, encoding="utf-8")

    # 5) datos, preguntas de evaluación y __init__
    shutil.copytree(origen / "data", DESTINO / "data")
    if (origen / "queries").exists():
        shutil.copytree(origen / "queries", DESTINO / "queries")
    (DESTINO / "__init__.py").write_text(
        '"""RAG del PB1 (Deporte municipal) empaquetado para el agente."""\n\n\n'
        "def responder(pregunta: str, k: int | None = None) -> dict:\n"
        '    """Import diferido: el modelo de embeddings y Chroma solo se cargan al usarlo."""\n'
        "    from .logic import responder as _responder\n\n"
        "    return _responder(pregunta, k=k)\n",
        encoding="utf-8",
    )
    print(f"OK: RAG del PB1 copiado en {DESTINO}. Siguiente paso: python -m rag --index")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]).resolve())
