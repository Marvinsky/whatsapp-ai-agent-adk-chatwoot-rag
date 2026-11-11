#!/bin/bash
# Arranca el chatbot (webhook de Chatwoot) en el puerto 8000
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

source .venv/bin/activate
uvicorn chatbot_adk:app --host 0.0.0.0 --port 8000 --reload
