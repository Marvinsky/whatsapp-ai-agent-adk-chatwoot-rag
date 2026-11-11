# Guía de migración a Google ADK

1. Instala dependencias: `pip install -r requirements.txt`.
2. Mueve tu prompt de sistema al campo `instruction` del `Agent` en `chatbot_adk.py`.
3. Reindexa los documentos con `ingest_documents_adk.py` (las colecciones antiguas de ChromaDB
   pueden tener otros embeddings; borra `chromadb_data/` si cambias de modelo).
4. Si usabas memoria en archivos o RAM, migra el historial a la tabla `chat_history`.
5. Apunta el webhook de Chatwoot a `/webhook` y desactiva el bot anterior.
6. Valida con `pytest test_adk.py`.
