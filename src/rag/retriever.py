"""
Retriever and evidence assembly module for AgriMind RAG Agent.
Handles metadata-filtered retrieval, citation formatting, and insufficient evidence detection using LangChain.
"""
from typing import Dict, Any, List, Optional
from pydantic import ConfigDict
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from src.rag.vectorstore import (
    get_langchain_vectorstore,
    DEFAULT_CHROMA_DIR,
    COLLECTION_NAME
)
from src.rag.embeddings import LocalMiniLMEmbeddings

INSUFFICIENT_EVIDENCE_FALLBACK = (
    "Insufficient agricultural evidence in the knowledge base to provide a verified recommendation. "
    "Consult a local agricultural extension specialist."
)

class AgrimindRetriever(BaseRetriever):
    """
    LangChain BaseRetriever for tomato disease management documents.
    Supports metadata filtering, calibrated similarity gating, and institutional citation formatting.
    """
    embeddings_model: Any = None
    persist_directory: str = DEFAULT_CHROMA_DIR
    collection_name: str = COLLECTION_NAME
    score_threshold: float = 0.55
    anchored_score_threshold: float = 0.30
    disease_target: Optional[str] = None
    top_k: int = 4
    vectorstore: Any = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self,
        embeddings_model=None,
        persist_directory: str = DEFAULT_CHROMA_DIR,
        collection_name: str = COLLECTION_NAME,
        score_threshold: float = 0.56,
        anchored_score_threshold: float = 0.30,
        disease_target: Optional[str] = None,
        top_k: int = 4,
        **kwargs
    ):
        emb = embeddings_model or LocalMiniLMEmbeddings()
        super().__init__(
            embeddings_model=emb,
            persist_directory=persist_directory,
            collection_name=collection_name,
            score_threshold=score_threshold,
            anchored_score_threshold=anchored_score_threshold,
            disease_target=disease_target,
            top_k=top_k,
            **kwargs
        )
        if self.vectorstore is None:
            self.vectorstore = get_langchain_vectorstore(
                embeddings_model=self.embeddings_model,
                persist_directory=self.persist_directory,
                collection_name=self.collection_name
            )

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None
    ) -> List[Document]:
        """
        LangChain standard retriever implementation.
        Retrieves relevant Document instances meeting the score threshold.
        """
        where_filter = None
        if self.disease_target:
            where_filter = {"disease_targets": self.disease_target}

        docs_and_scores = self.vectorstore.similarity_search_with_relevance_scores(
            query=query,
            k=self.top_k,
            filter=where_filter
        )

        relevant_docs = []
        for doc, score in docs_and_scores:
            if score >= self.score_threshold:
                doc.metadata["similarity_score"] = round(score, 4)
                relevant_docs.append(doc)
        return relevant_docs

    def retrieve(
        self,
        query: str,
        disease_target: Optional[str] = None,
        top_k: int = 4
    ) -> Dict[str, Any]:
        """
        Retrieves top_k relevant chunks for a query using LangChain vectorstore.
        If disease_target is specified, applies a metadata filter to prevent cross-disease leakage.
        """
        where_filter = None
        target = disease_target or self.disease_target
        if target:
            where_filter = {"disease_targets": target}

        docs_and_scores = self.vectorstore.similarity_search_with_relevance_scores(
            query=query,
            k=top_k,
            filter=where_filter
        )

        results = []
        for doc, score in docs_and_scores:
            dist = max(0.0, 1.0 - score)
            results.append({
                "text": doc.page_content,
                "metadata": doc.metadata,
                "distance": round(dist, 4),
                "similarity_score": round(score, 4)
            })

        # Check evidence sufficiency based on similarity score threshold
        has_sufficient_evidence = False
        if results:
            max_score = max(r["similarity_score"] for r in results)
            threshold = self.anchored_score_threshold if target else self.score_threshold
            if max_score >= threshold:
                has_sufficient_evidence = True

        # Assemble formatted context with explicit institutional citations
        formatted_context_blocks = []
        citations = []

        if has_sufficient_evidence:
            for idx, item in enumerate(results, start=1):
                meta = item["metadata"]
                doc_id = meta.get("doc_id", "UNKNOWN")
                title = meta.get("title", "")
                inst = meta.get("institution", "")
                url = meta.get("source_url", "")
                chunk_id = meta.get("chunk_id", "")
                sim = item["similarity_score"]

                citation_header = f"[{idx}] Source: {title} | Institution: {inst} | Doc ID: {doc_id} | Chunk: {chunk_id} | Similarity: {sim:.4f} | URL: {url}"
                formatted_context_blocks.append(f"{citation_header}\n{item['text']}")
                
                citations.append({
                    "citation_number": idx,
                    "doc_id": doc_id,
                    "title": title,
                    "institution": inst,
                    "source_url": url,
                    "chunk_id": chunk_id,
                    "similarity_score": sim
                })

            formatted_context = "\n\n---\n\n".join(formatted_context_blocks)
            fallback_text = None
        else:
            formatted_context = ""
            fallback_text = INSUFFICIENT_EVIDENCE_FALLBACK

        return {
            "query": query,
            "disease_target": target,
            "has_sufficient_evidence": has_sufficient_evidence,
            "retrieved_count": len(results),
            "results": results,
            "citations": citations,
            "context_text": formatted_context,
            "fallback_message": fallback_text
        }
