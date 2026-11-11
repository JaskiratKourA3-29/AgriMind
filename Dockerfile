# AgriMind Production Container
FROM python:3.11-slim

# Prevent Python from writing .pyc files & enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install system dependencies (curl for healthcheck and model download, ca-certificates for TLS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU first to avoid heavy GPU packages (exact pinned versions for reproducibility)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.6.0+cpu torchvision==0.21.0+cpu --index-url https://download.pytorch.org/whl/cpu

# Install application dependencies
COPY requirements-prod.txt /app/
# Remove the extra-index-url and torch lines since PyTorch CPU is already installed
RUN sed -i '/torch/d' requirements-prod.txt && \
    sed -i '/--extra-index-url/d' requirements-prod.txt && \
    pip install --no-cache-dir -r requirements-prod.txt

# Copy application source code and knowledge-base data
COPY src/ /app/src/
COPY data/knowledge_base/ /app/data/knowledge_base/

# Ingest and pre-build ChromaDB vectorstore at build time
RUN python -c "\
import json; \
from src.rag.vectorstore import build_or_update_vectorstore, DEFAULT_CHROMA_DIR, COLLECTION_NAME; \
from src.rag.embeddings import LocalMiniLMEmbeddings; \
chunks = json.load(open('data/knowledge_base/processed_chunks.json', encoding='utf-8')); \
build_or_update_vectorstore(chunks=chunks, embeddings_model=LocalMiniLMEmbeddings(), persist_directory=DEFAULT_CHROMA_DIR, collection_name=COLLECTION_NAME, force_rebuild=True)"

# Copy and prepare entrypoint script
COPY scripts/entrypoint.sh /app/scripts/entrypoint.sh
RUN chmod +x /app/scripts/entrypoint.sh

# Healthcheck targeting Uvicorn on dynamic PORT
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

EXPOSE 8000

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
