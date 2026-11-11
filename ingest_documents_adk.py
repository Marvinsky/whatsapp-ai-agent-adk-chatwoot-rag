"""Ingesta de documentos de ./RAG a ChromaDB (parseo con LlamaCloud, embeddings de Google)."""
import hashlib
import os
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from llama_parse import LlamaParse

load_dotenv()

RAG_DIR = Path("RAG")
EXTS = {".pdf", ".docx", ".pptx", ".txt", ".md"}
CHUNK, OVERLAP = 1000, 150


def trocear(texto: str):
    paso = CHUNK - OVERLAP
    for i in range(0, len(texto), paso):
        yield texto[i : i + CHUNK]


def main():
    parser = LlamaParse(api_key=os.getenv("LLAMA_CLOUD_API_KEY"), result_type="markdown")
    client = chromadb.PersistentClient(path="chromadb_data")
    col = client.get_or_create_collection(
        "documentos",
        embedding_function=embedding_functions.GoogleGenerativeAiEmbeddingFunction(
            api_key=os.getenv("GOOGLE_API_KEY", "")
        ),
    )

    for f in sorted(RAG_DIR.iterdir()):
        if f.suffix.lower() not in EXTS:
            continue
        print(f"Procesando {f.name}...")
        if f.suffix.lower() in {".txt", ".md"}:
            texto = f.read_text(encoding="utf-8")
        else:
            texto = "\n".join(d.text for d in parser.load_data(str(f)))
        chunks = list(trocear(texto))
        ids = [hashlib.md5(f"{f.name}:{i}".encode()).hexdigest() for i in range(len(chunks))]
        col.upsert(
            ids=ids,
            documents=chunks,
            metadatas=[{"fuente": f.name, "chunk": i} for i in range(len(chunks))],
        )
        print(f"  {len(chunks)} fragmentos")
    print(f"Total en la colección: {col.count()}")


if __name__ == "__main__":
    main()
