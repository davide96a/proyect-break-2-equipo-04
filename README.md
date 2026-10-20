# Agente Deporte municipal de Madrid — Project Break 2

> En construcción.

Agente multiagente con **LangGraph** que amplía el RAG del Project Break 1
(instalaciones, tarifas y normas del deporte municipal de Madrid).

Equipo 06 — María Muriel · Davide Campi · Alejandro Dietta

## Instalación

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
cp .env.example .env               # y pon tu GOOGLE_API_KEY
```

## RAG del PB1

El RAG del PB1 vive en `rag/` como paquete (importado con `scripts/importar_pb1.py`).
Construir el índice una vez (la primera vez descarga el modelo de embeddings, ~470 MB):

```bash
python -m rag --index
python -m rag --ask "¿Cuánto cuesta el abono de piscina?"
```

## Tool multimodal (`describir_imagen`)

Imagen → texto con Gemini (`src/tools/describir_imagen.py`). Envía los bytes de la imagen y un prompt
(más la pregunta del usuario, si la hay) y devuelve `{"status": "ok" | "error", "texto": ...}`; nunca lanza excepciones.

- **Imagen demo:** `assets/imagen_demo.jpg`, la infografía «Cómo adquirir online un Abono Deporte Madrid». Sin ruta, la tool usa esta imagen.
- **En el grafo:** la usa `especialista_instalaciones` cuando la pregunta menciona imagen, foto, cartel o infografía.
- **Requiere** `GOOGLE_API_KEY` en `.env` (mismo modelo que el grafo, `LLM_MODEL`).

Probarla aislada:

```bash
python -c "from src.tools.describir_imagen import describir_imagen; print(describir_imagen(pregunta='¿Qué pasos hay que seguir?'))"
python -m pytest tests/test_describir_imagen.py -v   # sin red ni clave (Gemini simulado)
```

## Estructura

```
├── main.py / app.py      # CLI y Streamlit
├── config.py             # límites, modelo y rutas
├── src/                  # estado, grafo, agente, LLM
│   └── tools/            # allowlist + tools
├── rag/                  # RAG del PB1 como paquete
├── data/                 # fallback de la API
├── assets/               # imagen para la tool multimodal
├── specs/                # especificación (SDD)
├── scripts/              # utilidades
├── tests/
└── entregables/          # informe de decisiones
```
