# Chatbot WhatsApp con Google ADK

## Componentes
- **Evolution API**: puente de WhatsApp (instancia conectada al inbox de Chatwoot).
- **Chatwoot**: bandeja de entrada y webhooks.
- **Google ADK** (`Agent` + `Runner`): genera las respuestas con Gemini.
- **ChromaDB**: base vectorial local (`chromadb_data/`) alimentada desde `RAG/`.
- **LlamaCloud (LlamaParse)**: convierte PDF/DOCX a markdown en la ingesta.
- **Supabase**: historial de conversaciones.

## Endpoints
- `GET /health`
- `POST /webhook` — recibe `message_created` de Chatwoot; ignora mensajes salientes.

## Variables de entorno
`GOOGLE_API_KEY`, `CHATWOOT_BASE_URL`, `CHATWOOT_ACCOUNT_ID`, `CHATWOOT_API_ACCESS_TOKEN`,
`LLAMA_CLOUD_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`.

## Desarrollo
```bash
pip install -r requirements.txt
pytest test_adk.py -v
uvicorn chatbot_adk:app --reload
```
