# AgriMind Stage C.3 — Expandable Reassessment History Timeline Milestone Report

**Date:** November 2, 2026  
**Status:** Completed & Fully Verified  
**Target Architecture:** Native Android (Kotlin, Jetpack Compose, Material 3, SQLite)  
**Execution Environment:** Android Emulator (`emulator-5554`), Windows 11 host  

---

## 1. Executive Summary

Stage C.3 delivers an **Expandable Chronological Reassessment History Timeline** on the Android `CaseDetailScreen`. Prior to this milestone:
1. Reassessment history was presented as a flat, uncollapsible list card shown only when `reassessmentCount > 0`.
2. Cases with zero reassessments rendered nothing, leaving the agronomist unaware of whether reassessments were available or what the baseline diagnostic state was.
3. Progressive severity shifts (e.g. `INDETERMINATE → CRITICAL`), trigger categories, rationale, and specific new evidence entries were not visually integrated into a timeline flow.

In Stage C.3, we implemented an expandable/collapsible, chronological vertical timeline connecting the initial diagnostic baseline directly to subsequent reassessment cycles. The timeline strictly visualizes persisted data fields without fabricating values, handles cases with no reassessments gracefully, and passed all unit and emulator integration tests.

---

## 2. Data Model Audit & Field Verification

Before modifying UI code, we audited `LocalCaseRecord.kt`, `ReassessmentModels.kt`, and `DiagnosisResponse.kt` to establish exactly which fields are persisted on disk:

### 2.1 Stored Diagnostic Baseline (Cycle #0)
In `LocalCaseRecord`:
- `createdAtIso`: ISO-8601 timestamp of original image submission (e.g., `2026-11-01T18:54:16Z`).
- `primaryDiagnosis`: Model predicted class (e.g., `Tomato___Late_blight`).
- `diagnosisConfidence`: Floating-point probability (e.g., `1.0`).
- `assignedSeverity`: Initial severity assessed by Risk Assessment Agent (e.g., `indeterminate`).
- `epidemicRisk`: Initial epidemic risk assessed (e.g., `high`).
- `planUrgency`: Urgency level of initial IPM plan (e.g., `high`).

### 2.2 Stored Reassessment Cycles (Cycles #1..N)
In `LocalCaseRecord.reassessmentHistory: List<ReassessmentResponse>`:
- `reassessmentCount`: Integer cycle counter (1 or 2).
- `reassessmentOutcome`: Categorical outcome string (`"revised"`, `"confirmed"`, or `"escalated"`).
- `assignedSeverity`: Revised severity (e.g., `critical`).
- `epidemicRisk`: Revised risk (e.g., `critical`).
- `planUrgency`: Revised urgency (e.g., `critical`).
- `reassessmentRecords: List<ReassessmentRecordItem>?`:
  - `trigger`: String identifier (e.g., `"weather_update"`, `"new_field_observation"`, `"treatment_ineffective"`).
  - `triggerRationale`: String rationale supplied during submission (e.g., `"Foliar damage increased to 50%"`).
  - `priorSeverity`: Recorded prior severity before cycle revision (e.g., `"indeterminate"` or `"severe"`).
  - `revisedSeverity`: Revised severity after cycle execution (e.g., `"critical"`).
  - `priorDiagnosis` & `revisedDiagnosis`: Diagnoses before and after reassessment.
  - `timestamp`: ISO-8601 timestamp of reassessment execution.
  - `newEvidence`: Map of field attributes updated during reassessment (e.g., `weather_conditions`, `leaf_damage_percentage`, `canopy_spread`).

### 2.3 Unrecorded / Missing Field Boundaries
- **No Fabricated Data:** If `triggerRationale` is null, no quote block is displayed. If `newEvidence` is empty, no evidence summary is injected.
- **Timestamp Graceful Fallback:** If `timestamp` is missing or unparseable, the system displays `"Timestamp not recorded"` or preserves the raw string without crashing.

---

## 3. Technical Implementation

### 3.1 Jetpack Compose Timeline Architecture (`CaseDetailScreen.kt`)
1. **Interactive Header with Expand/Collapse State:**
   - Wrapped inside `Card` with `SurfaceCard` container and `ForestGreenLight` border.
   - Header `Row` displays `Icons.Default.History`, `"Reassessment History Timeline"`, and subtitle `"${caseRecord.reassessmentCount} of 2 cycles completed"`.
   - Default expanded state: Expanded if `reassessmentCount > 0`; can be toggled by tapping anywhere on the header row or on the `ExpandLess`/`ExpandMore` IconButton.
2. **Dynamic Height Vertical Timeline (`TimelineNodeItem`):**
   - Utilizes `Row(modifier = Modifier.fillMaxWidth().height(IntrinsicSize.Min))` paired with `Column(modifier = Modifier.width(36.dp).fillMaxHeight())`.
   - An indicator circle displays the cycle icon (`Icons.Default.Flag` for baseline, `Icons.Default.Update` for reassessments) with custom badge colors.
   - The vertical connecting line (`Box(modifier = Modifier.width(2.dp).weight(1f))`) automatically stretches to match the dynamic height of the content column, preventing broken or overlapping connector lines.
3. **Severity Shift Indicators:**
   - Where `priorSeverity != revisedSeverity`, displays a clear directional shift:
     `Prior: MODERATE → Revised: CRITICAL`
   - Outcome badge (`REVISED`, `CONFIRMED`, `ESCALATED`, `BASELINE`) rendered in high-contrast colored chips.
4. **Empty Reassessment State Notice:**
   - When `reassessmentCount == 0`, the timeline renders the Baseline Node followed by an informative notice box:
     `"No adaptive reassessments recorded. This case is operating on initial baseline evidence. 2 of 2 reassessments available."`

### 3.2 Unit Test Helpers (`CaseDetailScreen.kt`)
- `formatTimelineTimestamp(isoString: String?): String`: Parses ISO-8601 strings (both UTC `'Z'` and fractional seconds) into clean human-readable dates (e.g., `Nov 2, 2026 • 12:24 AM`), handling nulls and malformed inputs safely.
- `formatTriggerLabel(rawTrigger: String?): String`: Maps enum triggers (`weather_update` $\rightarrow$ `"Weather Update"`, `new_field_observation` $\rightarrow$ `"New Field Observation"`) with snake_case fallback.

### 3.3 ViewModel Optimization (`CaseDetailViewModel.kt`)
- Configured `repository` and `pdfGenerator` as `lazy` delegates (`by lazy`), enabling lightweight, deterministic JVM unit testing of `CaseDetailViewModel` without requiring Android Context mocks.

---

## 4. Verification & Testing Evidence

### 4.1 Android Unit Test Suite (`CaseDetailViewModelTest.kt`)
Added 7 comprehensive unit tests in `android/app/src/test/java/com/agrimind/app/ui/viewmodel/CaseDetailViewModelTest.kt`:
1. `testInitialState_isIdle`: Confirms `activeCase == null`, `reassessmentState is Idle`, `pdfExportState is Idle`.
2. `testSetCase_updatesActiveCase`: Confirms setting a `LocalCaseRecord` populates `activeCase` and resets states.
3. `testResetStates_revertsToIdle`: Confirms reset helper methods.
4. `testFormatTriggerLabel_mapsKnownAndUnknownTriggers`: Verifies trigger enum mappings and null fallbacks.
5. `testFormatTimelineTimestamp_formatsIsoDatesCleanly`: Verifies ISO parsing, fractional seconds, and null/malformed safety.
6. `testTimelineEmptyHistory_preservesBaselineIntegrity`: Verifies 0-cycle baseline data integrity.
7. `testTimelineMultiCycleReassessment_preservesChronologicalEvolution`: Validates 2-cycle chronological evolution, severity transitions (`MODERATE → SEVERE → CRITICAL`), and trigger mapping.

**Unit Test Results:**
- `DiagnosisViewModelTest`: 7 passed
- `ChatViewModelTest`: 30 passed
- `CaseDetailViewModelTest`: 7 passed
- **Total:** `44/44 passed (BUILD SUCCESSFUL in 54s)`

### 4.2 Backend Test Suite Regression (`tests/test_api.py`)
- Full backend suite ran in WSL2 environment: `Ran 29 tests in 82.483s: OK (0 failures, 0 errors)`.

### 4.3 Live Android Emulator Verification (`emulator-5554`)
1. **Live Case Inspection (`CASE-7DC903FC`):**
   - Navigated to History tab $\rightarrow$ tapped `CASE-7DC903FC` (Late Blight, reassessed 2x).
   - **Expanded Timeline View:**
     - Baseline Node: `Nov 2, 2026 • 12:24 AM`, `Severity: INDETERMINATE`, `Risk: HIGH`, `Trigger: Initial Specimen Submission`.
     - Cycle #1 Node: `Nov 1, 2026 • 7:10 PM`, `Trigger: Weather Update`, `Prior: INDETERMINATE → Revised: CRITICAL`, `Evidence: weather conditions: cool_wet, leaf damage percentage: 25.0, canopy spread: mid_canopy`.
     - Cycle #2 Node: `Nov 1, 2026 • 7:10 PM`, `Trigger: Weather Update`, `Late blight (100%)`.
   - Verified screenshot: [`docs/stage_c3_reassessment_timeline_expanded.png`](file:///docs/stage_c3_reassessment_timeline_expanded.png).
2. **Interactive Collapse/Expand:**
   - Tapped timeline header: Section collapsed smoothly, reducing vertical height and positioning the IPM plan directly below the header.
   - Verified screenshot: [`docs/stage_c3_reassessment_timeline_collapsed.png`](file:///docs/stage_c3_reassessment_timeline_collapsed.png).
   - Tapped again: Section expanded smoothly back to full timeline view.

---

## 5. Summary of Changed Files

| File Path | Component | Changes Made |
|:---|:---|:---|
| `android/.../CaseDetailScreen.kt` | Android UI | Replaced flat audit card with `ReassessmentTimelineSection`, `TimelineNodeItem`, `OutcomeBadge`, `SeverityBadge`, `RiskBadge`, and date/trigger formatters. |
| `android/.../CaseDetailViewModel.kt` | Android ViewModel | Converted `repository` and `pdfGenerator` to lazy delegates for unit test isolation. |
| `android/.../CaseDetailViewModelTest.kt` | Android Tests | Added 7 unit tests covering timeline state, empty-history integrity, multi-cycle evolution, and formatting logic. |

---

## 6. Remaining Limitations & Boundaries
1. **Reassessment Quota:** The platform strictly enforces a maximum of 2 reassessments per case (`maxReassessments = 2`). The timeline reflects this constraint (`"${reassessmentCount} of 2 cycles completed"`).
2. **Preserved Boundaries:** ResNet-50 weights, datasets, disease classes, RAG vector stores, PDF export, and chat integration remain 100% intact and untouched. Postponed multi-crop expansion and Hindi voice improvements were not started.

