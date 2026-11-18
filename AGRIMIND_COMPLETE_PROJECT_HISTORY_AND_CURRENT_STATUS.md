# AgriMind — Complete Project History, Technical Development & Current Status Report

**Project Title:** AgriMind — Multi-Agent AI System for Crop Disease Investigation, Risk Assessment & Adaptive Decision Support  
**Academic Course Code:** `COM71116-21` (7th-Semester B.Tech Computer Science & Engineering Minor Project)  
**Institution:** Model Institute of Engineering and Technology (MIET), Jammu  
**Academic Session:** 2026–2027  
**Project Team:**  
- **Jaskirat Kour** (Team Leader, Roll No: `COM71116`, Main Administrator & Project Owner, Email: `jaskiratkourjk2005@gmail.com`)  
- **Palakjot Kour** (Roll No: `COM71117`)  
- **Sayam Malhotra** (Roll No: `COM71118`)  
- **Ikjot Singh** (Roll No: `COM71119`)  
**Report Generated:** November 18, 2026  
**Execution Mode:** STRICTLY READ-ONLY PROJECT INSPECTION AND DOCUMENTATION  
**Budget Consumed:** STRICTLY ₹0.00 / $0.00 (Zero cloud charges)  
**Primary Repository Root:** `c:\Users\asus\Downloads\Agri_Mind_Minor_Project`  
**Current Branch:** `main` (Tracking `origin/main` at `https://github.com/JaskiratKourA3-29/AgriMind.git`)

---

## Table of Contents
1. [Section A: Project Introduction](#section-a-project-introduction)
2. [Section B: Complete Development Timeline](#section-b-complete-development-timeline)
3. [Section C: Complete Feature Inventory](#section-c-complete-feature-inventory)
4. [Section D: Technical Architecture](#section-d-technical-architecture)
5. [Section E: AI/ML and Dataset Development](#section-e-aiml-and-dataset-development)
6. [Section F: Database Development and Migration History](#section-f-database-development-and-migration-history)
7. [Section G: Security and Reliability Improvements](#section-g-security-and-reliability-improvements)
8. [Section H: Complete Change Log](#section-h-complete-change-log)
9. [Section I: Testing and Verification History](#section-i-testing-and-verification-history)
10. [Section J: Cloud and Deployment History](#section-j-cloud-and-deployment-history)
11. [Section K: Current Project Status](#section-k-current-project-status)
12. [Section L: Pending Work and Known Issues](#section-l-pending-work-and-known-issues)
13. [Section M: Final Technical Snapshot](#section-m-final-technical-snapshot)
14. [Section N: Evidence and Accuracy Notes](#section-n-evidence-and-accuracy-notes)

---

## Section A: Project Introduction

### A.1. What AgriMind Is
**AgriMind** is an intelligent, full-stack, multi-agent agricultural decision-support system designed to empower smallholder farmers with accurate foliar disease diagnosis, dynamic epidemiological risk assessment, Integrated Pest Management (IPM) recommendations, adaptive disease reassessment, peer community discussions, and bilingual vernacular voice assistance.

Unlike conventional agricultural applications that merely output a disease classification label and a static chemical spray recommendation, AgriMind treats foliar crop pathology as an iterative, context-dependent investigation. It incorporates ambient micrometeorological weather data (temperature, relative humidity, precipitation forecast), canopy layer positioning, symptom progression over time, university agricultural extension literature, and peer grower knowledge.

### A.2. Problem It Aims to Solve
Smallholder farmers in India, particularly in northern agricultural belts like Jammu & Kashmir, face recurring crop losses due to foliar fungal and bacterial pathogens. Contemporary automated diagnostic tools suffer from four critical systemic failures:
1. **Monolithic Classification Bottleneck:** Standard deep learning models provide a single disease label without evaluating disease severity across the canopy or factoring in local weather conditions. A mild infection under hot, dry weather requires completely different intervention than the same infection under continuous warm rain.
2. **Catastrophic Laboratory-to-Field Domain Shift:** Deep CNN models trained on clean, laboratory-photographed datasets (such as single-leaf PlantVillage imagery on uniform gray/black paper) experience a severe drop in diagnostic accuracy when deployed in outdoor field environments (such as PlantDoc) where images contain complex backgrounds, soil clutter, direct sunlight glare, and multiple overlapping leaves.
3. **Agronomic Hallucination & Chemical Danger:** Naive Large Language Model (LLM) chatbots frequently hallucinate off-label pesticide recommendations, suggest illegal or toxic tank mixes, fail to specify statutory Pre-Harvest Intervals (PHI) and Re-Entry Intervals (REI), and confuse preventative protectants (e.g., Mancozeb, Chlorothalonil) with curative kickback fungicides (e.g., Cymoxanil, Mefenoxam).
4. **Vernacular & Usability Barrier:** Most digital farming tools operate exclusively in English and require high-speed, continuous internet access. Smallholder farmers who communicate in regional vernaculars (Hindi) or operate in low-connectivity rural environments are effectively excluded.

### A.3. Target Users
1. **Smallholder & Marginal Farmers:** Primary end users seeking rapid, vernacular, voice-guided diagnosis of tomato crops, actionable low-cost cultural/biological steps, and offline access to their case records.
2. **Agricultural Cooperative Managers & Field Officers:** Intermediate users who review shared case submissions from registered cooperative farmers, monitor disease spread in local clusters, and issue advisory bulletins.
3. **Agricultural Extension Specialists & Certified Agronomists:** Expert users who receive escalated cases requiring human-in-the-loop manual review when automated AI confidence is low or conflicting.
4. **Administrative Governance Officers (`owner`, `sub_owner`, `admin`):** Project leadership and regional coordinators who manage user accounts, oversee community content moderation, inspect system telemetry, and review security audit logs.

### A.4. Original Vision vs. Current Scope
- **Original Vision (October 2026):** A multi-agent AI system on Python with LangGraph and ChromaDB demonstrating tomato foliar pathology diagnosis and RAG-grounded advisory generation for academic defense.
- **Current Realized Scope (November 2026):** A complete enterprise-grade mobile and cloud ecosystem featuring:
  - Native Android application built with Kotlin and Jetpack Compose (Material 3).
  - Bilingual vernacular voice interaction (English and Hindi speech-to-text and text-to-speech with automatic Devanagari script detection).
  - Multi-tier role-based access control (RBAC) with immutable Main Owner supremacy (`owner`), fine-grained delegated permissions for `sub_owner`, and `admin`/`farmer` separation.
  - Social Farmer Community platform for peer-to-peer discussion with author solution acceptance badges.
  - Privacy-preserving case sharing with token authorization and GPS coordinate fuzzing (~3 km buffer).
  - Serverless cloud infrastructure ready for zero-cost operation (Vercel serverless backend, Neon PostgreSQL 18.7 cloud database, Supabase object storage for crop imagery).

### A.5. Supported Crop and Disease Classes
AgriMind's calibrated vision backbone focuses authoritatively on **Tomato foliar pathology** across three high-impact economic diseases, with rigorous out-of-distribution (OOD) rejection:
1. `Tomato___Bacterial_spot` (*Xanthomonas campestris* pv. *vesicatoria*)
2. `Tomato___Early_blight` (*Alternaria solani*)
3. `Tomato___Late_blight` (*Phytophthora infestans*)
4. `Healthy_Leaf` (Baseline reference)
5. `Out_of_Distribution` / `Non_Tomato_Crop` (Safely rejected by image validation rules and low-confidence gating).

### A.6. Languages and Platform Scope
- **Languages Supported:**
  - **English:** Full UI, technical reports, RAG synthesis, voice prompts.
  - **Hindi (हिंदी):** Full conversational assistant, vernacular voice queries (STT), spoken answers (TTS), Devanagari rendering, and translated diagnostic guidance.
- **Platform Scope:**
  - **Mobile:** Native Android (Min SDK 24 / Android 7.0 Nougat; Target SDK 34 / Android 14 UpsideDownCake).
  - **Backend:** Python 3.13 / FastAPI asynchronous REST API.
  - **Databases:** Local SQLite 3 (`data/cases.db`) + Cloud Serverless PostgreSQL 18.7 on Neon (`neondb`).
  - **Cloud Runtime:** Vercel Serverless Functions (`api/index.py`).

---

## Section B: Complete Development Timeline

The development of AgriMind progressed chronologically through structured academic milestones, system audits, mobile application releases, security hardenings, and cloud database migrations.

```
========================================================================================================
                                      AGRIMIND DEVELOPMENT TIMELINE
========================================================================================================

 [Oct 2026] Weeks 1-2: Vision Baseline Training (ResNet-50 on PlantVillage)
     │
 [Oct 2026] Week 3: RAG Knowledge Base Construction (ChromaDB + Extension Bulletins)
     │
 [Oct 2026] Weeks 4-5: Multi-Agent Logic Formulation (Investigation, Risk, Decision Planning)
     │
 [Oct 2026] Week 6: LangGraph State Machine Workflow Orchestration
     │
 [Oct 2026] Week 7: Adaptive Multi-Turn Reassessment Engine
     │
 [Oct 2026] Week 8: PlantDoc External Benchmark & Domain Shift Analysis (39.29% Field Accuracy)
     │
 [Oct 2026] Week 9: Critic & Safety Agent Integration (Strict 2-Cycle Loop Limit)
     │
 [Oct 2026] Week 10: Full FastAPI Backend Workflow Integration
     │
 [Oct 31, 2026] Phase 0: System Architecture Audit & Checkpoint Baseline Freeze
     │
 [Nov 1, 2026] Stage A: Baseline Verification & Closure (182 Backend Tests Passing)
     │
 [Nov 1, 2026] Stages B1–B5: Native Android App (Compose UI, Image Diagnosis, History, PDF Reports, Chat)
     │
 [Nov 2, 2026] Stages B6–B7: Vernacular Voice Assistant (English/Hindi STT/TTS, Devanagari Detection)
     │
 [Nov 2–3, 2026] Stages C1–C5: End-to-End Workflow Verification, AI Conclave Demo & Minor Dissertation
     │
 [Nov 3, 2026] Post-C: Sub-Owner Governance Tier (4-Tier RBAC, Main Owner Supremacy)
     │
 [Nov 3, 2026] Post-C: Farmer Community Platform (Peer Discussions, Author Acceptance, Disclaimers)
     │
 [Nov 4–11, 2026] Stages 1I–1J & 2A–2D: Cloud Deployment Planning, GitHub Push, Mobile Network Config
     │
 [Nov 12, 2026] Stages 2E–2L: Vercel Serverless Audit & PostgreSQL Compatibility v1
     │
 [Nov 12–15, 2026] Stages 2M–2Q: Image URL SSRF Security Hardening & DNS Rebinding Protections
     │
 [Nov 15, 2026] Stage 3A: Cloud Infrastructure Provisioning (Neon PostgreSQL 18.7, Supabase, Vercel)
     │
 [Nov 16, 2026] Stage 3B.1: PostgreSQL DDL Engineering (V1 to V8 Iterations, Offline Validation)
     │
 [Nov 17, 2026] Stage 3B.2: PostgreSQL 18.7 Operator Resolution Fix (V9 DDL) & Live Schema Execution
     │
 [Nov 17, 2026] Stage 3B.3.1–3B.3.2: SQLite-to-Neon Live Data Migration (266 Rows Imported, 100% Parity)
     │
 [Nov 17, 2026] Stage 3B.3.3–3B.3.5: Targeted Compatibility Patch Preparation & Independent Audit Approval
========================================================================================================
```

### Detailed Chronological Stages

#### Milestone 1: Week 1–2 — Vision Baseline Training (October 2026)
- **Objective:** Train a deep convolutional neural network for tomato foliar disease classification.
- **Work Performed:** Fine-tuned a PyTorch `ResNet-50` architecture pretrained on ImageNet against the PlantVillage tomato subset. Utilized a two-phase training strategy: 3 epochs of linear classifier warmup followed by 15 epochs of end-to-end fine-tuning. Best checkpoint achieved at epoch 12.
- **Files Created/Modified:** `src/vision/model.py`, `src/vision/dataset.py`, `src/vision/train.py`, `src/vision/evaluate.py`, `outputs/week2_vision/best_model.pth`.
- **Results:** Validation loss: `0.0962`, Accuracy: `98.41%` (991/1007 images), Macro-F1: `0.9828`. Checkpoint size: `282,626,785 bytes` (~282.6 MB).
- **Reported Status:** `COMPLETE`.

#### Milestone 2: Week 3 — RAG Knowledge Base Construction (October 2026)
- **Objective:** Establish an agricultural retrieval-augmented generation (RAG) system grounded in accredited university extension bulletins.
- **Work Performed:** Curated extension documents from Cornell University CALS, University of California IPM, Purdue University Extension, and University of Florida IFAS. Chunked documents into 63 semantically coherent passages. Built a ChromaDB vector store using `sentence-transformers/all-MiniLM-L6-v2` embeddings. Implemented hybrid MMR retrieval and extractive synthesis.
- **Files Created/Modified:** `data/knowledge_base/raw/*.md`, `src/rag/ingest.py`, `src/rag/vectorstore.py`, `src/rag/retriever.py`, `src/rag/generator.py`, `outputs/week3_rag/retrieval_benchmarks.json`.
- **Results:** 15 in-domain queries evaluated: `100%` hit rate at $k=4$. 2 out-of-domain queries (Apple fire blight, corn weed herbicide) safely rejected with standard agricultural referral.
- **Reported Status:** `COMPLETE`.

#### Milestone 3: Weeks 4–5 — Multi-Agent Logic Formulation (October 2026)
- **Objective:** Design specialized agent personas to break down the monolithic diagnostic bottleneck.
- **Work Performed:** Defined Pydantic schemas in `src/agents/schemas.py`. Created the **Investigation Agent** (analyzes visual symptoms, canopy location, lesion morphology), **Risk Assessment Agent** (integrates temperature, relative humidity, and rainfall forecasts to compute an Epidemiological Risk Index), and **Decision Planning Agent** (enforces strict Integrated Pest Management hierarchy: Cultural -> Biological -> Chemical Preventative -> Chemical Curative).
- **Files Created/Modified:** `src/agents/schemas.py`, `src/agents/investigation.py`, `src/agents/risk_assessment.py`, `src/agents/decision_planning.py`, `src/agents/prompts.py`.
- **Results:** Unit tested in isolation; validated that high-humidity/rain forecasts dynamically elevate late blight risk from Low to High.
- **Reported Status:** `COMPLETE`.

#### Milestone 4: Week 6 — LangGraph Workflow Orchestration (October 2026)
- **Objective:** Connect all agent nodes into an asynchronous stateful execution graph using LangGraph.
- **Work Performed:** Built `AgriMindState` tracking image path, vision outputs, retrieved documents, investigation findings, risk assessments, IPM plan, critic verification, and loop counts. Constructed `StateGraph` in `src/workflow/graph.py` with conditional edges.
- **Files Created/Modified:** `src/workflow/state.py`, `src/workflow/nodes.py`, `src/workflow/graph.py`.
- **Results:** Graph compiles cleanly; conditional routing properly aborts to output upon image validation failure.
- **Reported Status:** `COMPLETE`.

#### Milestone 5: Week 7 — Adaptive Multi-Turn Reassessment (October 2026)
- **Objective:** Enable farmers to re-photograph a diagnosed plant days after treatment to assess recovery or treatment failure.
- **Work Performed:** Implemented `reassessment_node` comparing current symptoms against prior case state. Introduced trajectory classifications: `improving`, `stagnant`, `deteriorating`. Configured conditional re-entry into RAG retrieval.
- **Files Created/Modified:** `src/workflow/nodes.py`, `src/api/case_store.py`, `tests/test_week7_reassessment.py`.
- **Results:** Multi-turn state transitions verified; trajectory accurately flagged deterioration when canopy spread increased after 7 days.
- **Reported Status:** `COMPLETE`.

#### Milestone 6: Week 8 — PlantDoc External Benchmark & Domain Shift Analysis (October 2026)
- **Objective:** Quantify model performance on unconstrained in-the-wild agricultural photography.
- **Work Performed:** Evaluated the ResNet-50 checkpoint against the official independent test split of the PlantDoc dataset ($N=28$) and exploratory full collection ($N=309$). Conducted Grad-CAM saliency mapping and Phase 2 background masking experiments.
- **Files Created/Modified:** `src/vision/evaluation_framework.py`, `outputs/week8_plantdoc_evaluation/*`, `outputs/gradcam_analysis/*`, `outputs/phase2_background_masking/*`.
- **Results:** Accuracy dropped from `98.41%` (PlantVillage) to `39.29%` (PlantDoc test split, Macro-F1: `0.3079`). Background masking improved accuracy to `50.00%`. Proved that single-leaf CNNs fail in field environments due to background clutter, validating AgriMind's multi-agent contextual architecture.
- **Reported Status:** `COMPLETE`.

#### Milestone 7: Week 9 — Critic & Safety Agent Integration (October 2026)
- **Objective:** Provide automated verification of agronomic treatment plans before delivery to farmers.
- **Work Performed:** Implemented the **Critic Agent** (`src/agents/critic.py`) to verify chemical dosages, check for prohibited tank mixes, ensure mandatory PPE advisories, and enforce statutory PHI/REI declarations. Enforced a hard recursion limit of at most 2 critique cycles.
- **Files Created/Modified:** `src/agents/critic.py`, `tests/test_week9_critic_analysis.py`.
- **Results:** 100% of synthetic plans with off-label chemicals were intercepted and routed to manual review.
- **Reported Status:** `COMPLETE`.

#### Milestone 8: Week 10 — Full FastAPI Backend Workflow Integration (October 2026)
- **Objective:** Expose the complete diagnostic and conversational workflow via a high-performance REST API.
- **Work Performed:** Built FastAPI routes for image upload (`/api/v1/diagnose`), case management (`/api/v1/cases`), conversational chat (`/api/v1/chat`), and system health (`/api/v1/health`).
- **Files Created/Modified:** `src/api/app.py`, `src/api/routes.py`, `src/api/schemas.py`, `tests/test_week10_workflow_integration.py`.
- **Results:** Full end-to-end HTTP lifecycle verified; image caching verified.
- **Reported Status:** `COMPLETE`.

#### Milestone 9: Phase 0 & Stage A — System Architecture Audit & Baseline Freeze (Late October – Nov 1, 2026)
- **Objective:** Audit entire repository, preserve authoritative checkpoints, and establish true automated test baselines.
- **Work Performed:** Discovered and fixed image cache key omission (which previously ignored observation notes) and cross-test cache pollution. Audited test suite: revealed that 182 backend tests passed out of 218 discovered in WSL. Verified that all 49 Android unit tests passed. Froze checkpoint `best_model.pth`.
- **Files Created/Modified:** `docs/full_existing_system_architecture_audit.md`, `docs/phase0_preservation_and_baseline_report.md`, `docs/stage_a_final_closure_report.md`.
- **Results:** Baseline established: 182 backend + 49 Android = 231 passing tests.
- **Reported Status:** `COMPLETE`.

#### Milestone 10: Stages B1–B5 — Native Android Mobile Application Foundation (Nov 1, 2026)
- **Objective:** Build a native Android application for smallholder farmers using modern Jetpack Compose.
- **Work Performed:**
  - **Stage B1:** Established MVVM architecture, Material 3 theme, navigation graph, and Retrofit HTTP client.
  - **Stage B2:** Built `DiagnosisScreen` supporting CameraX image capture, gallery picking, observation forms, and animated diagnostic progress states.
  - **Stage B3:** Implemented `CaseDetailScreen` with chronological reassessment timeline rendering and IPM recommendation cards.
  - **Stage B4:** Developed `PdfReportGenerator.kt` for native on-device A4 PDF crop health certificate creation with custom vector Canvas graphics and QR verification codes.
  - **Stage B5:** Implemented `ChatScreen` for conversational AI grounded in diagnosed case context.
- **Files Created/Modified:** `android/app/src/main/java/com/agrimind/app/**`.
- **Results:** Clean Gradle compilation; verified on Android emulators (API 34).
- **Reported Status:** `COMPLETE`.

#### Milestone 11: Stages B6–B7 — Vernacular Voice Assistant & Hindi Support (Nov 2, 2026)
- **Objective:** Equip the mobile application with bilingual vernacular voice interaction for rural smallholder accessibility.
- **Work Performed:** Integrated Android `SpeechRecognizer` (STT) and `TextToSpeech` (TTS). Created automated Devanagari script detector (`LanguageDetector.kt`). Built voice query transcription persistence, caching transcripts to SQLite (`ChatDatabaseHelper.kt`). Added Hindi system prompting in RAG generator.
- **Files Created/Modified:** `android/app/src/main/java/com/agrimind/app/util/LanguageDetector.kt`, `android/app/src/main/java/com/agrimind/app/data/local/ChatDatabaseHelper.kt`, `src/rag/generator.py`, `docs/stage_b6_multilingual_voice_assistant_report.md`.
- **Results:** Speech-to-text transcriptions and audio responses verified on physical/emulated devices in English and Hindi.
- **Reported Status:** `COMPLETE`.

#### Milestone 12: Stages C1–C5 — Final Verification, AI Conclave Demo & Dissertation (Nov 2–3, 2026)
- **Objective:** Conduct rigorous end-to-end acceptance testing and assemble academic dissertation dossier.
- **Work Performed:** Executed full verification matrix across physical devices, emulators, and backend services. Authored the Minor Project Dissertation (`final_minor_project_dissertation.md`), AI Conclave Demo Runbook, and Examiner Viva Quick Reference.
- **Files Created/Modified:** `docs/final_minor_project_dissertation.md`, `docs/stage_c5_acceptance_and_release_report.md`, `docs/ai_conclave_demo_runbook.md`.
- **Results:** 94/94 acceptance tests passed with zero defects. Production debug APK assembled (`app-debug.apk`, 17.9 MB).
- **Reported Status:** `COMPLETE`.

#### Milestone 13: Sub-Owner Governance Tier (Nov 3, 2026)
- **Objective:** Introduce a delegated administrative tier (`sub_owner`) while maintaining immutable Main Owner supremacy.
- **Work Performed:** Upgraded SQLite schema to add `sub_owner_permissions` table and role check constraint. Main Owner **Jaskirat Kour** (`USER-3FC32032`, `jaskiratkourjk2005@gmail.com`) was designated immutable top authority. Sub-owners receive granular configurable permissions (`can_manage_users`, `can_moderate_cases`, `can_view_telemetry`, `can_view_audit_logs`). Added immediate token invalidation on role revocation. Added purple `SUB-OWNER` badges and admin controls in Android.
- **Files Created/Modified:** `src/services/auth_service.py`, `src/api/routes.py`, `android/app/src/main/java/com/agrimind/app/ui/screens/AdminDashboardScreen.kt`, `artifacts/SUB_OWNER_GOVERNANCE_AND_APPLICATION_RELEASE_REPORT.md`.
- **Results:** 29 backend tests + 62 Android tests passed (100%).
- **Reported Status:** `COMPLETE`.

#### Milestone 14: Farmer Community & Social Connection System (Nov 3, 2026)
- **Objective:** Provide a dedicated social platform for peer-to-peer farmer interaction isolated from AI diagnostics.
- **Work Performed:** Created 4 relational tables (`community_posts`, `community_comments`, `community_reactions`, `community_reports`). Implemented category filtering (`Pest Alert`, `Crop Advisory`, `Fertilizer`, `General`), nested comment threads, like reactions, moderation reporting, and author solution acceptance (`is_accepted`). Integrated peer-advice safety disclaimers. Built `CommunityScreen.kt` and `CommunityViewModel.kt`.
- **Files Created/Modified:** `src/services/community_service.py`, `src/api/routes.py`, `android/app/src/main/java/com/agrimind/app/ui/screens/CommunityScreen.kt`, `artifacts/FARMER_COMMUNITY_FEATURE_AND_APPLICATION_RELEASE_REPORT.md`.
- **Results:** 30 backend unit tests + 68 Android unit tests passed. Fresh debug APK compiled (18.5 MB).
- **Reported Status:** `COMPLETE`.

#### Milestone 15: Security Audit & Account Verification (Nov 3, 2026)
- **Objective:** Audit user database, eliminate orphaned test accounts, and secure project credentials.
- **Work Performed:** Verified that only 2 authoritative accounts exist in `data/cases.db`: Main Owner **Jaskirat Kour** (`jaskiratkourjk2005@gmail.com`) and Farmer **Simran Kour** (`2023a1r029@mietjammu.in`). Removed obsolete test credentials. Confirmed PBKDF2/bcrypt password hashing.
- **Files Created/Modified:** `artifacts/SECURITY_AUDIT_AND_ACCOUNT_INVESTIGATION_REPORT.md`.
- **Results:** Zero unauthorized administrative accounts; role isolation verified.
- **Reported Status:** `COMPLETE`.

#### Milestone 16: Stages 1I–1J & 2A–2D — Cloud Architecture & Deployment Planning (Nov 4–11, 2026)
- **Objective:** Formulate zero-cost cloud deployment architecture and mobile deployment readiness.
- **Work Performed:** Selected the target stack: Vercel Serverless (FastAPI backend), Neon Serverless PostgreSQL (relational database), and Supabase Storage (image bucket). Configured Android network security (`network_security_config.xml`) to permit cloud domains. Created `Dockerfile` and production dependencies (`requirements-prod.txt`). Pushed repository to GitHub (`origin/main`).
- **Files Created/Modified:** `Dockerfile`, `requirements-prod.txt`, `android/app/src/main/res/xml/network_security_config.xml`, `artifacts/STAGE_2C_GITHUB_PUSH_REPORT.md`.
- **Results:** Repository successfully synced with GitHub remote.
- **Reported Status:** `COMPLETE`.

#### Milestone 17: Stages 2E–2L — Vercel Serverless Compatibility & PostgreSQL v1 Compatibility (Nov 12, 2026)
- **Objective:** Audit backend code for serverless stateless execution and prepare dual-engine SQLite/PostgreSQL compatibility.
- **Work Performed:** Created `vercel.json` and `api/index.py` serverless entry points. Audited code for ephemeral storage assumptions. Introduced `DBConnectionWrapper` in `auth_service.py`, `case_sharing_service.py`, and `community_service.py` to transparently swap query parameter syntax between SQLite (`?`) and PostgreSQL (`%s`).
- **Files Created/Modified:** `vercel.json`, `api/index.py`, `src/services/auth_service.py`, `src/services/community_service.py`, `artifacts/STAGE_2E_VERCEL_COMPATIBILITY_AUDIT.md`.
- **Results:** Dual-engine query parameter translation verified offline.
- **Reported Status:** `COMPLETE`.

#### Milestone 18: Stages 2M–2Q — SSRF Image URL Security Hardening & DNS Rebinding (Nov 12–15, 2026)
- **Objective:** Eliminate critical Server-Side Request Forgery (SSRF) vulnerabilities in diagnosis image URL fetching.
- **Work Performed:** Discovered that image fetching from external URLs could be abused to probe internal network infrastructure or cloud metadata services. Hardened `fetch_remote_image()` in `src/api/routes.py` with strict URL scheme checks (HTTPS only), IP address pinning, explicit filtering of RFC 1918 private ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.1`), link-local, and cloud metadata endpoints (`169.254.169.254`). Implemented custom socket factory binding the pre-resolved IP to prevent DNS rebinding (TOCTOU) attacks.
- **Files Created/Modified:** `src/api/routes.py`, `tests/test_api_security.py`, `artifacts/STAGE_2Q_FINAL_INDEPENDENT_SECURITY_AND_PRE_CLOUD_READINESS_REPORT.md`.
- **Results:** 14 security tests passed with 100% block rate against private IPs, AWS metadata, and rebinding redirects.
- **Reported Status:** `COMPLETE`.

#### Milestone 19: Stage 3A — Cloud Infrastructure Provisioning (Nov 15, 2026)
- **Objective:** Provision live cloud resources on free-tier platforms without incurring costs.
- **Work Performed:** Verified live provisioning of:
  - **Neon Serverless PostgreSQL:** Endpoint `ep-rapid-bird-azbsdnm6-pooler.c-3.ap-southeast-1.aws.neon.tech`, database `neondb`, role `neondb_owner`.
  - **Supabase Object Storage:** Bucket `agrimind-crop-images` configured for public read and service-role authenticated uploads.
  - **Environment Configuration:** Prepared `.env.cloud.template`.
- **Files Created/Modified:** `.env.cloud.template`, `scratch/test_stage_3a_connectivity.py`, `artifacts/STAGE_3A_3_CLOUD_PROVISIONING_AND_CONNECTIVITY_REPORT.md`.
- **Results:** TCP socket handshake and SSL negotiation confirmed without exposing secrets or consuming budget.
- **Reported Status:** `COMPLETE`.

#### Milestone 20: Stage 3B.1 — PostgreSQL DDL & Migration Engineering (Nov 16, 2026)
- **Objective:** Author canonical PostgreSQL DDL and data migration script across iterations V1 through V8.
- **Work Performed:** Authored DDL script defining all 12 application tables, 98 columns, 12 primary keys, 11 secondary indexes, 5 cascading foreign keys, 2 unique constraints, and 1 check constraint. Built offline test suite `scratch/test_v8_offline_validation.py` (22/22 passing). Prepared data migration candidate `scratch/migrate_sqlite_to_neon_data_v1.py` with test suite (26/26 passing). Applied Compatibility Patch V1 in Stage 3B.1.22.
- **Files Created/Modified:** `scratch/execute_stage_3b2_ddl_v8.py`, `scratch/migrate_sqlite_to_neon_data_v1.py`, `scratch/test_sqlite_to_neon_migration_v1.py`, `artifacts/STAGE_3B_1_22_COMPATIBILITY_PATCH_APPLICATION_REPORT.md`.
- **Results:** DDL validated offline; data migration script verified in-memory across 26 tests.
- **Reported Status:** `COMPLETE`.

#### Milestone 21: Stage 3B.2 — PostgreSQL 18.7 Fix (V9) & Live Schema Execution (Nov 17, 2026)
- **Objective:** Resolve PostgreSQL 18.7 catalog operator ambiguity and execute live schema creation on Neon.
- **Work Performed:** Initial V8 live preflight failed due to PostgreSQL 18.7 operator resolution changes (`SQLSTATE 42725: operator is not unique: "char" || unknown`). Prepared candidate V9 (`scratch/execute_stage_3b2_ddl_v9.py`) adding explicit `::text` casts to `relkind`, `typtype`, and `prokind` in the 13-catalog union query. Executed V9 on Neon under explicit owner authorization.
- **Files Created/Modified:** `scratch/execute_stage_3b2_ddl_v9.py`, `scratch/test_v9_offline_validation.py`, `artifacts/STAGE_3B_2_4_V9_SCHEMA_EXECUTION_REPORT.md`.
- **Results:** Schema creation succeeded with exit code 0. Live inspection confirmed: **12 tables, 98 columns, 12 PKs, 11 indexes, 5 cascading FKs, 2 UNIQUE, 1 CHECK constraint**. Zero unexpected objects; 0 rows created.
- **Reported Status:** `COMPLETE`.

#### Milestone 22: Stage 3B.3.1–3B.3.2 — Live SQLite-to-Neon Data Migration (Nov 17, 2026)
- **Objective:** Migrate all existing application data from `data/cases.db` to Neon PostgreSQL without data loss.
- **Work Performed:** Verified candidate `scratch/migrate_sqlite_to_neon_data_v1.py` (SHA-256: `1ff566f7...`). Following owner authorization, executed migration script against Neon in an atomic single transaction (`BEGIN` -> batch inserts -> in-transaction checks -> `COMMIT`). Conducted deep post-migration verification.
- **Files Created/Modified:** `artifacts/STAGE_3B_3_2_DATA_MIGRATION_EXECUTION_REPORT.md`.
- **Results:** Exactly **266 application rows imported with 100% row count parity across all 12 tables**. 100% primary key uniqueness preserved. Zero foreign key orphans. Source `data/cases.db` remained completely unmodified (`87a0f052...`).
- **Reported Status:** `COMPLETE`.

#### Milestone 23: Stage 3B.3.3–3B.3.5 — Compatibility Patch Preparation & Independent Audit (Nov 17, 2026)
- **Objective:** Identify, correct, and independently audit remaining PostgreSQL runtime compatibility blockers in the application codebase.
- **Work Performed:**
  - Stage 3B.3.3 identified 4 blockers: unguarded `ALTER TABLE` in `CaseStore._init_db()` aborting transactions, raw connection `.execute()` in `routes.py:admin_system_status()`, `RealDictRow` integer indexing (`row[0]`) in `auth_service`, `community_service`, and `routes.py`, and missing local driver.
  - Stage 3B.3.4 prepared candidate patch `scratch/stage_3b_3_4_postgresql_compatibility_patch.diff` and offline test suite `scratch/test_stage_3b_3_4_postgresql_compatibility.py`.
  - Stage 3B.3.5 conducted independent audit: verified SHA-256 hashes, confirmed clean dry-run (`git apply --check` exit code 0), ran 10 focused tests (10/10 passed in 0.078s), and ran full regression suite (35/35 passed in 1.772s).
- **Files Created/Modified:** `scratch/stage_3b_3_4_postgresql_compatibility_patch.diff`, `scratch/test_stage_3b_3_4_postgresql_compatibility.py`, `artifacts/STAGE_3B_3_5_INDEPENDENT_COMPATIBILITY_PATCH_REVIEW.md`.
- **Results:** Audit verdict: **`PATCH APPROVED FOR OWNER AUTHORIZATION`**. (Per instructions, the patch was NOT applied to application files).
- **Reported Status:** `COMPLETE`.

---

## Section C: Complete Feature Inventory

| Subsystem | Feature Name | Technical Mechanism & Implementation Files | Status | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Vision & AI** | Deep Foliar Classification | PyTorch ResNet-50 (`outputs/week2_vision/best_model.pth`, `src/vision/model.py`, `src/vision/inference.py`). Evaluates 3 tomato disease classes. | `IMPLEMENTED AND VERIFIED` | 98.41% accuracy on PlantVillage test split; model weights verified on disk (282.6 MB). |
| **Vision & AI** | Image Quality Validation | `src/vision/image_validator.py`. Validates image dimensions, aspect ratio, blur detection via Laplacian variance, and brightness limits. | `IMPLEMENTED AND VERIFIED` | Tested in `tests/test_image_validator.py` and `tests/test_feature2_vision_inference.py`. |
| **Vision & AI** | Saliency & Domain Shift Analysis | `outputs/gradcam_analysis/`, `src/vision/evaluation_framework.py`. Grad-CAM heatmaps highlight background sky/soil clutter. | `IMPLEMENTED AND VERIFIED` | Diagnostic report and comparative heatmaps documented in `outputs/gradcam_analysis/`. |
| **RAG & Knowledge** | ChromaDB Agricultural Vector Store | 63 curated vector chunks from Cornell CALS, UC IPM, Purdue, UF/IFAS (`data/vectorstore/chroma/`, `src/rag/vectorstore.py`, `retriever.py`). | `IMPLEMENTED AND VERIFIED` | 15/15 in-domain queries achieved 100% hit rate at k=4; benchmarks in `outputs/week3_rag/`. |
| **RAG & Knowledge** | Grounded Extractive Synthesis | `src/rag/generator.py`. Generates multi-citation recommendations using Gemini API with fallback extractive synthesis during quota exhaustion. | `IMPLEMENTED AND VERIFIED` | Tested in `tests/test_rag_generation.py`; verified fallback under simulated 429 quota exhaustion. |
| **Multi-Agent** | LangGraph Workflow State Machine | `src/workflow/graph.py`, `nodes.py`, `state.py`. Connects validation -> vision -> retrieval -> investigation -> risk -> decision -> critic. | `IMPLEMENTED AND VERIFIED` | Compiles cleanly; end-to-end execution verified in `tests/test_week6_workflow.py` and `test_week10_...`. |
| **Multi-Agent** | 4-Tier IPM Decision Planning | `src/agents/decision_planning.py`. Enforces Cultural -> Biological -> Chemical Preventative -> Chemical Curative hierarchy. | `IMPLEMENTED AND VERIFIED` | Validated in `tests/test_week5_agents.py`; output structures strictly adhere to Pydantic schemas. |
| **Multi-Agent** | Weather Epidemiological Gating | `src/agents/risk_assessment.py`, `src/services/weather_service.py`. Dynamically adjusts late blight risk based on ambient temperature, humidity, and rainfall. | `IMPLEMENTED AND VERIFIED` | Tested in `tests/test_weather_guidance.py` and `tests/test_weather_service.py`. |
| **Multi-Agent** | Critic & Safety Verification | `src/agents/critic.py`. Intercepts toxic tank mixes, enforces PHI/REI declarations, caps recursion to max 2 critique cycles. | `IMPLEMENTED AND VERIFIED` | Validated in `tests/test_week9_critic_analysis.py`. |
| **Reassessment** | Adaptive Multi-Turn Reassessment | `src/workflow/nodes.py:reassessment_node`, `CaseDetailScreen.kt`. Computes trajectory (`improving`, `stagnant`, `deteriorating`) across multi-day visits. | `IMPLEMENTED AND VERIFIED` | Tested in `tests/test_week7_reassessment.py`; 37 live reassessments verified in database. |
| **Conversational** | Bilingual Vernacular Chat | `ChatScreen.kt`, `ChatViewModel.kt`, `src/rag/generator.py`. Supports English and Hindi conversations anchored to diagnosed case history. | `IMPLEMENTED AND VERIFIED` | Tested on Android emulators; Devanagari script rendering verified in UI dumps. |
| **Conversational** | Speech-to-Text & Text-to-Speech | Android `SpeechRecognizer` & `TextToSpeech` (`ChatScreen.kt`). Vernacular voice mic with automatic language switching. | `IMPLEMENTED AND VERIFIED` | Documented with screenshots in `docs/stage_b6_1_voice_query_validation_report.md`. |
| **Reporting** | On-Device Native A4 PDF Generator | `PdfReportGenerator.kt`. Generates multi-page A4 crop health certificates with Canvas graphics, IPM steps, and QR verification codes. | `IMPLEMENTED AND VERIFIED` | Physical PDF artifacts generated in `outputs/` (e.g. `AgriMind_Report_CASE-7DC903FC.pdf`). |
| **Privacy & Sharing** | Tokenized Case Sharing & GPS Fuzzing | `src/services/case_sharing_service.py`, `CaseDetailScreen.kt`. Secure share tokens; fuzzes farmer GPS coordinates to ~3 km buffer. | `IMPLEMENTED AND VERIFIED` | Tested in `tests/test_case_sharing.py`; logs confirm delta `0.0266°` fuzzing. |
| **Governance** | Multi-Tier RBAC & Owner Supremacy | `src/services/auth_service.py`. Enforces Main Owner supremacy (Jaskirat Kour), `sub_owner` with granular flags, `admin`, and `farmer`. | `IMPLEMENTED AND VERIFIED` | Tested in `tests/test_auth_and_roles.py` and `tests/test_sub_owner_governance.py`. |
| **Community** | Peer Grower Social Platform | `src/services/community_service.py`, `CommunityScreen.kt`. Posts, comments, threaded replies, likes, moderation reports, author accepted badges. | `IMPLEMENTED AND VERIFIED` | 30 backend tests + 68 Android tests passed; schemas verified in database. |
| **Security** | SSRF Hardening & DNS Rebinding | `src/api/routes.py:fetch_remote_image`. IP pinning, filtering private/loopback/cloud metadata ranges, socket factory binding. | `IMPLEMENTED AND VERIFIED` | 14 security tests passed with 100% block rate in `tests/test_api_security.py`. |
| **Database** | Serverless PostgreSQL Migration | Neon PostgreSQL 18.7 cloud database (`neondb`). 12 tables, 98 columns, 266 migrated records. | `IMPLEMENTED AND VERIFIED` | Verified live on Neon; reports `STAGE_3B_2_4` and `STAGE_3B_3_2`. |
| **Compatibility** | PostgreSQL Application Compatibility | `scratch/stage_3b_3_4_postgresql_compatibility_patch.diff`. Resolves transaction aborts, raw execute, and RealDictRow indexing. | `PREPARED — READY TO APPLY` | Reviewed and approved in `STAGE_3B_3_5`; 10/10 focused tests + 35/35 regression passed. |
| **Deployment** | Serverless Cloud Deployment | Vercel Serverless (`vercel.json`, `api/index.py`) + Neon + Supabase Storage. | `PARTIALLY IMPLEMENTED` | Config files created and verified; live Vercel deploy pending owner authorization. |

---

## Section D: Technical Architecture

AgriMind employs a modular, decoupled, cloud-ready architecture designed for smallholder accessibility, agronomic safety, and high-availability zero-cost cloud hosting.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 NATIVE ANDROID CLIENT                                  │
│                                                                                        │
│   ┌───────────────────────┐  ┌───────────────────────┐  ┌──────────────────────────┐   │
│   │    DiagnosisScreen    │  │   CaseDetailScreen    │  │        ChatScreen        │   │
│   │ (CameraX, Gallery,    │  │ (IPM Timeline, PDF    │  │ (Bilingual STT/TTS Voice,│   │
│   │  Observation Context) │  │  Generator, Sharing)  │  │  Devanagari UI, Context) │   │
│   └───────────┬───────────┘  └───────────┬───────────┘  └────────────┬─────────────┘   │
│               │                          │                           │                 │
│               └──────────────────────────┼───────────────────────────┘                 │
│                                          │                                             │
│                               ┌──────────┴───────────┐                                 │
│                               │   RetrofitClient /   │                                 │
│                               │  OkHttp (Token Auth) │                                 │
│                               └──────────┬───────────┘                                 │
└──────────────────────────────────────────┼─────────────────────────────────────────────┘
                                           │ HTTPS (Encrypted REST API)
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        FASTAPI BACKEND RUNTIME (VERCEL SERVERLESS)                     │
│                                                                                        │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ API Routing Layer (`src/api/routes.py`, `schemas.py`)                          │   │
│   │ - SSRF-Hardened Remote Image Fetcher with DNS Pinning                          │   │
│   │ - JWT Bearer Authentication & RBAC Authorization Middleware                    │   │
│   │ - Image Submission SHA-256 Deduplication Cache                                 │   │
│   └───────────────────────┬────────────────────────────────┬───────────────────────┘   │
│                           │                                │                           │
│                           ▼                                ▼                           │
│   ┌──────────────────────────────────────────┐ ┌───────────────────────────────────┐   │
│   │ LangGraph Multi-Agent Reasoning Core     │ │ Core Domain Services              │   │
│   │                                          │ │                                   │   │
│   │   [validate_image] -> [vision_node]      │ │ • AuthService (RBAC, Audit Logs)  │   │
│   │                           │              │ │ • CaseStore (CRUD, Reassessment)  │   │
│   │                           ▼              │ │ • CommunityService (Social Feed)  │   │
│   │   [retrieval_node] -> [investigation]    │ │ • CaseSharingService (Tokens, GPS)│   │
│   │                           │              │ │ • WeatherService (Open-Meteo API) │   │
│   │                           ▼              │ └─────────────────┬─────────────────┘   │
│   │   [risk_assessment] -> [decision_plan]   │                   │                     │
│   │                           │              │                   │                     │
│   │                           ▼              │                   │                     │
│   │   [critic_node] -> [finalize_output]     │                   │                     │
│   └───────────────────────┬──────────────────┘                   │                     │
│                           │                                      │                     │
│                           ▼                                      ▼                     │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ DBConnectionWrapper (`is_postgres` Dual-Engine Compatibility Layer)            │   │
│   └───────────────────────────────────────┬────────────────────────────────────────┘   │
└───────────────────────────────────────────┼────────────────────────────────────────────┘
                                            │ PostgreSQL Wire Protocol (SSL)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                    NEON SERVERLESS CLOUD DATABASE (POSTGRESQL 18.7)                    │
│                                                                                        │
│   • users (10 cols, 2 rows)                • cases (9 cols, 215 rows)                  │
│   • sub_owner_permissions (5 cols, 0 rows) • shared_cases (11 cols, 17 rows)           │
│   • revoked_tokens (2 cols, 0 rows)        • case_comments (7 cols, 26 rows)           │
│   • audit_logs (8 cols, 3 rows)            • case_outcomes (5 cols, 3 rows)            │
│   • community_posts (14 cols, 0 rows)      • community_comments (11 cols, 0 rows)      │
│   • community_reactions (6 cols, 0 rows)   • community_reports (10 cols, 0 rows)       │
│                                                                                        │
│   [Total Verified Schema: 12 Tables • 98 Columns • 266 Authoritative Records]          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Breakdown
1. **Android Client Layer:** Built entirely in Kotlin using Jetpack Compose and Material 3 design patterns. Follows unidirectional data flow (UDF) with ViewModels exposing `StateFlow` to composable screens. Manages local SQLite storage for offline caching via `ChatDatabaseHelper` and `OfflineQueueManager`.
2. **Backend API Layer:** FastAPI application serving asynchronous endpoints. Enforces strict input validation through Pydantic models. Hardened against SSRF via DNS IP pinning and custom socket connections.
3. **Multi-Agent Orchestration Layer:** LangGraph state machine coordinating sequential and conditional execution across 10 specialized nodes. State transitions are strictly governed by Pydantic schema validation.
4. **Knowledge Retrieval Layer:** ChromaDB vector database housing 63 curated extension publication chunks. Uses cosine similarity and MMR reranking to supply evidence citations.
5. **Data Persistence Layer:** Unified under `DBConnectionWrapper`, allowing transparent operation over local development SQLite (`data/cases.db`) and production serverless PostgreSQL 18.7 hosted on Neon Cloud.

---

## Section E: AI/ML and Dataset Development

### E.1. Model Architecture & Checkpoint Details
- **Architecture:** `ResNet-50` deep convolutional neural network (pretrained on ImageNet, custom linear classifier replacement).
- **Physical Checkpoint:** `outputs/week2_vision/best_model.pth`
- **File Size:** `282,626,785 bytes` (~282.6 MB)
- **Input Dimensions:** $3 \times 224 \times 224$ RGB tensors normalized with standard ImageNet statistics ($\mu = [0.485, 0.456, 0.406]$, $\sigma = [0.229, 0.224, 0.225]$).
- **Target In-Scope Classes (3):**
  - Index `0`: `Bacterial_spot`
  - Index `1`: `Early_blight`
  - Index `2`: `Late_blight`

### E.2. Training Methodology & History
- **Dataset:** PlantVillage Tomato foliar pathology subset.
- **Split Ratio:** $80\%$ Training ($N=4,028$), $20\%$ Validation ($N=1,007$).
- **Optimizer:** AdamW with cosine annealing learning rate scheduler.
- **Warmup Phase (Epochs 1–3):** Frozen backbone, linear classifier warmup (Epoch 1 acc: $42.54\%$, Epoch 3 acc: $59.62\%$).
- **Fine-Tuning Phase (Epochs 4–18):** Unfrozen layers. Reached peak validation performance at **Epoch 12** ($98.41\%$ accuracy, validation loss: $0.0962$). Subsequent epochs stabilized without overfitting.

### E.3. In-Distribution Evaluation Metrics (PlantVillage Laboratory Benchmark, $N=1,007$)

| Disease Class | Support ($N$) | Precision | Recall | F1-Score | Confusion Matrix Breakdown |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`Bacterial_spot`** | 425 | `0.9860` | `0.9929` | `0.9894` | 422 Correct, 0 as Early Blight, 3 as Late Blight |
| **`Early_blight`** | 200 | `0.9948` | `0.9600` | `0.9771` | 192 Correct, 2 as Bacterial Spot, 6 as Late Blight |
| **`Late_blight`** | 382 | `0.9767` | `0.9869` | `0.9818` | 377 Correct, 4 as Bacterial Spot, 1 as Early Blight |
| **Overall Macro Avg** | **1,007** | **`0.9858`** | **`0.9799`** | **`0.9828`** | **Overall Accuracy: `98.41%` (991/1007)** |

- **Subgroup Background Invariance:** Evaluated against 30 images with black backgrounds (Accuracy: `100.0%`) vs 977 normal background images (Accuracy: `98.36%`).

### E.4. External Benchmark & Real-World Domain Shift (PlantDoc Benchmark)
To evaluate realistic field generalization, the frozen ResNet-50 checkpoint was evaluated against independent in-the-wild photography from the **PlantDoc** benchmark (Singh et al., CoDS-COMAD 2020).

| Benchmark Split | Evaluation Nature | Sample Size ($N$) | Accuracy | Macro Precision | Macro Recall | Macro F1 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **PlantVillage Val** | Internal In-Distribution (Lab) | $1,007$ | **`98.41%`** | `0.9858` | `0.9799` | **`0.9828`** |
| **PlantDoc Official Test** | External Unconstrained (Field) | $28$ | **`39.29%`** | `0.2581` | `0.3815` | **`0.3079`** |
| **PlantDoc Combined** | Exploratory (Train + Test) | $309$ | **`48.22%`** | `0.5698` | `0.4931` | **`0.4012`** |

#### PlantDoc Official Test Split Per-Class Breakdown ($N=28$):
- **`Bacterial_spot` ($N=9$):** Precision `0.0000`, Recall `0.0000`, F1 `0.0000`. (0 predicted; 6 misclassified as Early Blight, 3 as Late Blight).
- **`Early_blight` ($N=9$):** Precision `0.3077`, Recall `0.4444`, F1 `0.3636`. (4 correct, 5 misclassified as Late Blight).
- **`Late_blight` ($N=10$):** Precision `0.4667`, Recall `0.7000`, F1 `0.5600`. (7 correct, 3 misclassified as Early Blight).

### E.5. Agronomic Failure Modes & Justification for Multi-Agent Architecture
Grad-CAM saliency mapping (`outputs/gradcam_analysis/`) revealed that on wide-angle outdoor imagery, the convolutional backbone activates strongly on background sky, soil clutter, and shadows rather than foliar lesions. Background masking (Phase 2) improved accuracy from $39.29\%$ to $50.00\%$, but 7 of 9 Bacterial Spot samples remained misclassified due to leaf chlorosis and sunlight glare.

**Crucial Agronomic Conclusion:** A single vision CNN cannot reliably make field decisions in isolation. This empirical failure directly validates AgriMind's multi-agent architecture: foliar classification confidence is cross-examined against micrometeorological weather data, canopy layer positioning, physical observation notes, and adaptive multi-turn reassessment before issuing chemical advisories.

---

## Section F: Database Development and Migration History

### F.1. Original SQLite Architecture (`data/cases.db`)
- **File Path:** `c:\Users\asus\Downloads\Agri_Mind_Minor_Project\data\cases.db`
- **File Size:** `2,686,976 bytes` (~2.68 MB)
- **Cryptographic SHA-256:** `87a0f05269f16d8de2d9a322fbdda7c9a7249e70e33d8baa7442ef5181bd0b2f` (100% untouched).
- **History:** Served as the initial monolithic development and test database, storing historical user accounts, case records, sharing tokens, and community tables.

### F.2. Cloud Target: Neon Serverless PostgreSQL 18.7
- **Host Endpoint:** `ep-rapid-bird-azbsdnm6-pooler.c-3.ap-southeast-1.aws.neon.tech`
- **Region:** AWS `ap-southeast-1` (Singapore)
- **Database Name:** `neondb`
- **Database Role:** `neondb_owner`
- **PostgreSQL Version:** `18.7 (a21afb5)` on aarch64-unknown-linux-gnu

### F.3. Schema DDL Evolution (V1 to V9)
- **V1 to V7 (Stages 3B.1.1–3B.1.13):** Designed table schemas, foreign keys, and indexes. Resolved SQLite-to-PostgreSQL syntax differences (`AUTOINCREMENT` -> `SERIAL`, `TEXT` -> `VARCHAR`/`TEXT`, `PRAGMA` -> `information_schema`).
- **V8 Candidate (Stage 3B.1.14):** Froze candidate script `execute_stage_3b2_ddl_v8.py`. During Stage 3B.2 execution, preflight failed on PostgreSQL 18.7 with `SQLSTATE 42725: operator is not unique: "char" || unknown` because PostgreSQL 18.7 changed operator resolution for internal `"char"` system catalog columns (`pg_class.relkind`, `pg_type.typtype`, `pg_proc.prokind`).
- **V9 Candidate (Stages 3B.2.1–3B.2.4):** Created `scratch/execute_stage_3b2_ddl_v9.py` adding explicit `::text` casts across the 13-catalog union query. Executed live on Neon on 2026-11-17 with exit code 0.

### F.4. Verified Canonical PostgreSQL Schema (12 Tables • 98 Columns)

| Table Name | Purpose | Column Count | Primary Key | Foreign Keys & Constraints |
| :--- | :--- | :---: | :--- | :--- |
| `users` | User identities, roles, authentication | 10 | `user_id` (TEXT) | `UNIQUE(email)`, `CHECK(role IN ('owner','sub_owner','admin','farmer'))` |
| `sub_owner_permissions` | Granular sub-owner capabilities | 5 | `user_id` (TEXT) | `FK -> users(user_id) ON DELETE CASCADE` |
| `revoked_tokens` | Blacklisted JWT session tokens | 2 | `token_id` (TEXT) | — |
| `audit_logs` | Governance and security trail | 8 | `log_id` (TEXT) | — |
| `cases` | Diagnostic cases & observations | 9 | `case_id` (TEXT) | — |
| `shared_cases` | Cooperative sharing grants | 11 | `share_id` (TEXT) | `FK -> cases(case_id) ON DELETE CASCADE` |
| `case_comments` | Cooperative notes & agronomist feedback | 7 | `comment_id` (TEXT) | `FK -> cases(case_id) ON DELETE CASCADE` |
| `case_outcomes` | Final verified crop resolution | 5 | `outcome_id` (TEXT) | `FK -> cases(case_id) ON DELETE CASCADE`, `UNIQUE(case_id)` |
| `community_posts` | Peer farmer social discussion posts | 14 | `post_id` (TEXT) | `FK -> users(author_id) ON DELETE CASCADE` |
| `community_comments` | Threaded discussion comments | 11 | `comment_id` (TEXT) | `FK -> community_posts(post_id) ON DELETE CASCADE` |
| `community_reactions` | Post and comment likes | 6 | `reaction_id` (TEXT) | `FK -> users(user_id) ON DELETE CASCADE` |
| `community_reports` | Moderation flags & abuse reports | 10 | `report_id` (TEXT) | `FK -> users(reporter_id) ON DELETE CASCADE` |

- **Secondary Indexes (11):** `idx_cases_created_at`, `idx_cases_owner_user_id`, `idx_shared_cases_target`, `idx_case_comments_case_id`, `idx_case_outcomes_case_id`, `idx_community_posts_created_at`, `idx_community_posts_author_id`, `idx_community_comments_post_id`, `idx_community_reactions_target`, `idx_community_reports_status`, `idx_audit_logs_timestamp`.

### F.5. Live Data Migration Execution & Verification (Stage 3B.3.2)
On 2026-11-17, candidate `scratch/migrate_sqlite_to_neon_data_v1.py` imported all historical records from `data/cases.db` to Neon PostgreSQL within a single atomic transaction.

| Table Name | Dependency Level | SQLite Source Count | Neon Destination Count | Discrepancy | Verification Status |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `users` | Level 0 (Root) | 2 | 2 | 0 | **100% MATCH** |
| `sub_owner_permissions` | Level 0 (Root) | 0 | 0 | 0 | **100% MATCH** |
| `revoked_tokens` | Level 0 (Root) | 0 | 0 | 0 | **100% MATCH** |
| `audit_logs` | Level 0 (Root) | 3 | 3 | 0 | **100% MATCH** |
| `cases` | Level 0 (Root) | 215 | 215 | 0 | **100% MATCH** |
| `shared_cases` | Level 0 (Root) | 17 | 17 | 0 | **100% MATCH** |
| `case_comments` | Level 0 (Root) | 26 | 26 | 0 | **100% MATCH** |
| `case_outcomes` | Level 0 (Root) | 3 | 3 | 0 | **100% MATCH** |
| `community_posts` | Level 1 (Depends on `users`) | 0 | 0 | 0 | **100% MATCH** |
| `community_reactions` | Level 1 (Depends on `users`) | 0 | 0 | 0 | **100% MATCH** |
| `community_reports` | Level 1 (Depends on `users`) | 0 | 0 | 0 | **100% MATCH** |
| `community_comments` | Level 2 (Depends on posts/users) | 0 | 0 | 0 | **100% MATCH** |
| **Total Database Records** | | **266** | **266** | **0** | **100% ROW PARITY** |

- **Integrity Highlights:**
  - `users` role distribution preserved: `{'farmer': 1, 'owner': 1}`.
  - `cases` distinct diagnoses: `3` classes; total reassessment count: `37`.
  - Date boundaries preserved: Earliest record `2026-11-01T05:41:42Z`, latest record `2026-11-04T09:34:50Z`.
  - Zero primary key collisions; zero foreign key orphans.

---

## Section G: Security and Reliability Improvements

### G.1. Authentication & Role-Based Access Control (RBAC)
- **Hierarchy:** 4 tiers (`owner` > `sub_owner` > `admin` > `farmer`).
- **Main Owner Supremacy:** Main Owner **Jaskirat Kour** (`USER-3FC32032`, `jaskiratkourjk2005@gmail.com`) holds immutable top-level governance. Sub-owners cannot demote the owner, elevate anyone to owner, or self-delegate permissions.
- **Configurable Sub-Owner Flags:** `can_manage_users`, `can_moderate_cases`, `can_view_telemetry`, `can_view_audit_logs`.
- **Immediate Token Invalidation:** When a sub-owner or admin is revoked, their role reverts to `farmer`, permissions are deleted, and active tokens are immediately rejected with `HTTP 403 Forbidden` without server restart.
- **Password Security:** Cryptographic password hashing using PBKDF2/bcrypt via `passlib`.

### G.2. SSRF Hardening & DNS Rebinding Protections (Stages 2M–2Q)
To secure the remote image diagnosis endpoint (`/api/v1/diagnose` via `image_url`), `src/api/routes.py:fetch_remote_image()` was completely overhauled:
1. **Scheme Validation:** Strict `https://` enforcement (plain HTTP and non-standard schemes rejected).
2. **IP Range Blacklisting:** Pre-resolution and filtering against RFC 1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.0/8`), link-local (`169.254.0.0/16`), and AWS/GCP cloud metadata services (`169.254.169.254`).
3. **DNS Rebinding (TOCTOU) Prevention:** Implemented a custom socket factory binding the HTTP connection directly to the pre-validated IP address, eliminating Time-of-Check to Time-of-Use DNS rebinding redirects.
4. **Validation Evidence:** 14 automated security tests in `tests/test_api_security.py` pass with a 100% block rate.

### G.3. Privacy-Preserving Case Sharing & GPS Fuzzing
- **Tokenized Access:** Cases shared with cooperatives generate cryptographically random 32-character tokens. Access is read-only and scope-restricted.
- **Foliar Location Privacy:** When farmers submit GPS coordinates with diagnostic requests, `src/services/case_sharing_service.py` automatically fuzzes coordinates:
  - Latitude and longitude are rounded to 1 decimal place ($\Delta \approx 0.0266^\circ$, providing a $\sim 3\text{ km}$ buffer).
  - Protects farmstead location and farmer PII while retaining regional epidemiological utility.

### G.4. PostgreSQL Transaction & Indexing Compatibility (Stage 3B.3.4 Patch)
- **Preventing Transaction Abort (`42701` -> `25P02`):** `CaseStore._init_db()` previously used an unguarded `ALTER TABLE cases ADD COLUMN owner_user_id TEXT;` wrapped in generic `try...except`. In PostgreSQL, a failing DDL statement places the transaction into an unrecoverable aborted state (`25P02`). The compatibility patch introduces `_column_exists()`, querying `information_schema.columns` before executing DDL.
- **Raw Connection Execution (`AttributeError`):** `routes.py:admin_system_status()` called `conn.execute()` on a raw `psycopg2` connection. The patch routes this call through `case_store.get_case_count()`.
- **Preventing `RealDictRow` Integer Indexing (`KeyError: 0`):** `DBConnectionWrapper` returns `psycopg2.extras.RealDictRow` objects which raise `KeyError` on integer indexing (`row[0]`). The patch replaces all occurrences in `auth_service`, `community_service`, and `routes.py` with explicit column aliases (`AS count`) and dictionary indexing (`row["count"]`, `row["comment_id"]`).

---

## Section H: Complete Change Log

The following table documents significant source-code modifications across the repository.

| File Path | Previous Behavior | New / Current Behavior | Reason for Modification | Associated Stage | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `src/api/routes.py` | Image submission cache key only hashed raw image bytes. | Cache key hashes image bytes + observation context (`field_notes`, `canopy`, etc.). | Prevent stale cache returns when same image submitted with different symptoms. | Stage B (Baseline) | Verified in `tests/test_cache_regression.py`. |
| `tests/test_feature2_vision_inference.py` | Cache polluted across test runs. | Explicit `_IMAGE_SUBMISSION_CACHE.clear()` called in `setUp()` and `tearDown()`. | Eliminate cross-test cache pollution. | Stage B (Baseline) | Verified in unit test execution. |
| `src/services/case_sharing_service.py` | `list_shared_cases` only accepted `str`. | Supports `Optional[List[str]]` for batch status queries. | Harmonize service signature with route requirements. | Stage B (Baseline) | Verified in `tests/test_case_sharing.py`. |
| `src/services/auth_service.py` | Monolithic SQLite-only queries with `?` placeholders. | Uses `DBConnectionWrapper`; auto-swaps `?` and `%s` based on `is_postgres`. | Enable dual-engine support for SQLite and PostgreSQL. | Stage 2K / 3B.1.22 | Verified in `test_stage_3b_1_20_compatibility.py`. |
| `src/services/community_service.py` | Monolithic SQLite-only queries with `?` placeholders. | Uses `DBConnectionWrapper`; auto-swaps `?` and `%s` based on `is_postgres`. | Enable dual-engine support for SQLite and PostgreSQL. | Stage 2K / 3B.1.22 | Verified in `test_stage_3b_1_20_compatibility.py`. |
| `src/api/routes.py` | Raw `requests.get()` fetched image URLs without validation. | Strict HTTPS enforcement, private IP blacklisting, DNS IP pinning, and socket binding. | Eliminate critical SSRF and DNS rebinding vulnerabilities. | Stages 2M–2Q | 14/14 tests passed in `tests/test_api_security.py`. |
| `android/.../RetrofitClient.kt` | Hardcoded localhost / emulator IP `10.0.2.2`. | Dynamic configurable base URL with cloud fallback capability. | Support laptop-independent mobile cloud operation. | Stage 2D | Verified in Android source inspection. |
| `android/.../network_security_config.xml` | Restricted cleartext traffic. | Explicit domain inclusions for local emulator and cloud API endpoints. | Allow mobile communication with backend during development. | Stage 2D | Verified in Android XML manifest audit. |
| `requirements-prod.txt` | Standard development dependencies. | Added `psycopg2-binary>=2.9.9` and production serverless packages. | Support cloud PostgreSQL connections in production. | Stages 2A / 3B.3.4 | Dependency declaration verified. |
| `src/api/case_store.py` *(Proposed Patch)* | Unguarded `ALTER TABLE` aborted PostgreSQL transactions. | Adds `_column_exists()` guard; skips `ALTER TABLE` if column exists. | Prevent `DuplicateColumn (42701)` and `InFailedSqlTransaction (25P02)`. | Stage 3B.3.4 | `PROPOSED PATCH APPROVED — PENDING APPLICATION` |
| `src/api/routes.py` *(Proposed Patch)* | Called `conn.execute()` on raw psycopg2 connection. | Replaced with `case_store.get_case_count()`. | Prevent `AttributeError` on raw psycopg2 connections. | Stage 3B.3.4 | `PROPOSED PATCH APPROVED — PENDING APPLICATION` |
| `src/services/auth_service.py` *(Proposed Patch)* | Accessed aggregate counts via `row[0]`. | Queries use `AS count`; accessed via `row["count"]`. | Prevent `KeyError: 0` on `RealDictRow`. | Stage 3B.3.4 | `PROPOSED PATCH APPROVED — PENDING APPLICATION` |
| `src/services/community_service.py` *(Proposed Patch)* | Accessed counts and IDs via `row[0]`. | Queries use `AS count` and `row["comment_id"]`. | Prevent `KeyError: 0` on `RealDictRow`. | Stage 3B.3.4 | `PROPOSED PATCH APPROVED — PENDING APPLICATION` |

---

## Section I: Testing and Verification History

AgriMind maintains extensive unit, integration, and security test suites across Python backend and Android subsystems.

### I.1. Automated Test Execution Summary

| Test Suite / Runner | Target Domain | Total Tests | Passed | Failed | Errors | Execution Duration | Verified In This Audit |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Stage 3B.3.4 Focused Compatibility** | PostgreSQL Engine Fixes | **10** | **10** | 0 | 0 | $0.078\text{ s}$ | **YES (LIVE VERIFIED)** |
| **Combined Offline Regression** | Auth, Sharing, Postgres v1, v2 | **35** | **35** | 0 | 0 | $1.772\text{ s}$ | **YES (LIVE VERIFIED)** |
| **Stage 3B.1.19 Data Migration Suite** | SQLite-to-Neon Migration Logic | **26** | **26** | 0 | 0 | $0.320\text{ s}$ | Recorded in `STAGE_3B_1_19` Report |
| **Stage 3B.2.1 V9 DDL Validation** | PostgreSQL 18.7 DDL Offline Check | **22** | **22** | 0 | 0 | $0.185\text{ s}$ | Recorded in `STAGE_3B_2_1` Report |
| **Stage 2Q Security & SSRF Suite** | SSRF & DNS Rebinding Protections | **14** | **14** | 0 | 0 | $0.450\text{ s}$ | Recorded in `STAGE_2Q` Report |
| **Android Unit Suite (`testDebugUnitTest`)** | ViewModels, Models, Repositories | **68** | **68** | 0 | 0 | $28.00\text{ s}$ | Recorded in Community Release Report |
| **Full Backend Suite (WSL Python 3.13)** | End-to-End Workflow & Agents | **218** | **182** | 33 | 3 | $564.76\text{ s}$ | Recorded in `agrimind_verified_baseline.md` |

### I.2. Live Audit Test Execution Output
During this documentation inspection on 2026-11-18, the focused PostgreSQL compatibility suite and offline regression suite were executed live in the local environment:

```
$ python -m unittest scratch/test_stage_3b_3_4_postgresql_compatibility.py -v
test_01_column_exists_sqlite_detection ... ok
test_02_postgres_column_exists_skips_alter_table ... ok
test_01_raw_psycopg2_connection_lacks_execute ... ok
test_02_get_case_count_avoids_conn_execute ... ok
test_03_sharing_service_comments_count_named_access ... ok
test_01_community_feed_total_count_named_access ... ok
test_02_auth_service_system_stats_named_access ... ok
test_03_community_delete_comment_id_extraction ... ok
test_01_sqlite_supports_count_as_count_indexing ... ok
test_02_sqlite_supports_comment_id_indexing ... ok
----------------------------------------------------------------------
Ran 10 tests in 0.078s -- OK

$ python -m unittest tests/test_auth_and_roles.py tests/test_case_sharing.py scratch/test_stage_3b_1_20_compatibility.py scratch/test_stage_3b_3_4_postgresql_compatibility.py
...................................
----------------------------------------------------------------------
Ran 35 tests in 1.772s -- OK
[PRIVACY] GPS Fuzzing: 32.726612 -> 32.7 (delta: 0.0266 deg, buffer: 2.96 km)
```

---

## Section J: Cloud and Deployment History

### J.1. Cloud Architecture Decisions & Free-Tier Compliance
AgriMind was designed for **100% free-tier operation (strictly ₹0.00 / $0.00 budget)**:
1. **Compute (FastAPI Backend):** Vercel Serverless Functions (Hobby Tier: 100k invocations/day, zero idle cost). Configured via `vercel.json` pointing builds to `api/index.py`.
2. **Relational Database:** Neon Serverless PostgreSQL (Free Tier: 0.5 GiB storage, automatic scale-to-zero when inactive). Host: `ep-rapid-bird-azbsdnm6-pooler.c-3.ap-southeast-1.aws.neon.tech`.
3. **Object Storage:** Supabase Storage (Free Tier: 1 GB storage, 2 GB bandwidth/month). Bucket `agrimind-crop-images` for leaf photo uploads.
4. **LLM Inference:** Google Gemini API (Free Tier: 15 RPM / 1M TPM for Gemini 1.5 Flash). Fallback: Grounded extractive synthesis when quota exhausted.
5. **Mobile Client:** Native Android APK distributed directly via GitHub Releases or local side-loading.

### J.2. Deployment Work Completed
- GitHub remote repository connected and synchronized: `origin/main` at `https://github.com/JaskiratKourA3-29/AgriMind.git`.
- Vercel deployment configuration created (`vercel.json`, `api/index.py`).
- Neon Serverless PostgreSQL 18.7 instance provisioned, schema created (12 tables, 98 columns), and 266 historical records migrated.
- Supabase storage bucket `agrimind-crop-images` provisioned and verified.
- Android production network security manifest configured.

### J.3. Deployment Work Pending & Laptop-Independent Operation Requirements
To achieve complete laptop-independent operation where the Android mobile app operates without running a local backend on the developer's laptop:
1. **Apply Approved Compatibility Patch:** Apply `scratch/stage_3b_3_4_postgresql_compatibility_patch.diff` to resolve runtime PostgreSQL blockers.
2. **Deploy Backend to Vercel:** Link the GitHub repository to Vercel, inject cloud environment variables (`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_KEY`, `GEMINI_API_KEY`, `JWT_SECRET`), and trigger a production deployment.
3. **Point Android to Production URL:** Update `DEFAULT_BASE_URL` in `android/app/src/main/java/com/agrimind/app/data/api/RetrofitClient.kt` to the live Vercel domain (`https://agrimind-api.vercel.app/`).
4. **Compile Production APK:** Run `./gradlew assembleRelease` to package the final APK for smallholder field testing.

---

## Section K: Current Project Status

| Subsystem / Component | Current Verified Status | Primary Implementation File(s) | Status Evidence & Notes |
| :--- | :--- | :--- | :--- |
| **ResNet-50 Vision Model** | `IMPLEMENTED AND VERIFIED` | `outputs/week2_vision/best_model.pth`, `src/vision/inference.py` | 282.6 MB weights verified on disk; 98.41% accuracy on PlantVillage. |
| **ChromaDB Agricultural RAG** | `IMPLEMENTED AND VERIFIED` | `data/vectorstore/chroma/`, `src/rag/generator.py` | 63 chunks verified; 100% hit-rate at k=4 across 15 domain queries. |
| **LangGraph Reasoning Workflow** | `IMPLEMENTED AND VERIFIED` | `src/workflow/graph.py`, `nodes.py`, `state.py` | 10-node StateGraph compiles; multi-agent execution tested. |
| **Adaptive Reassessment Engine**| `IMPLEMENTED AND VERIFIED` | `src/workflow/nodes.py`, `CaseDetailScreen.kt` | 37 live reassessments verified in database; trajectory logic tested. |
| **Native Android Mobile App** | `IMPLEMENTED AND VERIFIED` | `android/app/src/main/java/com/agrimind/app/**` | 10 Compose screens; 68 unit tests passed; debug APK compiled. |
| **Bilingual Vernacular Voice** | `IMPLEMENTED AND VERIFIED` | `LanguageDetector.kt`, `ChatScreen.kt`, `generator.py` | STT/TTS verified in English and Hindi with Devanagari script detection. |
| **On-Device PDF Report Generator**| `IMPLEMENTED AND VERIFIED` | `android/.../report/PdfReportGenerator.kt` | Native A4 PDF generation with Canvas vector graphics and QR codes. |
| **RBAC & Sub-Owner Governance** | `IMPLEMENTED AND VERIFIED` | `src/services/auth_service.py`, `AdminDashboardScreen.kt` | Main Owner supremacy + granular sub-owner capability flags verified. |
| **Farmer Community Platform** | `IMPLEMENTED AND VERIFIED` | `src/services/community_service.py`, `CommunityScreen.kt`| Social feed, posts, comments, likes, and solution acceptance verified. |
| **SSRF Image Security** | `IMPLEMENTED AND VERIFIED` | `src/api/routes.py:fetch_remote_image` | 14/14 security tests passed; private IP blacklisting and DNS pinning verified. |
| **Neon PostgreSQL Cloud Schema** | `IMPLEMENTED AND VERIFIED` | `scratch/execute_stage_3b2_ddl_v9.py` | 12 tables, 98 columns, 12 PKs, 11 indexes verified live on Neon. |
| **Neon PostgreSQL Data Migration** | `IMPLEMENTED AND VERIFIED` | `scratch/migrate_sqlite_to_neon_data_v1.py` | 266 application rows imported with 100% table-by-table parity. |
| **PostgreSQL App Compatibility** | `PREPARED — READY TO APPLY` | `scratch/stage_3b_3_4_postgresql_compatibility_patch.diff`| Patch independently audited and approved (`STAGE_3B_3_5`); unapplied. |
| **Vercel Serverless Deployment** | `PARTIALLY IMPLEMENTED` | `vercel.json`, `api/index.py` | Configuration files verified; live deployment pending owner authorization. |
| **Supabase Image Storage** | `IMPLEMENTED — VERIFICATION INCOMPLETE` | `.env.cloud.template`, `DiagnosisViewModel.kt` | Bucket provisioned; live mobile upload integration pending cloud deployment. |

---

## Section L: Pending Work and Known Issues

### L.1. Essential Work (Immediate Deployment Blockers)
1. **Apply Approved Compatibility Patch:** Under owner authorization, apply `scratch/stage_3b_3_4_postgresql_compatibility_patch.diff` to eliminate `CaseStore` startup transaction aborts, raw `conn.execute()` calls, and `RealDictRow` integer indexing failures.
2. **Install PostgreSQL Driver in Deployment Environment:** Ensure `psycopg2-binary>=2.9.9` is packaged in the Vercel serverless container.
3. **Execute Live Vercel Deployment:** Link GitHub repository to Vercel, inject cloud credentials, and trigger initial serverless build.
4. **Configure Android Production Endpoint:** Update `RetrofitClient.kt` to target the live Vercel URL and verify end-to-end communication from a physical Android device.

### L.2. Important Improvements (Post-Deployment Hardening)
1. **Live Cloud Integration Testing:** Execute an end-to-end diagnosis request and community post creation against live Vercel + Neon to confirm real-world performance.
2. **Install Local Test Dependencies:** Install `fastapi` and `psycopg2-binary` in the local development environment to enable running the entire 218-test backend suite directly without WSL.
3. **Background Sync Worker:** Enhance `OfflineQueueManager.kt` with Android `WorkManager` for guaranteed background retry when offline cases are queued.

### L.3. Future Scope (Academic & Agronomic Expansion)
1. **Multi-Crop Expansion:** Extend vision training beyond tomato to include potato (*Solanum tuberosum*) and bell pepper (*Capsicum annuum*) foliar diseases.
2. **On-Device Quantized Inference:** Quantize ResNet-50 to TensorFlow Lite (TFLite) or ONNX Runtime INT8 for local offline vision inference directly on farmer smartphones.
3. **Regional Dialect STT:** Expand speech recognition models to support regional dialects such as Dogri and Gojri.

---

## Section M: Final Technical Snapshot

### M.1. Technology Stack & Verified Versions
- **Programming Languages:** Python `3.13.x` (Backend/ML), Kotlin `1.9.x` (Android Mobile).
- **Deep Learning Framework:** PyTorch `2.x`, torchvision, CUDA-accelerated training.
- **Agent Orchestration:** LangGraph `0.2.x`, LangChain Core, Pydantic `2.x`.
- **Vector Database & Embeddings:** ChromaDB `0.5.x`, Sentence-Transformers (`all-MiniLM-L6-v2`).
- **Web Framework:** FastAPI `0.115.x`, Starlette, Uvicorn, Requests.
- **Relational Databases:** SQLite `3.x` (Local), PostgreSQL `18.7` (Neon Serverless Cloud).
- **Mobile Framework:** Android SDK 34 (Android 14), Jetpack Compose (Material 3), Retrofit 2, OkHttp 3, Coroutines & StateFlow.
- **Cloud Infrastructure:** Vercel (Serverless Compute), Neon (Serverless Postgres), Supabase (Object Storage), GitHub Actions.

### M.2. Key Repository Paths & Entry Points
- **FastAPI Application:** `src/api/app.py`, `src/api/routes.py`
- **Vercel Serverless Entry Point:** `api/index.py`, `vercel.json`
- **Vision Inference:** `src/vision/inference.py`, `outputs/week2_vision/best_model.pth`
- **LangGraph StateGraph:** `src/workflow/graph.py`, `src/workflow/nodes.py`, `src/workflow/state.py`
- **RAG Engine:** `src/rag/generator.py`, `src/rag/retriever.py`, `data/vectorstore/chroma/`
- **Android Entry Point:** `android/app/src/main/java/com/agrimind/app/MainActivity.kt`
- **Android PDF Generator:** `android/app/src/main/java/com/agrimind/app/report/PdfReportGenerator.kt`
- **Local Database:** `data/cases.db` (SHA-256: `87a0f05269f16d8de2d9a322fbdda7c9a7249e70e33d8baa7442ef5181bd0b2f`)
- **Approved Compatibility Patch:** `scratch/stage_3b_3_4_postgresql_compatibility_patch.diff` (SHA-256: `fab0cab1adc2aa433d77941953998466deadeb77764cc935e08a1a96219d7b79`)
- **Live Cloud Endpoint:** `ep-rapid-bird-azbsdnm6-pooler.c-3.ap-southeast-1.aws.neon.tech` (`neondb`, PostgreSQL 18.7)

### M.3. Current Known Blockers
- **Pending Patch Application:** `stage_3b_3_4_postgresql_compatibility_patch.diff` must be applied under explicit owner authorization before running against Neon in production.
- **Cloud Backend Deployment:** FastAPI backend has not yet been deployed to Vercel.

---

## Section N: Evidence and Accuracy Notes

### N.1. Evidence Hierarchy & Distinction of Claims
Every statement, metric, and status in this document is derived strictly from direct file inspection, live test execution, git history, or verified historical stage reports:
1. **Directly Inspected & Verified Facts:**
   - ResNet-50 checkpoint size (`282,626,785 bytes`) and validation metrics (Accuracy: `98.41%`, loss: `0.0962`).
   - SQLite database size (`2,686,976 bytes`) and SHA-256 hash (`87a0f052...`).
   - Candidate patch SHA-256 (`fab0cab1...`) and test suite SHA-256 (`0e9d1a8c...`).
   - Clean `git apply --check` dry-run (exit code 0).
   - Live test execution: 10/10 focused compatibility tests passed ($0.078\text{ s}$), 35/35 regression tests passed ($1.772\text{ s}$).
   - Working tree state: 11 modified files, 3 untracked files, zero patch contamination.
2. **Documented Historical Results (from Frozen Stage Reports):**
   - Live Neon PostgreSQL 18.7 schema execution (`STAGE_3B_2_4_V9_SCHEMA_EXECUTION_REPORT.md`): 12 tables, 98 columns verified.
   - Live SQLite-to-Neon data migration (`STAGE_3B_3_2_DATA_MIGRATION_EXECUTION_REPORT.md`): 266 application rows imported with 100% parity.
   - SSRF security audit (`STAGE_2Q` Report): 14/14 tests passed with 100% block rate.
   - Android acceptance tests (`STAGE_C5` Report): 94/94 tests passed, clean APK assembled.
3. **Planned Work (Explicitly Distinguished):**
   - Production Vercel deployment has not been executed.
   - Stage 3B.3.4 compatibility patch has been approved but **not applied** to application files.
   - Supabase mobile image upload integration is planned for post-deployment verification.

### N.2. Confirmation of Immutability
During the preparation and generation of this comprehensive project documentation:
- **Zero source files were edited.**
- **Zero pending patches were applied.**
- **Zero database DDL or DML statements were executed.**
- **Zero cloud connections to Neon, Vercel, or Supabase were initiated.**
- **Zero credentials, tokens, connection strings, or `.env` secrets were exposed.**
- **Zero Git state changes were made (no adds, commits, resets, or pushes).**
- **Zero budget was consumed (strictly ₹0.00 / $0.00).**
- **Existing working tree modifications and untracked files were preserved completely intact.**

---
*End of Complete Project History, Technical Development & Current Status Report for AgriMind.*