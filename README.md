# Chatbot de WhatsApp con Google ADK, Chatwoot y RAG

Asesora virtual para WhatsApp que responde con información real del negocio.
Proyecto de práctica basado en el curso de Datapath, adaptado y ampliado.

```
WhatsApp ⇄ Evolution API ⇄ Chatwoot ──webhook──▶ chatbot_adk.py (FastAPI + Google ADK)
                                                   ├─ tool obtener_informacion_curso   → Supabase (tabla info_curso)
                                                   ├─ tool buscar_en_base_conocimientos → LlamaCloud (RAG)
                                                   └─ historial de conversación        → Supabase (conversation_history)
```

## Qué hace
- Recibe los mensajes de Chatwoot por webhook y responde con un agente de Google ADK (Gemini).
- Solo atiende conversaciones con la etiqueta `atiende-ia` y mensajes entrantes.
- Si el cliente pide hablar con una persona, cambia la etiqueta a `atiende-humano` y avisa.
- Guarda el historial en Supabase (con respaldo en memoria si no está disponible).
- Endpoints auxiliares: `/health`, `/stats`, `/history/{id}`, `/conversations`, `/test`.

## Requisitos
Python 3.11, cuentas de Google AI Studio (con facturación), Chatwoot, Evolution API, LlamaCloud y Supabase.

## Puesta en marcha
1. `pip install -r requirements.txt`
2. Copia `.env.example` a `.env` y completa tus claves.
3. En el SQL Editor de Supabase, ejecuta `supabase_setup.sql`.
4. Pon tus documentos en `RAG/Base_de_Conocimiento_Automatizacion/` y ejecuta `python RAG/rag_llamaparse.py`.
5. `python chatbot_adk.py` (servidor en el puerto 8000).
6. En desarrollo, expón el puerto con ngrok y registra `https://<tu-url>/webhook` en Chatwoot
   (Settings → Integrations → Webhooks, evento `message_created`).

## Seguridad
- Las claves viven solo en `.env`, que está en `.gitignore`.
- Usa la **Secret key** de Supabase solo en el backend.
- Con `DEBUG_LOGS=1` se imprimen los mensajes de los clientes: apágalo en producción.

## Stack
Python · FastAPI · Google ADK · Gemini · Chatwoot · Evolution API · Supabase · LlamaCloud · ngrok
