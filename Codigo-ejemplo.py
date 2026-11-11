"""Ejemplo mínimo: enviar un mensaje a una conversación de Chatwoot por API."""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

base = os.environ["CHATWOOT_BASE_URL"].rstrip("/")
account = os.environ["CHATWOOT_ACCOUNT_ID"]
token = os.environ["CHATWOOT_API_ACCESS_TOKEN"]
conversation_id = 1  # cámbialo por una conversación real

r = httpx.post(
    f"{base}/api/v1/accounts/{account}/conversations/{conversation_id}/messages",
    headers={"api_access_token": token},
    json={"content": "Hola desde el código de ejemplo", "message_type": "outgoing"},
)
print(r.status_code, r.text)
