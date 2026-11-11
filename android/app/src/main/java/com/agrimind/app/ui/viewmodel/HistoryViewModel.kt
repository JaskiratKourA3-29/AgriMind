package com.agrimind.app.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.agrimind.app.data.api.RetrofitClient
import com.agrimind.app.data.model.CooperativeInsightsData
import com.agrimind.app.data.model.CooperativeComparisonResponse
import com.agrimind.app.data.model.LocalCaseRecord
import com.agrimind.app.data.model.SharedCaseSummary
import com.agrimind.app.data.repository.LocalCaseRepository
import com.agrimind.app.report.PdfReportGenerator
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

class HistoryViewModel(application: Application) : AndroidViewModel(application) {

    private val repository = LocalCaseRepository.getInstance(application)
    private val pdfGenerator by lazy { PdfReportGenerator(application) }

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    val casesFlow: StateFlow<List<LocalCaseRecord>> = repository.casesFlow

    private val _cooperativeInsights = MutableStateFlow<CooperativeInsightsData?>(null)
    val cooperativeInsights: StateFlow<CooperativeInsightsData?> = _cooperativeInsights.asStateFlow()

    private val _sharedCases = MutableStateFlow<List<SharedCaseSummary>>(emptyList())
    val sharedCases: StateFlow<List<SharedCaseSummary>> = _sharedCases.asStateFlow()

    private val _cooperativeComparison = MutableStateFlow<CooperativeComparisonResponse?>(null)
    val cooperativeComparison: StateFlow<CooperativeComparisonResponse?> = _cooperativeComparison.asStateFlow()

    private val _isLoadingCooperative = MutableStateFlow(false)
    val isLoadingCooperative: StateFlow<Boolean> = _isLoadingCooperative.asStateFlow()

    private val _cooperativePdfState = MutableStateFlow<PdfExportState>(PdfExportState.Idle)
    val cooperativePdfState: StateFlow<PdfExportState> = _cooperativePdfState.asStateFlow()

    init {
        fetchCooperativeData()
    }

    fun onSearchQueryChanged(query: String) {
        _searchQuery.value = query
    }

    fun deleteCase(caseId: String) {
        repository.deleteCase(caseId)
    }

    fun clearAllHistory() {
        repository.clearAll()
    }

    fun resetCooperativePdfState() {
        _cooperativePdfState.value = PdfExportState.Idle
    }

    fun fetchCooperativeData() {
        viewModelScope.launch {
            _isLoadingCooperative.value = true
            try {
                val insightsResp = withContext(Dispatchers.IO) {
                    RetrofitClient.apiService.getCooperativeInsights()
                }
                if (insightsResp.isSuccessful && insightsResp.body() != null) {
                    _cooperativeInsights.value = insightsResp.body()
                }

                val sharedResp = withContext(Dispatchers.IO) {
                    RetrofitClient.apiService.listSharedCases()
                }
                if (sharedResp.isSuccessful && sharedResp.body() != null) {
                    _sharedCases.value = sharedResp.body()!!
                }

                val compResp = withContext(Dispatchers.IO) {
                    RetrofitClient.apiService.getCooperativeComparison()
                }
                if (compResp.isSuccessful && compResp.body() != null) {
                    _cooperativeComparison.value = compResp.body()
                }
            } catch (e: Exception) {
                // Cooperative service unreachable or offline
            } finally {
                _isLoadingCooperative.value = false
            }
        }
    }

    fun exportCooperativePdf() {
        val insights = _cooperativeInsights.value ?: return
        val cases = _sharedCases.value
        if (_cooperativePdfState.value is PdfExportState.Generating) return

        _cooperativePdfState.value = PdfExportState.Generating
        viewModelScope.launch {
            try {
                val file = withContext(Dispatchers.IO) {
                    pdfGenerator.generateAggregatedHealthReport(insights, cases)
                }
                _cooperativePdfState.value = PdfExportState.Ready(file, file.name)
            } catch (e: Exception) {
                _cooperativePdfState.value = PdfExportState.Error(e.localizedMessage ?: "Failed to generate cooperative audit report")
            }
        }
    }
}
