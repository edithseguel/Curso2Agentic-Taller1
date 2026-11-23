"""Pruebas del acceso protegido y errores seguros de la API."""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from api import app as modulo_api


cliente = TestClient(modulo_api.app)


def test_chat_rechaza_token_ausente(monkeypatch):
    """No permite consumir el coordinador sin credencial."""
    monkeypatch.setattr(modulo_api, "TOKEN_ACCESO_CHAT", "token-de-prueba")

    respuesta = cliente.post(
        "/chat", json={"user_id": "prueba", "texto": "Necesito un portal web"}
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "No autorizado."


def test_chat_autorizado(monkeypatch):
    """Ejecuta una solicitud cuando el token coincide."""
    monkeypatch.setattr(modulo_api, "TOKEN_ACCESO_CHAT", "token-de-prueba")
    monkeypatch.setattr(
        modulo_api,
        "ejecutar",
        AsyncMock(
            return_value={
                "ruta": "agente_Cristian_desarrollo_ti",
                "motivo": "Desarrollo solicitado.",
                "pregunta_reformulada": "Cotizar portal web.",
                "respuesta": "Propuesta referencial.",
            }
        ),
    )

    respuesta = cliente.post(
        "/chat",
        headers={"X-Token-Acceso": "token-de-prueba"},
        json={"user_id": "prueba", "texto": "Necesito un portal web"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["ruta"] == "agente_Cristian_desarrollo_ti"


def test_chat_sin_configuracion_rechaza(monkeypatch):
    """No abre el chat accidentalmente si falta el secreto de servidor."""
    monkeypatch.setattr(modulo_api, "TOKEN_ACCESO_CHAT", "")

    respuesta = cliente.post(
        "/chat", json={"user_id": "prueba", "texto": "Necesito un portal web"}
    )

    assert respuesta.status_code == 503


def test_telegram_rechaza_chat_no_autorizado(monkeypatch):
    """La lista opcional bloquea chats ajenos aunque conozcan el webhook."""
    monkeypatch.setattr(modulo_api, "TELEGRAM_SECRET", "secreto-prueba")
    monkeypatch.setattr(modulo_api, "TELEGRAM_ALLOWED_CHAT_IDS", {"123"})

    respuesta = cliente.post(
        "/telegram",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secreto-prueba"},
        json={"message": {"chat": {"id": 999}, "text": "Hola"}},
    )

    assert respuesta.status_code == 403
