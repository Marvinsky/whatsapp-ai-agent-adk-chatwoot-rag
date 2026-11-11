"""
Pipeline RAG con LlamaParse + LlamaCloud Index (API nueva).

Pasos:
  1. Subir los documentos a un directorio de LlamaCloud.
  2. Crear el índice "automations_docs_api_adk" sobre ese directorio. LlamaCloud
     hace en la nube: parseo con LlamaParse (a Markdown), troceado en chunks y
     embeddings, y guarda los vectores en su base de datos vectorial.
  3. Esperar a que el índice esté listo (status "ready").

Nota: la API nueva de Index no permite configurar chunk_size/chunk_overlap ni el
modelo de embeddings; LlamaCloud usa sus valores por defecto. Por eso este script
no necesita OPENAI_API_KEY.

Uso (desde la raíz del proyecto o desde RAG/):
    python RAG/rag_llamaparse.py
"""
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from llama_cloud import LlamaCloud

# Logging claro para ver el proceso
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))
logging.getLogger("httpx").setLevel(logging.WARNING)

# Carga las variables de entorno desde el .env en la raíz del proyecto
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

if not os.getenv("LLAMA_CLOUD_API_KEY"):
    raise ValueError("LLAMA_CLOUD_API_KEY no encontrada en el archivo .env")

# Nombre del índice (y del directorio de origen) en LlamaCloud
LLAMA_CLOUD_INDEX_NAME = "automations_docs_api_adk"

# Carpeta con los documentos a indexar
DOCS_DIR = Path(__file__).resolve().parent / "Base_de_Conocimiento_Automatizacion"
EXTS = {".pdf", ".docx", ".pptx", ".txt", ".md"}

# LlamaParse es un servicio avanzado de parsing que mejora significativamente
# la extracción de contenido de PDFs, especialmente con tablas, gráficos y layouts complejos.

logging.info("=" * 80)
logging.info("🚀 INICIANDO RAG CON LLAMAPARSE - INDEXACIÓN AVANZADA")
logging.info("=" * 80)

# ---------------- Paso 1: Configuración de LlamaParse (Parser Avanzado) ---------
# LlamaParse usa modelos de visión para entender mejor la estructura del documento
logging.info("Configurando LlamaParse...")
client = LlamaCloud(api_key=os.getenv("LLAMA_CLOUD_API_KEY"))
logging.info("✅ LlamaParse configurado correctamente (extracción en Markdown).")
# -------------------------------------------------------------------------------

# ---------------- Pasos 2 y 3: chunks y embeddings (gestionados por LlamaCloud) -
logging.info("✅ Troceado (chunks) y embeddings gestionados por LlamaCloud al crear el índice.")
# -------------------------------------------------------------------------------


def obtener_o_crear_directorio():
    """Reutiliza el directorio con el nombre del índice o lo crea."""
    for d in client.beta.directories.list(name=LLAMA_CLOUD_INDEX_NAME):
        if d.name == LLAMA_CLOUD_INDEX_NAME:
            return d
    return client.beta.directories.create(
        name=LLAMA_CLOUD_INDEX_NAME,
        description="Base de conocimiento: creación de APIs con FastAPI y Flask",
    )


def ingest_data_with_llamaparse():
    """
    Función principal que ejecuta el pipeline de ingesta usando LlamaParse.

    LlamaParse ofrece:
    - Mejor extracción de tablas y gráficos
    - Reconocimiento de estructura visual del documento
    - Preservación de jerarquía y formato
    """
    # ---------------- Paso 1: Document Loader ----------------
    logging.info(f"🔍 Buscando documentos en la carpeta '{DOCS_DIR.name}'...")

    archivos = [
        f
        for f in sorted(DOCS_DIR.iterdir())
        if f.suffix.lower() in EXTS and not f.name.upper().startswith("LEEME")
    ]
    if not archivos:
        logging.warning("⚠️ No se encontraron documentos para procesar. Finalizando.")
        return
    # ---------------------------------------------------------

    logging.info(
        f"✅ Se encontraron {len(archivos)} documentos. "
        "Iniciando el proceso de almacenamiento con LlamaCloud..."
    )
    logging.info("⏳ El procesamiento con LlamaParse puede tardar más tiempo pero ofrece mejor calidad...")

    # ---------------- Paso 2: Llevada de los documentos a LlamaCloud ----------
    logging.info("☁️ Conectando con LlamaCloud...")
    directorio = obtener_o_crear_directorio()
    logging.info(f"📁 Directorio: {directorio.name} ({directorio.id})")

    for archivo in archivos:
        # Si ya está en el directorio (misma ejecución previa), no se vuelve a subir
        if any(client.beta.directories.files.list(directorio.id, unique_id=archivo.name)):
            logging.info(f"⏭️  {archivo.name} ya está en LlamaCloud; se omite.")
            continue
        logging.info(f"⬆️  Subiendo {archivo.name}...")
        with open(archivo, "rb") as f:
            subido = client.files.create(file=f, purpose="user_data")
        client.beta.directories.files.add(
            directorio.id,
            file_id=subido.id,
            display_name=archivo.name,
            unique_id=archivo.name,  # evita duplicados si vuelves a ejecutar
        )

    # LlamaCloud Index: parsea, trocea, genera embeddings e indexa automáticamente
    existentes = [
        i
        for i in client.indexes.list(source_directory_id=directorio.id)
        if i.name == LLAMA_CLOUD_INDEX_NAME
    ]
    if existentes:
        index = existentes[0]
        logging.info(f"🔄 El índice ya existe ({index.id}); sincronizando cambios...")
        client.indexes.sync(index.id)
    else:
        index = client.indexes.create(
            source_directory_id=directorio.id,
            name=LLAMA_CLOUD_INDEX_NAME,
        )
        logging.info(f"🆕 Índice creado ({index.id})")

    # ---------------- Esperar a que el índice esté listo ----------------------
    while True:
        idx = client.indexes.get(index.id)
        estado = (idx.metadata or {}).get("status", "unknown")
        if estado == "ready":
            break
        if estado == "failed":
            raise RuntimeError(f"Falló la creación del índice: {(idx.metadata or {}).get('error_message')}")
        logging.info(f"⏳ Estado del índice: {estado} ...")
        time.sleep(3)
    # ---------------------------------------------------------------------------

    logging.info("=" * 80)
    logging.info(f"🎉 ¡ÉXITO! {len(archivos)} documentos procesados con LlamaParse")
    logging.info(f"📊 Índice: '{LLAMA_CLOUD_INDEX_NAME}' creado exitosamente en LlamaCloud")
    logging.info("=" * 80)
    logging.info("")
    logging.info("💡 VENTAJAS DE LLAMAPARSE:")
    logging.info("   ✓ Mejor extracción de tablas y datos estructurados")
    logging.info("   ✓ Reconocimiento visual de layouts complejos")
    logging.info("   ✓ Preservación de jerarquía y formato del documento")
    logging.info("   ✓ Mayor precisión en PDFs con múltiples columnas")
    logging.info("   ✓ Mejor manejo de imágenes y gráficos con texto")
    logging.info("=" * 80)

    return index


if __name__ == "__main__":
    ingest_data_with_llamaparse()
