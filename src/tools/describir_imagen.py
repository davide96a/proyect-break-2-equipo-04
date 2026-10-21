"""Tool multimodal: imagen (infografía, cartel) → texto."""

from pathlib import Path

import config

PROMPT = (
    "Describe la imagen en 2-3 frases en español. "
    "Si hay texto, pasos, fechas, precios o lugares visibles, menciónalos."
)


def describir_imagen(ruta: str = "", pregunta: str | None = None) -> dict:
    """Describe una imagen del deporte municipal (infografía, cartel, folleto).

    Sin ruta usa la imagen demo (assets/imagen_demo.jpg).
    Úsala cuando el usuario mencione una imagen, foto, cartel o infografía.
    """
    path = Path(ruta) if (ruta or "").strip() else config.IMAGEN_DEMO
    if not path.is_absolute():
        path = (config.BASE_DIR / path).resolve()
    if not path.exists():
        return {"status": "error", "texto": f"Error: no hay imagen en {path}"}

    if not config.GOOGLE_API_KEY:
        return {"status": "error", "texto": "Error: falta GOOGLE_API_KEY"}

    texto_prompt = PROMPT
    if (pregunta or "").strip():
        texto_prompt += f" Responde además a esta pregunta del usuario: {pregunta.strip()}"

    try:
        from google import genai
        from google.genai import types

        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        client = genai.Client(api_key=config.GOOGLE_API_KEY)
        out = client.models.generate_content(
            model=config.LLM_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(data=path.read_bytes(), mime_type=mime),
                        types.Part.from_text(text=texto_prompt),
                    ],
                )
            ],
            config={"temperature": config.TEMPERATURE},
        )
    except Exception as e:
        return {"status": "error", "texto": f"Error al leer la imagen: {e}"}

    descripcion = (out.text or "").strip()
    if not descripcion:
        return {"status": "error", "texto": "Error: respuesta vacía del modelo."}
    return {"status": "ok", "texto": descripcion}
