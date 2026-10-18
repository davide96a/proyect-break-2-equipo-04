"""Allowlist de tools y ejecución segura con traza (tool, args, status, preview)."""

from src.tools.hora_actual import hora_actual
from src.tools.rag_ask import rag_ask

# Allowlist: solo estas tools se pueden ejecutar.
TOOLS_PERMITIDAS = {
    "hora_actual": hora_actual,
    "rag_ask": rag_ask,
}

PREVIEW_MAX = 200


def _preview(texto: str, n: int = PREVIEW_MAX) -> str:
    """Recorta el texto de una tool para la traza."""
    texto = (texto or "").replace("\n", " ").strip()
    return texto if len(texto) <= n else texto[: n - 3] + "..."


def _entrada(nombre: str, args: dict, resultado: dict) -> dict:
    """Entrada de traza: tool, args, status, preview y resultado completo."""
    return {
        "tool": nombre,
        "args": args,
        "status": resultado.get("status", "ok"),
        "preview": _preview(resultado.get("texto", "")),
        "resultado": resultado,
    }


def ejecutar_tool(nombre: str, args: dict | None = None, permitidas=None) -> dict:
    """Ejecuta una tool solo si está en la allowlist.

    - Si el nombre no está en TOOLS_PERMITIDAS, o `permitidas` (la lista del
      especialista) no lo incluye, NO se ejecuta nada: status "blocked".
    - Nunca lanza excepciones: un fallo de la tool queda como status "error".
    """
    args = dict(args or {})

    if nombre not in TOOLS_PERMITIDAS or (
        permitidas is not None and nombre not in permitidas
    ):
        bloqueada = {"status": "blocked", "texto": f"Error: tool '{nombre}' no está permitida."}
        return _entrada(nombre, args, bloqueada)

    try:
        resultado = TOOLS_PERMITIDAS[nombre](**args)
        if not isinstance(resultado, dict):
            resultado = {"status": "ok", "texto": str(resultado)}
    except Exception as e:  # noqa: BLE001
        resultado = {"status": "error", "texto": f"Error al ejecutar {nombre}: {e}"}

    return _entrada(nombre, args, resultado)
