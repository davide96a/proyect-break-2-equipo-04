"""Tool api_deporte: agenda de actividades deportivas del Ayuntamiento de Madrid.

Fuente: https://datos.madrid.es/dataset/212504-0-agenda-actividades-deportes (JSON-LD,
las actividades están en la clave "@graph"). Si falla la red o la respuesta,
usa la copia local data/fallback_api.json (descargada el 20/10/2026).
"""

import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

URL_API = (
    "https://datos.madrid.es/dataset/212504-0-agenda-actividades-deportes/resource/"
    "212504-2-agenda-actividades-deportes-json/download/"
    "212504-2-agenda-actividades-deportes-json.json"
)
RUTA_FALLBACK = Path(__file__).resolve().parents[2] / "data" / "fallback_api.json"
FECHA_COPIA_LOCAL = "20/10/2026"
TIMEOUT_SEGUNDOS = 12
LIMITE_DEFECTO = 5
LIMITE_MAXIMO = 10

DIAS = {"MO": "lunes", "TU": "martes", "WE": "miércoles", "TH": "jueves",
        "FR": "viernes", "SA": "sábado", "SU": "domingo"}

# Palabras de la pregunta que no sirven para buscar (ya estamos en la agenda deportiva).
IGNORAR = {
    "que", "hay", "para", "como", "donde", "cual", "cuales", "cuando", "quiero", "puedo",
    "hacer", "algun", "alguna", "esta", "este", "estos", "semana", "hoy", "ahora", "manana",
    "actividad", "actividades", "evento", "eventos", "agenda", "deporte", "deportes",
    "deportiva", "deportivas", "deportivo", "municipal", "municipales", "madrid", "sobre",
    "tiene", "tienen", "gratis", "gratuita", "gratuitas", "gratuito", "gratuitos",
}


def _normalizar(texto) -> str:
    """Minúsculas y sin tildes, para comparar palabras."""
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _d(valor) -> dict:
    return valor if isinstance(valor, dict) else {}


def _fecha(valor):
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def _cargar() -> tuple[list, str]:
    """Pide la agenda a datos.madrid.es; si falla, lee la copia local."""
    try:
        r = requests.get(URL_API, timeout=TIMEOUT_SEGUNDOS)
        r.raise_for_status()
        eventos = r.json()["@graph"]
        if not isinstance(eventos, list):
            raise ValueError("formato inesperado")
        return eventos, "api"
    except Exception:  # noqa: BLE001  (red, timeout, JSON raro...)
        datos = json.loads(RUTA_FALLBACK.read_text(encoding="utf-8-sig"))
        return datos["@graph"], "local"


def _vigente(e: dict, hoy: date) -> bool:
    fin = _fecha(e.get("dtend")) or _fecha(e.get("dtstart"))
    return fin is None or fin >= hoy


def _lugar(e: dict) -> str:
    lugar = (
        (e.get("event-location") or "").strip()
        or (_d(e.get("organization")).get("organization-name") or "").strip()
        or "lugar por confirmar"
    )
    distrito = (_d(_d(e.get("address")).get("district")).get("@id") or "").rsplit("/", 1)[-1]
    return f"{lugar} ({distrito})" if distrito else lugar


def _cuando(e: dict) -> str:
    inicio, fin = _fecha(e.get("dtstart")), _fecha(e.get("dtend"))
    hora = (e.get("time") or "").strip()
    dias = [DIAS[d] for d in (_d(e.get("recurrence")).get("days") or "").split(",") if d in DIAS]
    rango = f"del {inicio:%d/%m/%Y} al {fin:%d/%m/%Y}" if inicio and fin and fin != inicio else ""
    if dias:
        franja = "todos los días" if len(dias) == 7 else ", ".join(dias)
        return " ".join(p for p in (franja, hora) if p) + (f", {rango}" if rango else "")
    base = rango or (f"{inicio:%d/%m/%Y}" if inicio else "fecha por confirmar")
    return f"{base} {hora}".strip()


def _precio(e: dict) -> str:
    if e.get("free") in (1, "1", True):
        return "gratis"
    precio = str(e.get("price") or "").strip()
    return precio or "de pago (precio no indicado)"


def _linea(e: dict) -> str:
    return f"- {e.get('title', 'Sin título')} · {_lugar(e)} · {_cuando(e)} · {_precio(e)}"


def _buscar(eventos: list, consulta: str, limite: int, hoy: date) -> list:
    """Actividades vigentes que encajan con la consulta (por palabras sueltas)."""
    n = _normalizar(consulta)
    solo_gratis = "gratis" in n or "gratuit" in n
    claves = [p for p in re.findall(r"\w+", n) if len(p) > 3 and p not in IGNORAR]

    candidatos = []
    for e in eventos:
        if not _vigente(e, hoy):
            continue
        if solo_gratis and e.get("free") not in (1, "1", True):
            continue
        pajar = _normalizar(f"{e.get('title', '')} {_lugar(e)}")
        puntos = sum(1 for c in claves if c in pajar)
        if claves and puntos == 0:
            continue
        candidatos.append((-puntos, str(e.get("dtstart") or ""), e))
    candidatos.sort(key=lambda c: (c[0], c[1]))
    return [c[2] for c in candidatos[:limite]]


def api_deporte(consulta: str = "", limite: int = LIMITE_DEFECTO) -> dict:
    """Busca actividades y eventos deportivos municipales vigentes en Madrid
    (agenda en vivo del Ayuntamiento): qué hay, dónde, qué días y a qué hora,
    y si son gratuitas. Si no hay red, usa una copia local.
    """
    try:
        limite = max(1, min(int(limite), LIMITE_MAXIMO))
    except (TypeError, ValueError):
        limite = LIMITE_DEFECTO

    try:
        eventos, fuente = _cargar()
    except Exception as e:  # noqa: BLE001  (ni API ni respaldo local)
        return {"status": "error", "texto": f"Error: no se pudo leer la agenda ({e}).", "fuente": None}

    hoy = datetime.now(ZoneInfo("Europe/Madrid")).date()
    elegidos = _buscar(eventos, consulta, limite, hoy)
    cabecera = (
        "Fuente: api (datos.madrid.es)"
        if fuente == "api"
        else f"Fuente: local (copia del {FECHA_COPIA_LOCAL})"
    )
    if not elegidos:
        return {
            "status": "abstencion",
            "texto": f"{cabecera}\nNo hay actividades vigentes en la agenda que coincidan con la consulta.",
            "fuente": fuente,
        }
    return {"status": "ok", "texto": "\n".join([cabecera] + [_linea(e) for e in elegidos]), "fuente": fuente}
