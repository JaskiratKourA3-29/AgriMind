"""
Persistent ChromaDB Vector Store Interface for AgriMind RAG Agent.
"""
import os
import shutil
from typing import List, Dict, Any, Optional

DEFAULT_CHROMA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "vectorstore", "chroma"
)
COLLECTION_NAME = "agrimind_tomato_diseases"

def get_chroma_client(persist_directory: str = DEFAULT_CHROMA_DIR):
    """
    Initializes a persistent ChromaDB client pointing to local directory.
    """
    import chromadb
    os.makedirs(persist_directory, exist_ok=True)
    return chromadb.PersistentClient(path=persist_directory)

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
    import chromadb
    client = get_chroma_client(persist_directory)

    if force_rebuild:
        try:
            client.delete_collection(name=collection_name)
            print(f"Deleted existing collection '{collection_name}' for clean rebuild.")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "AgriMind Tomato Diseases Knowledge Base", "hnsw:space": "cosine"}
    )

    existing_count = collection.count()
    if existing_count > 0 and not force_rebuild:
        print(f"Collection '{collection_name}' already contains {existing_count} chunks. Skipping re-indexing.")
        return {
            "collection_name": collection_name,
            "total_chunks": existing_count,
            "status": "loaded_existing"
        }

    ids = [chunk["chunk_id"] for chunk in chunks]
    texts = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]

    print(f"Generating embeddings for {len(texts)} chunks...")
    embeddings = embeddings_model.embed_documents(texts)

    print(f"Inserting {len(chunks)} chunks into ChromaDB collection '{collection_name}'...")
    # Insert in batches of 100 for stability
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
    print(f"Vector store populated successfully. Total indexed chunks: {final_count}")
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
    Initializes a LangChain Chroma vector store instance wrapping the persistent index.
    """
    from langchain_community.vectorstores import Chroma
    from src.rag.embeddings import LocalMiniLMEmbeddings

    emb = embeddings_model or LocalMiniLMEmbeddings()
    return Chroma(
        collection_name=collection_name,
        persist_directory=persist_directory,
        embedding_function=emb
    )

def query_vectorstore(
    query_text: str,
    embeddings_model,
    n_results: int = 4,
    where_filter: Optional[Dict[str, Any]] = None,
    persist_directory: str = DEFAULT_CHROMA_DIR,
    collection_name: str = COLLECTION_NAME
) -> Dict[str, Any]:
    """
    Queries the persistent Chroma collection using LangChain vector store interface.
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
