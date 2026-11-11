package com.agrimind.app.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.agrimind.app.data.api.RetrofitClient
import com.agrimind.app.data.model.CaseShareRequest
import com.agrimind.app.data.model.CaseShareResponse
import com.agrimind.app.data.model.CaseComment
import com.agrimind.app.data.model.CaseCommentCreate
import com.agrimind.app.data.model.CaseOutcome
import com.agrimind.app.data.model.CaseOutcomeCreate
import com.agrimind.app.data.model.LocalCaseRecord
import com.agrimind.app.data.model.ReassessmentRequest
import com.agrimind.app.data.model.ReassessmentResponse
import com.agrimind.app.data.repository.LocalCaseRepository
import com.agrimind.app.report.PdfReportGenerator
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException

sealed interface ReassessmentState {
    object Idle : ReassessmentState
    object Submitting : ReassessmentState
    data class Success(val response: ReassessmentResponse) : ReassessmentState
    data class Error(val message: String) : ReassessmentState
}

sealed interface PdfExportState {
    object Idle : PdfExportState
    object Generating : PdfExportState
    data class Ready(val file: File, val fileName: String) : PdfExportState
    data class Error(val message: String) : PdfExportState
}

sealed interface CaseShareState {
    object Idle : CaseShareState
    object Sharing : CaseShareState
    data class Success(val response: CaseShareResponse) : CaseShareState
    data class Error(val message: String) : CaseShareState
}

class CaseDetailViewModel(application: Application) : AndroidViewModel(application) {

    private val repository by lazy { LocalCaseRepository.getInstance(application) }
    private val pdfGenerator by lazy { PdfReportGenerator(application) }

    private val _activeCase = MutableStateFlow<LocalCaseRecord?>(null)
    val activeCase: StateFlow<LocalCaseRecord?> = _activeCase.asStateFlow()

    private val _reassessmentState = MutableStateFlow<ReassessmentState>(ReassessmentState.Idle)
    val reassessmentState: StateFlow<ReassessmentState> = _reassessmentState.asStateFlow()

    private val _pdfExportState = MutableStateFlow<PdfExportState>(PdfExportState.Idle)
    val pdfExportState: StateFlow<PdfExportState> = _pdfExportState.asStateFlow()

    private val _caseShareState = MutableStateFlow<CaseShareState>(CaseShareState.Idle)
    val caseShareState: StateFlow<CaseShareState> = _caseShareState.asStateFlow()

    // Community observations & farmer comments
    private val _comments = MutableStateFlow<List<CaseComment>>(emptyList())
    val comments: StateFlow<List<CaseComment>> = _comments.asStateFlow()

    private val _isSubmittingComment = MutableStateFlow(false)
    val isSubmittingComment: StateFlow<Boolean> = _isSubmittingComment.asStateFlow()

    // Treatment outcome tracking
    private val _treatmentOutcome = MutableStateFlow<CaseOutcome?>(null)
    val treatmentOutcome: StateFlow<CaseOutcome?> = _treatmentOutcome.asStateFlow()

    private val _isSubmittingOutcome = MutableStateFlow(false)
    val isSubmittingOutcome: StateFlow<Boolean> = _isSubmittingOutcome.asStateFlow()

    fun resetCaseShareState() {
        _caseShareState.value = CaseShareState.Idle
    }

    fun loadComments(caseId: String) {
        viewModelScope.launch {
            try {
                val resp = withContext(Dispatchers.IO) {
                    RetrofitClient.apiService.getCaseComments(caseId)
                }
                if (resp.isSuccessful && resp.body() != null) {
                    _comments.value = resp.body()!!
                }
            } catch (e: Exception) {
                // Non-fatal offline/network error
            }
        }
    }

    fun addComment(caseId: String, commentText: String, authorRole: String = "farmer") {
        if (commentText.isBlank() || _isSubmittingComment.value) return
        _isSubmittingComment.value = true
        viewModelScope.launch {
            try {
                val req = CaseCommentCreate(
                    authorId = "farmer_local",
                    commentText = commentText.trim(),
                    authorRole = authorRole,
                    isAi = false
                )
                val resp = withContext(Dispatchers.IO) {
                    RetrofitClient.apiService.addCaseComment(caseId, req)
                }
                if (resp.isSuccessful && resp.body() != null) {
                    _comments.value = _comments.value + resp.body()!!
                }
            } catch (e: Exception) {
                // Non-fatal
            } finally {
                _isSubmittingComment.value = false
            }
        }
    }

    fun loadOutcome(caseId: String) {
        viewModelScope.launch {
            try {
                val resp = withContext(Dispatchers.IO) {
                    RetrofitClient.apiService.getCaseOutcome(caseId)
                }
                if (resp.isSuccessful) {
                    _treatmentOutcome.value = resp.body()
                }
            } catch (e: Exception) {
                // Non-fatal
            }
        }
    }

    fun recordOutcome(caseId: String, outcome: String, details: String?) {
        if (_isSubmittingOutcome.value) return
        _isSubmittingOutcome.value = true
        viewModelScope.launch {
            try {
                val req = CaseOutcomeCreate(
                    farmerId = "farmer_local",
                    outcome = outcome,
                    details = details?.trim()
                )
                val resp = withContext(Dispatchers.IO) {
                    RetrofitClient.apiService.recordCaseOutcome(caseId, req)
                }
                if (resp.isSuccessful && resp.body() != null) {
                    _treatmentOutcome.value = resp.body()
                }
            } catch (e: Exception) {
                // Non-fatal
            } finally {
                _isSubmittingOutcome.value = false
            }
        }
    }

    fun shareCase(targetEntity: String = "cooperative_all", anonymizePii: Boolean = true, notes: String? = null) {
        val current = _activeCase.value ?: return
        if (_caseShareState.value is CaseShareState.Sharing) return
        _caseShareState.value = CaseShareState.Sharing

        viewModelScope.launch {
            try {
                val req = CaseShareRequest(
                    caseId = current.caseId,
                    ownerFarmerId = "farmer_local",
                    targetEntity = targetEntity,
                    anonymizePii = anonymizePii,
                    notes = notes
                )
                val resp = withContext(Dispatchers.IO) {
                    RetrofitClient.apiService.shareCase(req)
                }
                if (resp.isSuccessful && resp.body() != null) {
                    _caseShareState.value = CaseShareState.Success(resp.body()!!)
                } else {
                    val code = resp.code()
                    val error = resp.errorBody()?.string() ?: "Sharing failed"
                    _caseShareState.value = CaseShareState.Error("Share failed (HTTP $code): $error")
                }
            } catch (e: Exception) {
                _caseShareState.value = CaseShareState.Error(e.localizedMessage ?: "Failed to share case")
            }
        }
    }

    fun loadCase(caseId: String) {
        val record = repository.getCaseById(caseId)
        if (record != null) {
            _activeCase.value = record
        } else {
            // Authoritative server-side retrieval fallback if not in local cache (Stage C.2)
            viewModelScope.launch {
                try {
                    val resp = withContext(Dispatchers.IO) {
                        RetrofitClient.apiService.getCase(caseId)
                    }
                    if (resp.isSuccessful && resp.body() != null) {
                        val body = resp.body()!!
                        val timestamp = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", java.util.Locale.US).format(java.util.Date())
                        val remoteRecord = LocalCaseRecord(
                            caseId = body.caseId,
                            createdAtIso = timestamp,
                            primaryDiagnosis = body.primaryDiagnosis ?: "Unknown",
                            diagnosisConfidence = body.diagnosisConfidence ?: 0f,
                            assignedSeverity = body.assignedSeverity ?: "indeterminate",
                            epidemicRisk = body.epidemicRisk ?: "UNKNOWN",
                            planUrgency = body.planUrgency,
                            isVerified = body.isVerified,
                            imageUriString = null,
                            imageFileName = null,
                            initialDiagnosis = body
                        )
                        repository.saveCase(remoteRecord)
                        _activeCase.value = remoteRecord
                    }
                } catch (e: Exception) {
                    // Non-fatal remote lookup error
                }
            }
        }
        _reassessmentState.value = ReassessmentState.Idle
        _pdfExportState.value = PdfExportState.Idle
        loadComments(caseId)
        loadOutcome(caseId)
    }

    fun setCase(record: LocalCaseRecord) {
        _activeCase.value = record
        _reassessmentState.value = ReassessmentState.Idle
        _pdfExportState.value = PdfExportState.Idle
        loadComments(record.caseId)
        loadOutcome(record.caseId)
    }

    fun resetReassessmentState() {
        _reassessmentState.value = ReassessmentState.Idle
    }

    fun resetPdfExportState() {
        _pdfExportState.value = PdfExportState.Idle
    }

    /**
     * Generates a native Android PDF crop-health report for the active case record.
     */
    fun generatePdfReport() {
        val currentCase = _activeCase.value ?: return

        if (_pdfExportState.value is PdfExportState.Generating) return

        _pdfExportState.value = PdfExportState.Generating

        viewModelScope.launch {
            try {
                val file = withContext(Dispatchers.IO) {
                    pdfGenerator.generateReport(currentCase)
                }
                _pdfExportState.value = PdfExportState.Ready(file, file.name)
            } catch (e: Exception) {
                _pdfExportState.value = PdfExportState.Error(
                    e.localizedMessage ?: "Failed to generate PDF crop-health report"
                )
            }
        }
    }

    /**
     * Submits an adaptive reassessment request to the FastAPI backend (POST /reassess).
     */
    fun submitReassessment(
        trigger: String,
        newEvidence: Map<String, Any>,
        rationale: String?
    ) {
        val currentCase = _activeCase.value ?: return

        // Prevent duplicate submissions
        if (_reassessmentState.value is ReassessmentState.Submitting) return

        // Check if ceiling already reached on client side
        if (currentCase.reassessmentCount >= 2) {
            _reassessmentState.value = ReassessmentState.Error(
                "Maximum reassessment limit (2) reached for case '${currentCase.caseId}'. Formal clinical escalation required."
            )
            return
        }

        _reassessmentState.value = ReassessmentState.Submitting

        viewModelScope.launch {
            try {
                val request = ReassessmentRequest(
                    caseId = currentCase.caseId,
                    trigger = trigger,
                    newEvidence = newEvidence,
                    rationale = rationale
                )

                val response = withContext(Dispatchers.IO) {
                    RetrofitClient.apiService.reassess(request)
                }

                if (response.isSuccessful && response.body() != null) {
                    val result = response.body()!!
                    // Update persistent storage
                    val updatedCase = repository.updateWithReassessment(currentCase.caseId, result)
                    if (updatedCase != null) {
                        _activeCase.value = updatedCase
                    }
                    _reassessmentState.value = ReassessmentState.Success(result)
                } else {
                    val code = response.code()
                    val errorDetail = response.errorBody()?.string() ?: "Reassessment failed"
                    _reassessmentState.value = ReassessmentState.Error(
                        "Reassessment failed (HTTP $code): $errorDetail"
                    )
                }
            } catch (e: SocketTimeoutException) {
                _reassessmentState.value = ReassessmentState.Error(
                    "Reassessment timed out. Backend decision workflow did not respond in time."
                )
            } catch (e: ConnectException) {
                _reassessmentState.value = ReassessmentState.Error(
                    "Connection refused at ${RetrofitClient.getBaseUrl()}. Ensure FastAPI server is running."
                )
            } catch (e: IOException) {
                _reassessmentState.value = ReassessmentState.Error(
                    "Network error during reassessment: ${e.localizedMessage ?: "Communication error"}"
                )
            } catch (e: Exception) {
                _reassessmentState.value = ReassessmentState.Error(
                    "Unexpected error: ${e.localizedMessage ?: e.javaClass.simpleName}"
                )
            }
        }
    }
}

