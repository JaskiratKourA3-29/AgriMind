# AgriMind Stage B.6 — Root Cause Analysis: Evidence-Grounded Conversational QA Failure

## 1. Executive Summary

During manual evaluation of the AgriMind Stage B.5 conversational endpoint, the query:
> *"how can i grow tomato healthy"*

resulted in the following evidence-gating response:
> *"Insufficient agricultural evidence in the knowledge base to provide a verified recommendation. Consult a local agricultural extension specialist."*

This read-only diagnostic investigation evaluates the root cause across the retrieval pipeline, vector store metadata, similarity score distributions, and document coverage.

---

## 2. Empirical Investigation & Measured Scores

A diagnostic script was executed against the active ChromaDB vector collection (`agrimind_tomato_diseases`) using the local `sentence-transformers/all-MiniLM-L6-v2` embedding model.

### 2.1 Measured Similarity Results

| Test Query | Target Disease Filter | Top-1 Score | Top-1 Matched Document & Chunk | Gating Status (`threshold = 0.56`) |
| :--- | :--- | :--- | :--- | :--- |
| `"how can i grow tomato healthy"` | `None` (Global) | **0.5238** | `DOC-UCIPM-TOM-LB-02-C006` (Late Blight Cultural Management) | **REJECTED (Insufficient Evidence)** |
| `"How to control Early Blight?"` | `None` (Global) | **0.6406** | `DOC-UCIPM-TOM-EB-02-C001` (Early Blight Overview) | **ACCEPTED (Sufficient Evidence)** |
| `"Late Blight fungicide recommendations"` | `None` (Global) | **0.7099** | `DOC-CORNELL-TOM-LB-01-C007` (Late Blight Fungicides) | **ACCEPTED (Sufficient Evidence)** |
| `"tomato watering and soil care"` | `None` (Global) | **0.6627** | `DOC-CORNELL-TOM-BS-01-C007` (Bacterial Spot Irrigation) | **ACCEPTED (Sufficient Evidence)** |

---

## 3. Verified Root Causes

### Root Cause 1: Incomplete Knowledge Base Coverage for General Tomato Agronomy
- **Verification**: Inspected `data/knowledge_base/metadata_manifest.json` and `data/knowledge_base/raw/`.
- **Finding**: The knowledge base contains exactly **6 documents** totaling **50 chunks**. Every document targets one of three specific tomato diseases:
  1. `DOC-CORNELL-TOM-BS-01` (`Tomato___Bacterial_spot`)
  2. `DOC-UFIFAS-TOM-BS-02` (`Tomato___Bacterial_spot`)
  3. `DOC-PURDUE-TOM-EB-01` (`Tomato___Early_blight`)
  4. `DOC-UCIPM-TOM-EB-02` (`Tomato___Early_blight`)
  5. `DOC-CORNELL-TOM-LB-01` (`Tomato___Late_blight`)
  6. `DOC-UCIPM-TOM-LB-02` (`Tomato___Late_blight`)
- **Conclusion**: There is zero extension literature covering general tomato cultural practices, soil preparation, spacing, staking, fertilization, or baseline plant health.

### Root Cause 2: Calibrated Evidence-Gating Threshold Operation
- **Verification**: Inspected `src/rag/retriever.py` lines 30 and 122–128:
  ```python
  score_threshold: float = 0.56
  # ...
  max_score = max(r["similarity_score"] for r in results)
  if max_score >= self.score_threshold:
      has_sufficient_evidence = True
  ```
- **Finding**: For `"how can i grow tomato healthy"`, the highest cosine similarity against the disease-specific chunks was **0.5238** (< 0.56).
- **Conclusion**: The similarity threshold correctly prevented hallucination on out-of-scope material. Lowering the threshold blindly would force false matches against irrelevant fungicide spray schedules. The correct remedy is traceably ingesting authoritative general tomato cultural management literature.

### Root Cause 3: Single-Turn Retrieval on Conversational Queries (Lack of Anaphora Resolution)
- **Verification**: Inspected `src/api/routes.py` lines 580–587.
- **Finding**: The `/chat` route executed retrieval directly on `request.query`. If a user asked a follow-up such as *"Can it infect the fruit?"* or *"How often should I spray this?"*, vector search failed because the pathogen name was missing from the raw query string.
- **Conclusion**: A safe, deterministic query referent resolution mechanism is required to resolve pronouns from recent conversation history and active case context before retrieval.

---

## 4. Remediation Plan

1. **Traceable Extension Literature Ingestion**:
   - Ingest an accredited university extension publication on **General Tomato Cultural Management and Plant Health** (Cornell University Cooperative Extension / Ohio State University Extension).
   - Document metadata: title, author, institution, publication year, source URL, and categories (`Cultural Practices`, `Soil & Fertility`, `Irrigation & Spacing`, `Disease Prevention`).
   - Add new chunks incrementally into ChromaDB without deleting or recreating the existing collection.
2. **Context-Aware Query Normalization for Multi-Turn Dialogue**:
   - In `src/rag/generator.py` or `src/api/routes.py`, resolve anaphoric follow-up queries (e.g. *"Can it infect fruit?"* -> *"Can [Tomato___Late_blight] infect fruit?"*) using the latest resolved disease target from `conversation_history` or `case_id`.
3. **Multilingual Support (English and Hindi, extensible for Dogri)**:
   - Accept language preference (`"en"` / `"hi"`) in `ChatRequest`.
   - Deliver verified, accurate Hindi responses while preserving Latin botanical names and citations.
4. **Android Native Voice Input & Output**:
   - Add microphone control using Android `SpeechRecognizer` with `RECORD_AUDIO` runtime permission.
   - Add read-aloud TTS control using Android `TextToSpeech` with clean text formatting (skipping bracket citations and URLs).

