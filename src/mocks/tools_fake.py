"""Tools falsas con el mismo formato que src/tools (PR #3). Se activan con USE_MOCKS=1.

Cada tool devuelve {"status", "texto", ...} y ejecutar_tool devuelve la entrada
de traza {tool, args, status, preview, resultado}, igual que la versión real.
"""


def rag_ask(consulta: str) -> dict:
    if "francia" in consulta.lower():  # caso de abstención para probar
        return {"status": "abstencion",
                "texto": "No tengo información suficiente en los documentos para responder a esa pregunta.",
                "fuentes": []}
    return {"status": "ok",
            "texto": "[MOCK] La entrada de adulto a la piscina de verano cuesta 4,50 €.",
            "fuentes": ["300083-10-deportes-tarifas.xlsx"]}


def api_deporte(consulta: str) -> dict:
    return {"status": "ok", "texto": "[MOCK] Yoga al aire libre · CDM Moratalaz · 2026-10-18 10:00",
            "fuente": "local"}


def hora_actual() -> dict:
    return {"status": "ok", "texto": "jueves 15/10/2026, 18:30 (hora de Madrid)",
            "iso": "2026-10-15T18:30:00+02:00"}


def describir_imagen(ruta: str, pregunta: str | None = None) -> dict:
    return {"status": "ok", "texto": f"[MOCK] Infografía ({ruta}): cómo sacar el Abono Deporte Madrid online."}


TOOLS_PERMITIDAS = {"rag_ask": rag_ask, "api_deporte": api_deporte,
                    "hora_actual": hora_actual, "describir_imagen": describir_imagen}


def ejecutar_tool(nombre: str, args: dict | None = None, permitidas=None) -> dict:
    args = dict(args or {})
    if nombre not in TOOLS_PERMITIDAS or (permitidas is not None and nombre not in permitidas):
        resultado = {"status": "blocked", "texto": f"Error: tool '{nombre}' no está permitida."}
    else:
        try:
            resultado = TOOLS_PERMITIDAS[nombre](**args)
        except Exception as e:  # noqa: BLE001
            resultado = {"status": "error", "texto": f"Error al ejecutar {nombre}: {e}"}
    return {"tool": nombre, "args": args, "status": resultado["status"],
            "preview": resultado["texto"][:200], "resultado": resultado}
