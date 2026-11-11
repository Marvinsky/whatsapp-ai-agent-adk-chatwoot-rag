# Chatbot para WhatsApp con Evolution API y Chatwoot

Empieza aquí.

```
WhatsApp ⇄ Evolution API ⇄ Chatwoot ──webhook──▶ chatbot_adk.py (Google ADK)
                                                   ├─ ChromaDB (RAG, carpeta RAG/)
                                                   └─ Supabase (historial)
```

## Archivos
| Archivo | Para qué sirve |
|---|---|
| `chatbot_adk.py` | Servidor FastAPI con el webhook y el agente ADK |
| `ingest_documents_adk.py` | Carga documentos de `RAG/` a `chromadb_data/` |
| `supabase_setup.sql` | Tabla `chat_history` |
| `start.sh` | Crea el venv y arranca el servidor |
| `test_adk.py` | Pruebas |
| `Codigo-ejemplo.py` | Ejemplo de envío a Chatwoot |
| `INSTRUCCIONES_RAPIDAS.md` | Pasos mínimos |
| `GUIA_MIGRACION.md` | Migrar de otra versión a ADK |
| `SUPABASE_SETUP.md` | Configurar Supabase |
| `README_ADK.md` | Documentación técnica |

Rellena `.env` antes de arrancar. No subas `.env` a git.
