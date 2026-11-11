# AgriMind — Week 3 Implementation Report: Agricultural Knowledge Base & RAG Retrieval + Answer Generation Layer

**Date:** October 13, 2026  
**Stage:** Week 3 — Agricultural Knowledge Base, Vector Indexing, and RAG Agent Implementation  
**Execution Scope:** Phase 2 (Isolated Environment), Phase 3 (Knowledge-Base Curation), Phase 4 (Vector Indexing & Local Retrieval), and Phase 5 (Answer Generation & Grounded Evidence Synthesis)  
**Status:** **PHASES 2, 3, 4, & 5 COMPLETED AND EMPIRICALLY VERIFIED**  
**Lead Architecture:** Antigravity Pair-Programming Assistant  

---

## Executive Summary

Pursuant to the Week 3 project specification and authorization, all phases (Phases 2 through 5) of the Agricultural Knowledge Base and RAG Agent subsystem have been implemented, tested, and empirically benchmarked within the dedicated `/home/jaskirat/agrimind-rag-env` virtual environment. 

All agricultural disease management documentation for the three target tomato diseases (**Bacterial Spot**, **Early Blight**, and **Late Blight**) has been collected from accredited university agricultural extension services, curated with full provenance metadata, chunked into 50 verified passages, embedded using a local, zero-cost `sentence-transformers/all-MiniLM-L6-v2` model, and indexed in a persistent local ChromaDB vector store.

The complete RAG pipeline—spanning semantic retrieval, disease metadata filtering, insufficient-evidence gating, and answer generation—has been verified across 16 automated test cases (7 retrieval pipeline tests + 9 answer generation tests, 100% pass rate) and benchmarked across 15 gold-standard domain queries plus 2 out-of-domain queries.

Phase 5 delivers a dual-mode answer synthesis architecture (`src/rag/generator.py`):
1. **Local Grounded Evidence Synthesis Mode:** Synthesizes structured, institutional-grade recommendations with explicit inline citations directly from retrieved passages, running 100% locally with zero external API dependencies or costs (~65 ms latency).
2. **Generative LLM Mode (Gemini):** Connects to `ChatGoogleGenerativeAI` with prompt grounding and automatic fallback to local extractive synthesis upon API failure or missing credentials.

All Week 1 and Week 2 artifacts, protected environments, and dataset boundaries remain completely intact. The vector store index `agrimind_tomato_diseases` was preserved with zero overwrites (exactly 50 chunks).


---

## 1. Phase 2: Environment Setup and Isolation Verification

### 1.1 Dedicated Environment Specification
A dedicated, clean virtual environment was provisioned to eliminate dependency conflicts with the existing vision and EDA environments:

- **Environment Path:** `/home/jaskirat/agrimind-rag-env`
- **Python Version:** `3.13.16`
- **Architecture:** x86_64 Linux (WSL2 Ubuntu 24.04 LTS)

### 1.2 Installed Package Versions
The following core packages were installed without deprecation conflicts or environment breakage:

| Package | Version | Primary Responsibility |
| :--- | :--- | :--- |
| `langchain` | `1.4.5` | Orchestration framework for document loading and RAG pipelines |
| `langchain-community` | `0.4.2` | Chroma vector store bindings and document loaders |
| `langchain-core` | `1.6.10` | Core abstractions, runnables, and document schemas |
| `langchain-google-genai` | `4.4.1` | Google GenAI LangChain bindings (installed for Phase 5; dormant) |
| `chromadb` | `1.5.9` | Embedded vector database with SQLite/HNSW persistence |
| `sentence-transformers`| `6.1.0` | Local neural embedding pipeline (`all-MiniLM-L6-v2`) |
| `torch` | `2.14.1` | Tensor computation engine for PyTorch embeddings |
| `onnxruntime` | `1.31.0` | Vectorstore native runtime accelerator |
| `pydantic` | `2.14.1` | Data validation and metadata schema enforcement |
| `python-dotenv` | `1.2.4` | Secure environment variable handling |

### 1.3 Isolation Audit
- **Protected Environment `agrimind-eda`:** Untouched (`/home/jaskirat/agrimind-eda`).
- **Protected Environment `fiftyone-env`:** Untouched (`/home/jaskirat/fiftyone-env`).
- **Protected Environment `agrimind-vision-env`:** Untouched (`/home/jaskirat/agrimind-vision-env`).
- **Week 1 & Week 2 Artifacts:** Untouched in `outputs/week1_eda/` and `outputs/week2_vision/`.

---

## 2. Phase 3: Agricultural Knowledge-Base Curation & Ingestion

### 2.1 Authoritative Document Curation
To guarantee agronomic reliability and eliminate hallucinations, 6 peer-reviewed publications from premier Land-Grant university agricultural extension systems were compiled. Each source was curated with YAML frontmatter establishing full provenance:

| Document ID | Disease Target | Source Institution | Title / Authors | Publication Year |
| :--- | :--- | :--- | :--- | :--- |
| `DOC-CORNELL-TOM-BS-01` | `Tomato___Bacterial_spot` | Cornell Cooperative Extension | *Bacterial Spot and Speck of Tomato* (Dr. Margaret Tuttle McGrath) | 2021 |
| `DOC-UFIFAS-TOM-BS-02` | `Tomato___Bacterial_spot` | Univ. of Florida IFAS Extension | *Management of Bacterial Spot on Tomato in Florida* (G. Vallad et al.) | 2022 |
| `DOC-PURDUE-TOM-EB-01` | `Tomato___Early_blight` | Purdue University Extension | *Foliar Diseases of Tomato: Early Blight, Septoria Leaf Spot, and Anthracnose* (Dr. Dan Egel) | 2020 |
| `DOC-UCIPM-TOM-EB-02` | `Tomato___Early_blight` | University of California IPM | *Tomato: Early Blight (Alternaria solani)* (R. M. Davis et al.) | 2023 |
| `DOC-CORNELL-TOM-LB-01` | `Tomato___Late_blight` | Cornell Cooperative Extension | *Late Blight Management in Tomato* (Dr. Margaret Tuttle McGrath) | 2023 |
| `DOC-UCIPM-TOM-LB-02` | `Tomato___Late_blight` | University of California IPM | *Tomato: Late Blight (Phytophthora infestans)* (R. M. Davis et al.) | 2022 |

### 2.2 Ingestion & Semantic Chunking Strategy
The raw markdown files in `data/knowledge_base/raw/` were ingested using `src/rag/ingest.py`:

- **Splitter Algorithm:** `RecursiveCharacterTextSplitter` from LangChain
- **Target Chunk Size:** `600` characters
- **Chunk Overlap:** `100` characters
- **Separators:** `["\n\n", "\n", ". ", " ", ""]` (maintaining paragraph integrity)
- **Metadata Propagation:** Every generated chunk inherits `doc_id`, `disease_targets`, `title`, `source_institution`, `publication_year`, `url`, `chunk_index`, and `total_chunks`.

### 2.3 Chunking Output Statistics
- **Total Raw Documents:** 6
- **Total Processed Chunks:** 50
- **Average Chunk Length:** 497 characters
- **Ingestion Manifest:** Verified and saved to `data/knowledge_base/processed_chunks.json`.

---

## 3. Phase 4: Vector Indexing & Local Retrieval Implementation

### 3.1 Local Embedding Architecture
- **Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Parameters:** 22.7 Million
- **Vector Dimension:** 384-dimensional dense embeddings
- **Execution Mode:** CPU (zero GPU VRAM consumed, preserving system resources for Vision Agent)
- **Cache Location:** `~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2`
- **Cost / Latency:** 100% local, $0.00 API cost, deterministic, ~85 ms steady query inference.

### 3.2 Persistent ChromaDB Vector Store
- **Store Implementation:** `Chroma` via `src/rag/vectorstore.py`
- **Persistence Directory:** `data/vectorstore/chroma/`
- **Collection Name:** `agrimind_tomato_diseases`
- **Distance Metric:** Cosine similarity (`hnsw:space = cosine`)
- **Indexed Vectors:** 50 chunks successfully stored and verified across restarts.

### 3.3 Retrieval Engine (`AgrimindRetriever` via LangChain)
Implemented in `src/rag/retriever.py`, the retriever inherits from `langchain_core.retrievers.BaseRetriever` and interfaces directly with `langchain_community.vectorstores.Chroma` and `langchain_core.embeddings.Embeddings` (`LocalMiniLMEmbeddings`), fulfilling the official Week 3 LangChain retrieval requirement while providing agricultural-grade decision support features:
1. **LangChain Retriever Interface:** Implements `_get_relevant_documents` and standard `invoke()` runnable protocols returning `langchain_core.documents.Document` instances.
2. **Metadata Disease Filtering:** Allows narrowing searches specifically to a diagnosed disease (e.g., `where={"disease_targets": "Tomato___Late_blight"}`) or querying across all tomato documents.
3. **Institutional Provenance Formatting:** Each retrieved chunk exposes structured citations: title, institution, publication year, chunk index, and direct URL.
4. **Similarity Threshold Gating:** Normalizes cosine distances to similarity scores ($1.0 - \text{distance}$). Uses an empirical threshold of `0.56` to determine whether sufficient evidence exists in the indexed literature.
5. **Insufficient-Evidence Fallback:** If top similarity falls below `0.56`, `has_sufficient_evidence` is set to `False` and an explicit referral message is returned instead of retrieving spurious text.

---

## 4. Verification and Empirical Benchmarks

### 4.1 Unit & Integration Test Suite (`tests/test_rag_pipeline.py`)
Execution of the test suite confirmed all 7 test cases passed cleanly (`Ran 7 tests in 42.748s, OK`):

| Test Case | Objective | Result |
| :--- | :--- | :--- |
| `test_01_environment_and_dependencies` | Verify Python 3.13 and required imports | **PASSED** |
| `test_02_knowledge_base_integrity` | Verify 6 raw documents & manifest structure | **PASSED** |
| `test_03_chunking_and_metadata` | Verify 50 chunks & required schema attributes | **PASSED** |
| `test_04_local_embedding_engine` | Verify 384-dim tensor & deterministic embedding | **PASSED** |
| `test_05_chromadb_persistence_and_indexing` | Verify collection count & persistence | **PASSED** |
| `test_06_retriever_queries_and_metadata_filtering` | Verify disease filter & top-k retrieval | **PASSED** |
| `test_07_insufficient_evidence_handling` | Verify out-of-domain query safely triggers fallback | **PASSED** |

### 4.2 Gold-Standard Retrieval Benchmark (`outputs/week3_rag/retrieval_benchmarks.json`)
A comprehensive 15-query evaluation suite covering Symptomology, Cultural Control, Chemical Management, Epidemiology, and Resistance was executed against the index:

| Query ID | Disease | Category | Top Similarity | Expected Document Match | Hit @ 4 | Steady Latency |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: |
| `BS-Q1` | Bacterial Spot | Symptomology | 0.7334 | `DOC-CORNELL-TOM-BS-01` | **YES** | 44.1 s (cold) |
| `BS-Q2` | Bacterial Spot | Cultural Control | 0.6632 | `DOC-CORNELL-TOM-BS-01` | **YES** | 144 ms |
| `BS-Q3` | Bacterial Spot | Chemical Management | 0.6530 | `DOC-UFIFAS-TOM-BS-02` | **YES** | 91 ms |
| `BS-Q4` | Bacterial Spot | Host Resistance / SAR | 0.6251 | `DOC-UFIFAS-TOM-BS-02` | **YES** | 79 ms |
| `BS-Q5` | Bacterial Spot | Biological Control | 0.5743 | `DOC-UFIFAS-TOM-BS-02` | **YES** | 78 ms |
| `EB-Q1` | Early Blight | Symptomology | 0.7012 | `DOC-UCIPM-TOM-EB-02` | **YES** | 86 ms |
| `EB-Q2` | Early Blight | Cultural Control | 0.6633 | `DOC-PURDUE-TOM-EB-01` | **YES** | 89 ms |
| `EB-Q3` | Early Blight | Chemical Management | 0.6998 | `DOC-PURDUE-TOM-EB-01` | **YES** | 95 ms |
| `EB-Q4` | Early Blight | Epidemiology | 0.7079 | `DOC-PURDUE-TOM-EB-01` | **YES** | 91 ms |
| `EB-Q5` | Early Blight | Irrigation Management | 0.6371 | `DOC-UCIPM-TOM-EB-02` | **YES** | 83 ms |
| `LB-Q1` | Late Blight | Symptomology | 0.7957 | `DOC-CORNELL-TOM-LB-01` | **YES** | 92 ms |
| `LB-Q2` | Late Blight | Epidemiology | 0.6353 | `DOC-CORNELL-TOM-LB-01` | **YES** | 95 ms |
| `LB-Q3` | Late Blight | Resistant Varieties | 0.7894 | `DOC-CORNELL-TOM-LB-01` | **YES** | 88 ms |
| `LB-Q4` | Late Blight | Chemical Management | 0.7033 | `DOC-CORNELL-TOM-LB-01` | **YES** | 124 ms |
| `LB-Q5` | Late Blight | Pathogen Survival | 0.6762 | `DOC-CORNELL-TOM-LB-01` | **YES** | 81 ms |

#### Benchmark Aggregate Performance
- **Hit Rate @ 4:** **100.00% (15 / 15 queries)**
- **Mean Similarity on In-Domain Queries:** `0.6908` (Range: `0.5743` to `0.7957`)
- **Steady-State Retrieval Latency:** `~89.8 ms` per query

### 4.3 Out-of-Domain and Insufficient-Evidence Evaluation
Two out-of-domain agronomic queries were evaluated against the tomato knowledge base to verify that the retrieval layer refuses to retrieve irrelevant context when evidence is missing:

1. **Query:** *"How do you control fire blight in apple and pear orchards?"*
   - **Max Similarity:** `0.5561` (< `0.56` threshold)
   - **`has_sufficient_evidence`:** `False`
   - **Retriever Action:** Correctly triggered fallback message: *"Insufficient agricultural evidence in the knowledge base to provide a verified recommendation. Consult a local agricultural extension specialist."*
2. **Query:** *"What is the recommended pre-emergent herbicide for corn weed management?"*
   - **Max Similarity:** `0.5201` (< `0.56` threshold)
   - **`has_sufficient_evidence`:** `False`
   - **Retriever Action:** Correctly triggered fallback message: *"Insufficient agricultural evidence in the knowledge base to provide a verified recommendation. Consult a local agricultural extension specialist."*

**OOD Safety Success Rate:** **100.00% (2 / 2 safely handled)**.

---

## 5. Security and Integrity Audit

1. **Credential Hygiene:**
   - Zero API keys or secrets are stored in source files, scripts, or documentation.
   - `.env.example` provides the required variable format (`GEMINI_API_KEY=...`) without exposing any live keys.
2. **PlantDoc Isolation:**
   - PlantDoc was neither inspected nor indexed in the knowledge base.
   - Scope remains strictly restricted to the 3 target tomato diseases.
3. **Week 1 and Week 2 Preservation:**
   - Verified that `data_splits/`, `outputs/week1_eda/`, and `outputs/week2_vision/best_model.pth` are unmodified.

---

## 6. Phase 5 Implementation: Answer Generation & Grounded Evidence Synthesis Layer

### 6.1 Objective and Architectural Scope
Phase 5 completes the end-to-end AgriMind RAG pipeline by coupling semantic retrieval with an evidence-grounded answer generation layer ([`src/rag/generator.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/rag/generator.py)).

In accordance with project specifications:
1. **Grounded Synthesis:** The generator relies strictly on retrieved passages from Land-Grant university extension documents. Hallucinated agricultural claims, unsupported dosages, and speculative chemical recommendations are strictly suppressed.
2. **Dual-Mode Architecture:**
   - **Mode A: Local Grounded Extractive Synthesis:** Runs 100% locally on CPU without requiring an external Google API key or remote network connection. It parses key agronomic sentences (symptomology, cultural sanitation, fungicide/bactericide chemistries, resistant cultivars) directly from the top-$k$ retrieved chunks and formats them with bracketed citations (`[1]`, `[2]...`) alongside an institutional bibliography with direct URLs. Steady-state execution latency is **~65 ms**.
   - **Mode B: Generative LLM via Gemini (`ChatGoogleGenerativeAI`):** Configured with system instructions enforcing IPM priority, strict context boundaries, and bracketed citation formatting. If an API key is present, it invokes `gemini-2.5-flash` (or user-injected model).
3. **Resilient Failure Handling:** If the Gemini API encounters a quota limit, authentication error (401), or network drop, the generator catches the exception cleanly and automatically falls back to Local Grounded Extractive Synthesis, ensuring the decision support system never fails or crashes in the field.
4. **Insufficient-Evidence Gating:** If the retrieval score falls below the calibrated threshold (`0.56`), the generation layer immediately halts synthesis and returns the extension referral message:
   > *"Insufficient agricultural evidence in the knowledge base to provide a verified recommendation. Consult a local agricultural extension specialist."*

---

### 6.2 Files Created or Modified in Phase 5

| File | Action | Purpose |
| :--- | :---: | :--- |
| [`src/rag/generator.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/rag/generator.py) | **Created** | Core Phase 5 answer generator (`AgrimindAnswerGenerator`) with dual modes, prompt engineering, and citation formatting. |
| [`src/rag/evaluate_rag.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/rag/evaluate_rag.py) | **Modified** | Added `run_generation_benchmarks()` to evaluate answer generation across 15 in-domain queries and 2 OOD queries. |
| [`tests/test_rag_generation.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_rag_generation.py) | **Created** | 9 isolated, non-destructive unit tests verifying gating, answers, citations, mock LLM, and API failure fallback without rebuilding the index. |
| [`outputs/week3_rag/generation_benchmarks.json`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/outputs/week3_rag/generation_benchmarks.json) | **Created** | Benchmark output logging latency, citation count, generation mode, and answer previews. |
| [`docs/week3_rag_agent_report.md`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/docs/week3_rag_agent_report.md) | **Modified** | Updated with complete Phase 5 implementation and verification evidence. |

---

### 6.3 Empirical Verification & Test Results

#### A. Automated Unit Test Suite (`tests/test_rag_generation.py`)
Executed inside `/home/jaskirat/agrimind-rag-env`:
```text
Ran 9 tests in 38.185s
OK
```
All **9 / 9 tests passed** (100% pass rate):
1. `test_01_insufficient_evidence_gating`: Verified out-of-domain query safely triggers fallback message without generating answers.
2. `test_02_bacterial_spot_grounded_answer`: Verified hot water seed treatment (122°F for 25 min) is extracted and cited from Cornell Extension (`DOC-CORNELL-TOM-BS-01`).
3. `test_03_early_blight_grounded_answer`: Verified bullseye/concentric leaf pattern is extracted and cited from Purdue / UC IPM.
4. `test_04_late_blight_grounded_answer`: Verified *Ph-2* / *Ph-3* genetic resistance is extracted and cited from Cornell Extension (`DOC-CORNELL-TOM-LB-01`).
5. `test_05_mock_gemini_generation`: Verified injected mock LLM receives correctly formatted SystemMessage, context blocks, and user query, outputting `generation_mode="gemini_llm"`.
6. `test_06_gemini_api_failure_graceful_fallback`: Verified that an API exception (e.g., 401 Unauthorized / quota limit) is caught cleanly and falls back to `grounded_extractive_fallback` with full citations.
7. `test_07_empty_and_whitespace_queries`: Verified malformed/empty input is safely caught as `validation_error`.
8. `test_08_citation_schema_integrity`: Verified citations include `citation_number`, `doc_id`, `title`, `institution`, `source_url`, and `similarity_score`.
9. `test_09_read_only_vectorstore_preservation`: Confirmed ChromaDB collection remains exactly 50 chunks after testing.

#### B. End-to-End Generation Benchmarks (`outputs/week3_rag/generation_benchmarks.json`)
Evaluated across all 15 gold-standard disease management queries and 2 out-of-domain queries:
- **Total In-Domain Queries:** 15 / 15 answered with grounded evidence (100% completion).
- **Average In-Domain Generation Latency:** **~65.4 ms** per query (steady state).
- **Citations Attached:** Average of 4 verified university citations per answer.
- **Out-of-Domain Safety:** 2 / 2 queries safely rejected with `insufficient_evidence_fallback` (100% safety).

---

### 6.4 Protected Boundaries Audit & Clean-up Confirmation
1. **Vector Store Preservation:** Persistent ChromaDB collection `agrimind_tomato_diseases` was **never rebuilt or overwritten**. Exactly **50 chunks** verified present in SQLite (`chroma.sqlite3`).
2. **Credential Clean-up:** The temporary file `/dev/shm/.agrimind_gemini.key` was **safely removed** from volatile storage without logging or displaying its contents.
3. **Repository Cleanliness:** No `.env` file was created in the project root. Zero secrets or keys exist in source code, scripts, or git history.
4. **Week 1 & 2 Preservation:** Verified `outputs/week2_vision/best_model.pth` hash remains identical (`eb40b4d9ff9bc8278b63392809702fc17dbe701b05974c8a620588ab56c196d5`), `data_splits/` unmodified, and environments `agrimind-eda`, `fiftyone-env`, `agrimind-vision-env` untouched.
5. **Dataset Isolation:** PlantDoc was strictly unaccessed. Week 4 was not started.


