"""Tests de api_deporte sin red: la agenda se simula y el respaldo se redirige a un fichero temporal."""

import json
from datetime import date

import pytest
import requests

from src.tools import api_dominio as api

HOY = date(2026, 10, 20)


def _evento(titulo, inicio, fin, free=1, dias="MO", hora="18:00", lugar="Polideportivo Test"):
    return {
        "title": titulo,
        "free": free,
        "price": "",
        "dtstart": f"{inicio} {hora}:00.0",
        "dtend": f"{fin} 23:59:00.0",
        "time": hora,
        "recurrence": {"days": dias},
        "event-location": lugar,
        "address": {"district": {"@id": "https://datos.madrid.es/x/Distrito/Villaverde"}},
    }


@pytest.fixture
def eventos():
    return [
        _evento("Yoga al aire libre", "2026-09-01", "2099-12-31"),
        _evento("Ajedrez en los parques", "2026-04-10", "2026-06-01"),  # ya terminó
        _evento("Torneo de pádel", "2099-01-10", "2099-01-11", free=0, dias=""),
    ]


class _Respuesta:
    def __init__(self, eventos):
        self._eventos = eventos

    def raise_for_status(self):
        pass

    def json(self):
        return {"@graph": self._eventos}


@pytest.fixture
def con_red(monkeypatch, eventos):
    monkeypatch.setattr(api.requests, "get", lambda *a, **k: _Respuesta(eventos))


@pytest.fixture
def sin_red(monkeypatch, tmp_path, eventos):
    def caida(*a, **k):
        raise requests.ConnectionError("sin red")

    ruta = tmp_path / "respaldo.json"
    ruta.write_text(json.dumps({"@graph": eventos}), encoding="utf-8")
    monkeypatch.setattr(api.requests, "get", caida)
    monkeypatch.setattr(api, "RUTA_FALLBACK", ruta)


def test_con_red_usa_la_api(con_red):
    r = api.api_deporte("yoga")
    assert r["status"] == "ok"
    assert r["fuente"] == "api"
    assert "Fuente: api" in r["texto"]
    assert "Yoga al aire libre" in r["texto"]


def test_sin_red_usa_el_respaldo_local(sin_red):
    r = api.api_deporte("yoga")
    assert r["status"] == "ok"
    assert r["fuente"] == "local"
    assert "Fuente: local" in r["texto"]


def test_si_fallan_api_y_respaldo_devuelve_error_sin_lanzar(sin_red, monkeypatch, tmp_path):
    monkeypatch.setattr(api, "RUTA_FALLBACK", tmp_path / "no_existe.json")
    r = api.api_deporte("yoga")
    assert r["status"] == "error"
    assert r["texto"].startswith("Error")


def test_el_respaldo_real_tiene_el_formato_esperado():
    datos = json.loads(api.RUTA_FALLBACK.read_text(encoding="utf-8-sig"))
    assert isinstance(datos["@graph"], list) and datos["@graph"]
    assert "title" in datos["@graph"][0]
