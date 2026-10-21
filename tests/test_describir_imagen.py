from google import genai

import config
from src.tools import ejecutar_tool
from src.tools.describir_imagen import describir_imagen


class _ClienteFalso:
    """Sustituye a genai.Client: no hay red ni clave real. Guarda lo que se le envía."""

    def __init__(self, texto="", error=None):
        self.texto, self.error, self.enviado, self.config = texto, error, None, None
        self.models = self

    def __call__(self, api_key):
        return self

    def generate_content(self, model, contents, config=None):
        self.enviado, self.config = contents, config
        if self.error:
            raise self.error
        return type("Respuesta", (), {"text": self.texto})()


def test_imagen_inexistente_devuelve_error(tmp_path):
    r = describir_imagen(str(tmp_path / "no_existe.jpg"))
    assert r["status"] == "error"
    assert "no hay imagen" in r["texto"]


def test_sin_clave_devuelve_error(monkeypatch):
    monkeypatch.setattr(config, "GOOGLE_API_KEY", None)
    r = describir_imagen()
    assert r["status"] == "error"
    assert "GOOGLE_API_KEY" in r["texto"]


def test_gemini_simulado_describe_la_imagen_demo(monkeypatch):
    monkeypatch.setattr(config, "GOOGLE_API_KEY", "clave-falsa")
    cliente = _ClienteFalso(texto="Infografía del Abono Deporte Madrid en 4 pasos.")
    monkeypatch.setattr(genai, "Client", cliente)

    r = describir_imagen(pregunta="¿Qué pasos hay que seguir?")

    assert r["status"] == "ok"
    assert r["texto"] == "Infografía del Abono Deporte Madrid en 4 pasos."
    prompt = cliente.enviado[0].parts[1].text
    assert "¿Qué pasos hay que seguir?" in prompt
    assert cliente.config == {"temperature": config.TEMPERATURE}


def test_fallo_de_gemini_devuelve_error(monkeypatch):
    monkeypatch.setattr(config, "GOOGLE_API_KEY", "clave-falsa")
    monkeypatch.setattr(genai, "Client", _ClienteFalso(error=RuntimeError("503 UNAVAILABLE")))

    r = describir_imagen()

    assert r["status"] == "error"
    assert "503" in r["texto"]


def test_esta_en_la_allowlist(monkeypatch):
    monkeypatch.setattr(config, "GOOGLE_API_KEY", "clave-falsa")
    monkeypatch.setattr(genai, "Client", _ClienteFalso(texto="Infografía del abono."))

    r = ejecutar_tool("describir_imagen", {"pregunta": "¿Qué pone?"})

    assert r["status"] == "ok"
    assert r["preview"] == "Infografía del abono."
