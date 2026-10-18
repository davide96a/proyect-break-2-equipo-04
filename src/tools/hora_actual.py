"""Tool auxiliar: fecha y hora actuales en Madrid (determinista, sin red)."""

from datetime import datetime
from zoneinfo import ZoneInfo

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def hora_actual() -> dict:
    """Devuelve el día de la semana, la fecha y la hora actuales en Madrid.

    Úsala cuando haga falta saber qué día es hoy o si algo está abierto ahora.
    """
    ahora = datetime.now(ZoneInfo("Europe/Madrid"))
    texto = f"{DIAS[ahora.weekday()]} {ahora:%d/%m/%Y}, {ahora:%H:%M} (hora de Madrid)"
    return {"status": "ok", "texto": texto, "iso": ahora.isoformat(timespec="seconds")}
