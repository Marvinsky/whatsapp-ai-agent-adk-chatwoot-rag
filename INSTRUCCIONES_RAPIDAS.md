# Instrucciones rápidas

1. Completa `.env` con tus claves (Google, Chatwoot, LlamaCloud, Supabase).
2. Ejecuta `supabase_setup.sql` en el SQL Editor de Supabase.
3. Copia tus documentos a `RAG/` y corre:
   ```bash
   python ingest_documents_adk.py
   ```
4. Arranca el bot:
   ```bash
   chmod +x start.sh && ./start.sh
   ```
5. En Chatwoot → Settings → Integrations → Webhooks, agrega
   `https://TU_DOMINIO/webhook` con el evento **message_created**.
   (En local, expón el puerto 8000 con ngrok o cloudflared.)
6. En Evolution API, conecta tu instancia de WhatsApp al inbox de Chatwoot.
7. Escribe por WhatsApp y verifica la respuesta.
