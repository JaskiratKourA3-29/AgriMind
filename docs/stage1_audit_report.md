# AgriMind Stage 1 — Workspace & Environment Audit Report

**Date & Time:** October 13, 2026 | 12:15 IST  
**Project:** AgriMind — Multi-Agent AI System for Crop Disease Investigation, Risk Assessment & Adaptive Decision Support  
**Course Code:** COM71116-21 (7th-Semester CSE Minor Project)  
**Team:** Jaskirat Kour (Team Leader), Palakjot Kour, Sayam Malhotra, Ikjot Singh  
**Stage:** Stage 1 (Workspace Audit + EDA on Three Datasets)

---

## 1. Executive Summary & Audit Status

Every item in the workspace, environment, filesystem, and database was inspected directly using read-only and non-destructive operations. No files or repositories were moved, renamed, overwritten, or deleted.

| Component / Artifact | Status | Verified Location / Observation |
|---|---|---|
| **AgriMind Workspace** | **Verified (Clean)** | `c:\Users\asus\Downloads\Agri_Mind_Minor_Project` (Windows). Originally empty; now contains `scripts/` and `docs/`. |
| **Git Version Control** | **Verified** | Git is installed in system. Workspace was not yet a git repository (`fatal: not a git repository`). |
| **Operating System** | **Verified** | Ubuntu 26.04.1 LTS under WSL2 (kernel `6.18.33.2-microsoft-standard-WSL2`, x86_64). |
| **Python Environments** | **Verified** | Pyenv interpreter `3.13.16` with virtual environment `fiftyone-env`. Virtualenv `agrimind-eda` exists at `/home/jaskirat/agrimind-eda` and was preserved untouched. |
| **MongoDB Service** | **Verified & Functional** | Standalone MongoDB 8.0.17 at `/home/jaskirat/agrimind-fiftyone-eda/mongodb/bin/mongod` (SHA256: `4bebd8cb4cfe06b256f6bd7dd574c9c925d618e8e4f4f81d6dedb859fe46ac99`), data directory size: 204 MB. Successfully binds to `127.0.0.1:27018`. |
| **FiftyOne Dataset** | **Verified** | `plantvillage_tomato3` exists persistently in MongoDB with exactly 5,036 samples, all schema fields, and 8 sample tag categories. |
| **PlantVillage Dataset** | **Verified Local Copy** | `/mnt/c/Users/asus/PlantVillage-Dataset/raw/color` (Windows: `C:\Users\asus\PlantVillage-Dataset\raw\color`). |
| **Tomato-Village Dataset** | **Verified Local Copy** | `/home/jaskirat/datasets/Tomato-Village` (Contains Variants A, B, and C). |
| **PlantDoc Dataset** | **Verified Local Copy** | `/home/jaskirat/PlantDoc-Dataset` (Contains `train/` and `test/` splits). |
| **Existing EDA Artifacts** | **Verified** | All 5 files in `/home/jaskirat/agrimind-fiftyone-eda/outputs/` verified intact (refused overwrite). |
| **Prior Experiments E0-E5** | **Not Found** | Searched `/home/jaskirat` and Windows directories. No code, scripts, or experiment logs exist on disk. |
| **Reported PlantVillage Split Lists** | **Not Found** | Searched `/home/jaskirat` and Windows. The stratified 80/20 file lists (4,029 / 1,007) do not exist as saved files on disk. |

---

## 2. Environment & Service Details

### 2.1 WSL & Python Environment
- **WSL Distribution:** Ubuntu 26.04.1 LTS
- **Pyenv Root:** `/home/jaskirat/.pyenv`
- **Active Environment for EDA:** `/home/jaskirat/.pyenv/versions/fiftyone-env` (Python 3.13.16, FiftyOne 1.22.1, PyMongo 4.9.2, Pillow, Pandas, NumPy, Scikit-image, OpenCV-python-headless).
- **Untouched Environment:** `/home/jaskirat/agrimind-eda` was identified as a Python virtualenv and was preserved without any access or modification.

### 2.2 MongoDB Architecture & Behavior under WSL2
- **Binary:** `/home/jaskirat/agrimind-fiftyone-eda/mongodb/bin/mongod`
- **Startup Script:** `/home/jaskirat/agrimind-fiftyone-eda/scripts/start_mongod.sh`
- **Port:** `127.0.0.1:27018`
- **WSL Session Lifecycle Observation:** In WSL2 without active systemd keep-alive or open interactive shell sessions, background processes spawned by transient WSL commands are terminated by `init (PID 1)` via SIGTERM when the session terminates. Starting mongod within the execution wrapper or maintaining an active WSL session maintains mongod connectivity reliably.

---

## 3. Prior Experiments & Historical Artifacts Audit

1. **Vision Agent Experiments E0–E5:**
   - Exhaustive searches across `/home/jaskirat` and `C:\Users\asus` revealed no model weights, training checkpoints, training scripts, or log files for ResNet-50 experiments E0–E5.
   - Status: **Not Found**. Per project rules, no results for E0–E5 are assumed or reported.
2. **PlantVillage 80/20 Train/Validation Split:**
   - The reported split counts (train 4,029, val 1,007; Bacterial 1702/425, Early 800/200, Late 1527/382) represent a exact 80.00% / 20.00% stratified split of 5,036 samples.
   - Exhaustive search of `/home/jaskirat/.bash_history` and filesystem revealed that no file list (CSV, JSON, TXT) was ever saved on disk.
   - Status: **Not Found on Disk**. Requires explicit generation and approval before Week 2.

---

## 4. What Is Safe to Do Next & Blockers

- **Safe to do:** Complete Stage 1 documentation, summarize EDA across all three datasets, and formulate a rigorous data preparation proposal.
- **Blockers needing User Decision:**
  1. Authorizing the generation of the stratified train/validation split file list for PlantVillage.
  2. Deciding on the treatment of the 153 non-.JPG Late blight cutout images (with 150 dark-background images).
  3. Formal sign-off on Stage 1 before transitioning to Stage 2 (Week 2 Vision Agent).
