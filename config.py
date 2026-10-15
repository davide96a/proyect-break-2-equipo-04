"""Configuración central del agente (límites, modelo, rutas).

Las rutas se calculan desde este fichero, así el proyecto funciona
lo lances desde donde lo lances (python main.py, streamlit run app.py, tests).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# --- LLM ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite")
TEMPERATURE = 0.0

# --- Límites duros (los aplica Python, nunca el LLM) ---
MAX_ITER = 6     # pasos máximos del supervisor por turno
MAX_STEPS = 3    # llamadas a tools máximas por especialista y turno
MAX_TURNS = 10   # turnos de usuario por conversación (thread_id)

# --- Rutas ---
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
SALIDAS_DIR = BASE_DIR / "salidas"          # fichas generadas al aprobar (no se versiona)
IMAGEN_DEMO = ASSETS_DIR / "imagen_demo.jpg"
FALLBACK_API = DATA_DIR / "fallback_api.json"
