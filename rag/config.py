import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")  # el .env único está en la raíz del repo

# --- API ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Modelos ---
EMBEDDING_MODEL ="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # local (HF); antes: Gemini
GENERATION_MODEL = "gemini-3.1-flash-lite"
TEMPERATURE = 0.0

# --- Chunking ---
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# --- Retrieval ---
TOP_K = 3
MAX_CHUNKS = 5

# --- Paths ---
DATA_DIR = str(BASE_DIR / "data")
CHROMA_DIR = str(BASE_DIR / "chroma")

# --- Ingesta ---
# Ficheros del corpus "Deporte municipal": los tres CSV de centros comparten
# idéntico esquema de columnas; el XLSX de tarifas y el CSV de descuentos
# necesitan trato distinto (ver load.py).
EXTENSIONES_PDF = {".pdf"}

CSV_CENTROS = {
    "200186-0-polideportivos-csv.csv": "polideportivo",
    "200215-0-instalaciones-deportivas-csv.csv": "instalacion_basica",
    "210227-0-piscinas-publicas-csv.csv": "piscina",
}
XLSX_TARIFAS = "300083-10-deportes-tarifas.xlsx"
CSV_DESCUENTOS = "300097-3-deportes-descuentos-csv.csv"

# --- Salida del pipeline offline (embed.py) ---
OUTPUT_DIR = str(BASE_DIR / "output")
CHUNKS_JSON = str(BASE_DIR / "output/chunks.json")
EMBEDDINGS_JSON = str(BASE_DIR / "output/embeddings.json")
EMBED_BATCH_SIZE = 32  # nº de textos por lote al codificar en local (sentence-transformers)
PAUSE_BETWEEN_BATCHES = 2
