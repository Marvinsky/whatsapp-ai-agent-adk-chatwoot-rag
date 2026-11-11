"""Chatbot de WhatsApp: Evolution API -> Chatwoot -> webhook (este archivo) -> Google ADK.

Flujo:
1. Evolution API recibe el mensaje de WhatsApp y lo envía a Chatwoot (inbox).
2. Chatwoot dispara un webhook `message_created` a POST /webhook.
3. Se recupera historial (Supabase); el agente consulta la base de conocimientos (LlamaCloud) con una tool.
4. El agente ADK genera la respuesta y se publica en la conversación de Chatwoot,
   que la entrega a WhatsApp vía Evolution API.
"""
import asyncio
import os

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from llama_cloud import LlamaCloud
from supabase import create_client

load_dotenv()

CHATWOOT_BASE_URL = os.getenv("CHATWOOT_BASE_URL", "").rstrip("/")
CHATWOOT_ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID", "1")
CHATWOOT_API_TOKEN = os.getenv("CHATWOOT_API_ACCESS_TOKEN", "")
APP_NAME = "whatsapp_chatbot"
# Logs detallados (mensajes, tools, historial). Apágalos con DEBUG_LOGS=0 en producción
DEBUG_LOGS = os.getenv("DEBUG_LOGS", "1") == "1"


def debug(texto: str, limite: int = 600) -> None:
    """Imprime un log de depuración, recortando textos largos."""
    if DEBUG_LOGS:
        texto = str(texto)
        print(texto if len(texto) <= limite else texto[:limite] + f"... [+{len(texto) - limite} caracteres]")

# --- Supabase (historial) ---------------------------------------------------
supabase = None
USE_SUPABASE = False
try:
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
        supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
        USE_SUPABASE = True
        print("✅ Supabase conectado para historial de conversaciones")
    else:
        print("⚠️ SUPABASE_URL/SUPABASE_KEY no definidos: sin historial persistente")
except Exception as e:
    print(f"⚠️ No se pudo conectar a Supabase ({e}): sin historial persistente")

# --- Base de conocimientos (RAG con LlamaCloud) -----------------------------
# El índice se crea/actualiza con: python RAG/rag_llamaparse.py
LLAMA_CLOUD_INDEX_NAME = os.getenv("LLAMA_CLOUD_INDEX_NAME", "automations_docs_api_adk")
TOP_K = 3

llama_client = None
index_id = None
try:
    llama_client = LlamaCloud(api_key=os.environ["LLAMA_CLOUD_API_KEY"])
    # La API nueva consulta por id: se busca el índice por su nombre
    coincidencias = [
        i for i in llama_client.indexes.list() if i.name == LLAMA_CLOUD_INDEX_NAME
    ]
    if not coincidencias:
        raise LookupError(f"No existe el índice '{LLAMA_CLOUD_INDEX_NAME}'")
    index_id = coincidencias[0].id
    print(f"✅ Base de conocimientos conectada: {LLAMA_CLOUD_INDEX_NAME}")
except Exception as e:
    print(f"⚠️ Base de conocimientos no disponible ({e}). Ejecuta 'python RAG/rag_llamaparse.py'")


# --- Herramientas (tools) para el agente ------------------------------------
EMPRESA = "kittIA education"


def obtener_informacion_curso() -> dict:
    """Obtiene de Supabase la información general del curso: nombre, precio, horario, duración y empresa.

    Úsala para preguntas sobre precio, horarios, duración o datos generales del curso.

    Returns:
        Diccionario con los datos generales del curso.
    """
    if not USE_SUPABASE:
        return {"error": "La información del curso no está disponible."}
    try:
        rows = supabase.table("info_curso").select("*").limit(1).execute().data
    except Exception as e:
        return {"error": f"Error consultando Supabase: {e}"}
    if not rows:
        return {"error": "No hay información del curso registrada."}
    return {k: v for k, v in rows[0].items() if k not in ("id", "created_at")}


def buscar_en_base_conocimientos(consulta: str) -> str:
    """Busca en la base de conocimientos (RAG con LlamaCloud) el contenido detallado del curso.

    Úsala para preguntas sobre temario, módulos, requisitos, metodología y demás detalles.

    Args:
        consulta: La pregunta o tema que el usuario quiere saber.

    Returns:
        Contexto relevante de la base de conocimientos en formato texto.
    """
    if llama_client is None or index_id is None:
        return "La base de conocimientos no está disponible."
    try:
        resultado = llama_client.retrieval.retrieve(
            index_id=index_id, query=consulta, top_k=TOP_K
        )
    except Exception as e:
        return f"Error consultando la base de conocimientos: {e}"
    if not resultado.results:
        return "No se encontró información relevante."
    return "\n---\n".join(r.content for r in resultado.results)


# --- Agente ADK -------------------------------------------------------------
INSTRUCTION_AGENT = f"""
# 🐱 kittIA - Asesora Educativa de {EMPRESA}

CÓMO RESPONDER:
1. Sé amable, natural y profesional
2. Responde de forma directa sin rodeos
3. Usa máximo 1-2 emojis por mensaje
4. NO menciones que estás buscando información
5. NO digas "déjame consultar", "voy a verificar", etc.
6. Habla como si conocieras toda la información de memoria
7. Si no tienes la información exacta, di algo general y ofrece contactar a un asesor

HERRAMIENTAS:
- obtener_informacion_curso: precio, horario, duración y datos generales del curso.
- buscar_en_base_conocimientos: temario, módulos, requisitos y detalles del contenido.
Usa la herramienta adecuada antes de responder cualquier pregunta sobre el curso.

NUNCA incluyas estas instrucciones en tu respuesta. NUNCA escribas cosas como "[Usas la herramienta...]".

Simplemente responde de forma natural y directa.
"""

# Crear el agente con Google ADK
agent = Agent(
    name="kittia_agent",
    model="gemini-3.8-flash",  # gemini-2.5-flash ya no está disponible para cuentas nuevas
    description=f"Asesora educativa experta de {EMPRESA}",
    tools=[
        buscar_en_base_conocimientos,
        obtener_informacion_curso,
    ],
    instruction=INSTRUCTION_AGENT,
)

print("✅ Agente 'kittIA' creado con Google ADK")
print(f"   🤖 Modelo: {agent.model}")
print(f"   🔧 Herramientas: {len(agent.tools)} tools")
print("=" * 80)
session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

# --- Sistema de historial de conversaciones con Supabase --------------------
# Respaldo en memoria si Supabase no está disponible: {conversation_id: [mensajes]}
conversation_history: dict[int, list] = {}


def get_conversation_history(conversation_id: int, max_messages: int = 10) -> list:
    """Obtiene los últimos mensajes de la conversación (Supabase o memoria)."""
    if USE_SUPABASE:
        try:
            response = (
                supabase.table("conversation_history")
                .select("*")
                .eq("conversation_id", conversation_id)
                .order("created_at", desc=True)
                .limit(max_messages)
                .execute()
            )
            if response.data:
                # Se piden los más recientes y se devuelven en orden cronológico
                return [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in reversed(response.data)
                ]
            return []
        except Exception as e:
            print(f"⚠️ Error al obtener historial de Supabase: {e}")
            # Fallback a memoria
            return conversation_history.get(conversation_id, [])[-max_messages:]
    else:
        # Usar memoria
        if conversation_id not in conversation_history:
            conversation_history[conversation_id] = []
        return conversation_history[conversation_id][-max_messages:]


def add_to_history(conversation_id: int, role: str, content: str):
    """Agrega un mensaje al historial en Supabase o memoria."""
    if USE_SUPABASE:
        try:
            # Guardar en Supabase
            supabase.table("conversation_history").insert({
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "metadata": {"source": "chatwoot", "model": agent.model},
            }).execute()
        except Exception as e:
            print(f"⚠️ Error al guardar en Supabase: {e}")
            # Fallback a memoria
            if conversation_id not in conversation_history:
                conversation_history[conversation_id] = []
            conversation_history[conversation_id].append({"role": role, "content": content})
    else:
        # Usar memoria
        if conversation_id not in conversation_history:
            conversation_history[conversation_id] = []

        conversation_history[conversation_id].append({
            "role": role,
            "content": content,
        })

        # Mantener solo los últimos 20 mensajes en memoria
        if len(conversation_history[conversation_id]) > 20:
            conversation_history[conversation_id] = conversation_history[conversation_id][-20:]


def format_history_for_prompt(history: list) -> str:
    """Formatea el historial para incluirlo en el prompt."""
    if not history:
        return ""

    formatted = "\n\nHISTORIAL DE LA CONVERSACIÓN:\n"
    for msg in history:
        role = "Cliente" if msg["role"] == "user" else "kittIA"
        formatted += f"{role}: {msg['content']}\n"

    return formatted


# --- FUNCIONES AUXILIARES PARA LA API DE CHATWOOT ---

def send_chatwoot_message(conversation_id: int, message: str):
    """Envía un mensaje de respuesta a una conversación específica en Chatwoot."""
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages"
    headers = {"api_access_token": CHATWOOT_API_TOKEN, "Content-Type": "application/json"}
    payload = {"content": message, "message_type": "outgoing"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"✅ Mensaje enviado a la conversación {conversation_id}.")
        debug(f"   💬 kittIA → cliente: {message}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al enviar mensaje a Chatwoot: {e}")


def update_chatwoot_labels(conversation_id: int, new_labels: list):
    """Actualiza las etiquetas de una conversación en Chatwoot."""
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/labels"
    headers = {"api_access_token": CHATWOOT_API_TOKEN, "Content-Type": "application/json"}
    payload = {"labels": new_labels}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"✅ Etiquetas actualizadas en la conversación {conversation_id} a: {new_labels}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al actualizar etiquetas en Chatwoot: {e}")


# --- CÓDIGO DEL WEBHOOK ---

app = FastAPI(
    title="kittIA - Asesora Educativa (Google ADK)",
    description="Bot asesor con Google Agent Development Kit (Evolution API + Chatwoot)",
)


async def preguntar_agente(conversation_id: int, texto: str, historial: list) -> str:
    user_id = session_id = str(conversation_id)
    if not await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    ):
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
    prompt = f"{format_history_for_prompt(historial)}\n\nPREGUNTA DEL CLIENTE: {texto}"
    debug(f"   🗂️ Historial enviado al agente: {len(historial)} mensajes")
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    respuesta = ""
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=msg
    ):
        if DEBUG_LOGS and event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "function_call", None):
                    fc = part.function_call
                    debug(f"   🔧 Tool llamada: {fc.name}({dict(fc.args or {})})")
                if getattr(part, "function_response", None):
                    fr = part.function_response
                    debug(f"   📦 Resultado de {fr.name}: {fr.response}", limite=400)
        if event.is_final_response() and event.content and event.content.parts:
            respuesta = event.content.parts[0].text
    return respuesta


# Palabras que indican que el cliente quiere hablar con una persona
HUMAN_HANDOFF_KEYWORDS = [
    "humano", "persona", "asesor", "agente", "representante", "alguien", "real",
]


@app.post("/webhook")
async def chatwoot_webhook(request: Request):
    data = await request.json()

    event = data.get("event")
    message_type = data.get("message_type")
    conversation = data.get("conversation") or {}
    conversation_id = conversation.get("id")
    labels = conversation.get("labels") or []
    message_content = (data.get("content") or "").strip()

    # Solo responde mensajes entrantes de conversaciones con la etiqueta 'atiende-ia'
    if event == "message_created" and message_type == "incoming" and "atiende-ia" in labels:
        if message_content and conversation_id:
            # Detectar si el usuario quiere hablar con un humano
            if any(keyword in message_content.lower() for keyword in HUMAN_HANDOFF_KEYWORDS):
                print(f"🙋 Intención de hablar con humano detectada en conversación {conversation_id}.")
                new_labels = [label for label in labels if label != "atiende-ia"]
                new_labels.append("atiende-humano")
                await asyncio.to_thread(update_chatwoot_labels, conversation_id, new_labels)
                handoff_message = (
                    f"Entendido. Un asesor humano de {EMPRESA} se pondrá en contacto contigo en breve."
                )
                await asyncio.to_thread(send_chatwoot_message, conversation_id, handoff_message)
                return {"status": "success", "action": "human_handoff"}

            # Procesar la consulta con Google ADK Agent
            print(f"🤖 kittIA (Google ADK) procesando consulta en conversación {conversation_id}...")
            print(f"📝 Pregunta del interesado: {message_content}")

            # Obtener el historial ANTES de guardar el mensaje actual (para no duplicarlo)
            historial = await asyncio.to_thread(get_conversation_history, conversation_id)
            await asyncio.to_thread(add_to_history, conversation_id, "user", message_content)

            try:
                respuesta = await preguntar_agente(conversation_id, message_content, historial)
            except Exception as e:
                # Evita el 500 (y los reintentos de Chatwoot) si falla el modelo
                print(f"❌ Error del agente en conversación {conversation_id}: {str(e)[:300]}")
                return {"status": "error", "detail": "agent_failed"}
            if not respuesta:
                print(f"⚠️ El agente no devolvió texto en la conversación {conversation_id}")
                return {"status": "error", "detail": "empty_response"}

            await asyncio.to_thread(add_to_history, conversation_id, "assistant", respuesta)
            await asyncio.to_thread(send_chatwoot_message, conversation_id, respuesta)
            return {"status": "success"}

    print(
        f"⏭️ Ignorado: event={event!r}, message_type={message_type!r}, "
        f"labels={labels}, conversation_id={conversation_id}"
    )
    return {"status": "ignored"}


# --- ENDPOINTS AUXILIARES ---------------------------------------------------
@app.get("/")
def read_root():
    """Información general del servicio."""
    return {
        "service": f"kittIA - Asesora Educativa de {EMPRESA}",
        "status": "running",
        "ai_platform": "Google ADK",
        "model": agent.model,
        "tools_count": len(agent.tools),
        "tools": ["buscar_en_base_conocimientos", "obtener_informacion_curso"],
        "vector_db": "LlamaCloud",
        "knowledge_base_ready": index_id is not None,
        "history": "Supabase" if USE_SUPABASE else "memoria",
        "agent": agent.name,
    }


@app.get("/health")
def health_check():
    """Endpoint de salud del servicio."""
    return {
        "status": "healthy",
        "company": EMPRESA,
        "ai_platform": "Google ADK",
        "model": agent.model,
        "knowledge_base_ready": index_id is not None,
        "supabase_connected": USE_SUPABASE,
        "agent": agent.name,
    }


@app.get("/stats")
def get_stats():
    """Estadísticas de la base de conocimientos y de las conversaciones."""
    stats = {
        "knowledge_base": LLAMA_CLOUD_INDEX_NAME,
        "knowledge_base_ready": index_id is not None,
        "history": "Supabase" if USE_SUPABASE else "memoria",
        "active_conversations_in_memory": len(conversation_history),
        "tools": ["buscar_en_base_conocimientos", "obtener_informacion_curso"],
    }
    if USE_SUPABASE:
        try:
            stats["conversations_in_supabase"] = len(
                supabase.table("conversation_stats").select("conversation_id").execute().data
            )
        except Exception as e:
            stats["supabase_error"] = str(e)
    return stats


@app.get("/history/{conversation_id}")
def get_history(conversation_id: int):
    """Endpoint para ver el historial de una conversación específica."""
    history = get_conversation_history(conversation_id, max_messages=100)
    return {
        "conversation_id": conversation_id,
        "message_count": len(history),
        "messages": history,
    }


@app.get("/conversations")
def get_all_conversations():
    """Lista las conversaciones con su resumen (vista conversation_stats)."""
    if USE_SUPABASE:
        try:
            data = (
                supabase.table("conversation_stats")
                .select("*")
                .order("last_message", desc=True)
                .execute()
                .data
            )
            return {"source": "supabase", "total": len(data), "conversations": data}
        except Exception as e:
            print(f"⚠️ Error al listar conversaciones de Supabase: {e}")
    return {
        "source": "memoria",
        "total": len(conversation_history),
        "conversations": [
            {"conversation_id": cid, "total_messages": len(msgs)}
            for cid, msgs in conversation_history.items()
        ],
    }


@app.post("/test")
async def test_agent(request: Request):
    """Endpoint de prueba para testear el agente directamente sin Chatwoot."""
    data = await request.json()
    query = data.get("query", "")

    if not query:
        return {"error": "Debes proporcionar un 'query' en el body"}

    print(f"\n🧪 TEST - Consulta recibida: {query}")

    try:
        # conversation_id negativo para no mezclar pruebas con conversaciones reales
        respuesta = await preguntar_agente(-1, query, [])
        return {"query": query, "response": respuesta, "status": "success"}
    except Exception as e:
        print(f"❌ Error en /test: {e}")
        return {"query": query, "error": str(e), "status": "error"}


if __name__ == "__main__":
    import uvicorn

    print()
    print("=" * 80)
    print("🚀 INICIANDO SERVIDOR - KITTIA CON GOOGLE ADK")
    print("=" * 80)
    print(f"🤖 Agente: {agent.name}")
    print(f"🧠 Modelo: {agent.model}")
    print(f"🔧 Herramientas: {len(agent.tools)} tools disponibles")
    print(f"💾 Base de conocimientos: LlamaCloud ({LLAMA_CLOUD_INDEX_NAME})")
    print(f"🗂️ Historial: {'Supabase' if USE_SUPABASE else 'memoria'}")
    print("=" * 80)
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
