"""Pruebas básicas: python -m pytest test_adk.py -v  (con el servidor no necesario)."""
from fastapi.testclient import TestClient

import chatbot_adk

client = TestClient(chatbot_adk.app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_webhook_ignora_mensajes_salientes():
    r = client.post(
        "/webhook",
        json={"event": "message_created", "message_type": "outgoing", "content": "hola"},
    )
    assert r.json() == {"ignored": True}


def test_webhook_ignora_otros_eventos():
    r = client.post("/webhook", json={"event": "conversation_updated"})
    assert r.json() == {"ignored": True}
