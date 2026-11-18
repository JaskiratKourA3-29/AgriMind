"""
ChromaDB Vector Store Interface for AgriMind RAG Agent.
Supports persistent local storage for development and in-memory EphemeralClient
for Vercel serverless environments with read-only filesystems.
"""
import os
import json
import logging
import shutil
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_CHROMA_DIR = os.path.join(WORKSPACE_DIR, "data", "vectorstore", "chroma")
PROCESSED_CHUNKS_PATH = os.path.join(WORKSPACE_DIR, "data", "knowledge_base", "processed_chunks.json")
COLLECTION_NAME = "agrimind_tomato_diseases"

# Module-level client and vectorstore singletons for memory reuse across serverless requests
_GLOBAL_CHROMA_CLIENT = None
_GLOBAL_LANGCHAIN_STORE = None


def is_serverless_env() -> bool:
    """Detects whether code is running inside a serverless / read-only environment like Vercel."""
    return (
        os.environ.get("VERCEL") == "1"
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
        or os.environ.get("CHROMA_EPHEMERAL", "false").lower() in ("true", "1")
    )


def get_chroma_client(persist_directory: str = DEFAULT_CHROMA_DIR):
    """
    Initializes a ChromaDB client.
    Uses EphemeralClient in serverless/read-only environments or falls back
    if PersistentClient cannot obtain a write lock.
    """
    global _GLOBAL_CHROMA_CLIENT
    if _GLOBAL_CHROMA_CLIENT is not None:
        return _GLOBAL_CHROMA_CLIENT

    import chromadb

    if is_serverless_env():
        logger.info("[ChromaDB] Initializing EphemeralClient for serverless runtime.")
        _GLOBAL_CHROMA_CLIENT = chromadb.EphemeralClient()
        return _GLOBAL_CHROMA_CLIENT

    try:
        os.makedirs(persist_directory, exist_ok=True)
        client = chromadb.PersistentClient(path=persist_directory)
        _GLOBAL_CHROMA_CLIENT = client
        return client
    except Exception as e:
        logger.warning(f"[ChromaDB] PersistentClient failed ({e}). Falling back to EphemeralClient.")
        _GLOBAL_CHROMA_CLIENT = chromadb.EphemeralClient()
        return _GLOBAL_CHROMA_CLIENT


def load_knowledge_base_chunks() -> List[Dict[str, Any]]:
    """Loads the 63 verified tomato disease chunks from disk."""
    if not os.path.exists(PROCESSED_CHUNKS_PATH):
        logger.warning(f"[ChromaDB] Knowledge base chunks not found at: {PROCESSED_CHUNKS_PATH}")
        return []
    try:
        with open(PROCESSED_CHUNKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[ChromaDB] Error reading knowledge base chunks: {e}")
        return []


def ensure_collection_populated(
    client,
    collection_name: str = COLLECTION_NAME,
    embeddings_model=None
) -> Any:
    """
    Ensures that the ChromaDB collection contains the knowledge-base documents.
    If the collection is empty (e.g. in EphemeralClient on cold start), populates it.
    """
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "AgriMind Tomato Diseases Knowledge Base", "hnsw:space": "cosine"}
    )

    if collection.count() == 0:
        chunks = load_knowledge_base_chunks()
        if chunks:
            from src.rag.embeddings import LocalMiniLMEmbeddings
            emb = embeddings_model or LocalMiniLMEmbeddings()
            ids = [chunk["chunk_id"] for chunk in chunks]
            texts = [chunk["text"] for chunk in chunks]
            metadatas = [chunk["metadata"] for chunk in chunks]

            logger.info(f"[ChromaDB] Ingesting {len(texts)} chunks into collection '{collection_name}'...")
            embeddings = emb.embed_documents(texts)
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            logger.info(f"[ChromaDB] Successfully populated collection '{collection_name}' ({collection.count()} chunks).")
    return collection


def build_or_update_vectorstore(
    chunks: List[Dict[str, Any]],
    embeddings_model,
    persist_directory: str = DEFAULT_CHROMA_DIR,
    collection_name: str = COLLECTION_NAME,
    force_rebuild: bool = False
) -> Dict[str, Any]:
    """
    Populates ChromaDB with processed document chunks and their embeddings.
    If force_rebuild is True, clears existing collection to prevent duplication.
    """
    client = get_chroma_client(persist_directory)

    if force_rebuild:
        try:
            client.delete_collection(name=collection_name)
            logger.info(f"Deleted existing collection '{collection_name}' for clean rebuild.")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "AgriMind Tomato Diseases Knowledge Base", "hnsw:space": "cosine"}
    )

    existing_count = collection.count()
    if existing_count > 0 and not force_rebuild:
        logger.info(f"Collection '{collection_name}' already contains {existing_count} chunks. Skipping re-indexing.")
        return {
            "collection_name": collection_name,
            "total_chunks": existing_count,
            "status": "loaded_existing"
        }

    ids = [chunk["chunk_id"] for chunk in chunks]
    texts = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]

    logger.info(f"Generating embeddings for {len(texts)} chunks...")
    embeddings = embeddings_model.embed_documents(texts)

    logger.info(f"Inserting {len(chunks)} chunks into ChromaDB collection '{collection_name}'...")
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        end = min(i + batch_size, len(ids))
        collection.add(
            ids=ids[i:end],
            embeddings=embeddings[i:end],
            documents=texts[i:end],
            metadatas=metadatas[i:end]
        )

    final_count = collection.count()
    logger.info(f"Vector store populated successfully. Total indexed chunks: {final_count}")
    return {
        "collection_name": collection_name,
        "total_chunks": final_count,
        "status": "built_fresh",
        "persist_directory": persist_directory
    }


def get_langchain_vectorstore(
    embeddings_model=None,
    persist_directory: str = DEFAULT_CHROMA_DIR,
    collection_name: str = COLLECTION_NAME
):
    """
    Initializes a LangChain Chroma vector store instance wrapping either
    the in-memory client (serverless) or the persistent directory.
    """
    global _GLOBAL_LANGCHAIN_STORE
    if _GLOBAL_LANGCHAIN_STORE is not None:
        return _GLOBAL_LANGCHAIN_STORE

    from langchain_community.vectorstores import Chroma
    from src.rag.embeddings import LocalMiniLMEmbeddings

    emb = embeddings_model or LocalMiniLMEmbeddings()
    client = get_chroma_client(persist_directory)
    ensure_collection_populated(client, collection_name=collection_name, embeddings_model=emb)

    # In serverless or ephemeral mode, wrap the client directly
    if is_serverless_env() or isinstance(client, getattr(__import__("chromadb"), "EphemeralClient", type(None))):
        store = Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=emb
        )
    else:
        store = Chroma(
            collection_name=collection_name,
            persist_directory=persist_directory,
            embedding_function=emb
        )

    _GLOBAL_LANGCHAIN_STORE = store
    return store


def query_vectorstore(
    query_text: str,
    embeddings_model,
    n_results: int = 4,
    where_filter: Optional[Dict[str, Any]] = None,
    persist_directory: str = DEFAULT_CHROMA_DIR,
    collection_name: str = COLLECTION_NAME
) -> Dict[str, Any]:
    """
    Queries the Chroma collection using LangChain vector store interface.
    """
    lc_store = get_langchain_vectorstore(
        embeddings_model=embeddings_model,
        persist_directory=persist_directory,
        collection_name=collection_name
    )

    docs_and_scores = lc_store.similarity_search_with_relevance_scores(
        query=query_text,
        k=n_results,
        filter=where_filter
    )

    parsed_results = []
    for doc, sim in docs_and_scores:
        dist = max(0.0, 1.0 - sim)
        parsed_results.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "distance": round(dist, 4),
            "similarity_score": round(sim, 4)
        })

    return {
        "query": query_text,
        "results": parsed_results,
        "count": len(parsed_results)
    }


def get_collection_stats(
    persist_directory: str = DEFAULT_CHROMA_DIR,
    collection_name: str = COLLECTION_NAME
) -> Dict[str, Any]:
    """
    Inspects collection statistics.
    """
    client = get_chroma_client(persist_directory)
    try:
        collection = client.get_collection(name=collection_name)
        return {
            "collection_name": collection_name,
            "total_chunks": collection.count(),
            "exists": True
        }
    except Exception as e:
        return {
            "collection_name": collection_name,
            "total_chunks": 0,
            "exists": False,
            "error": str(e)
        }
