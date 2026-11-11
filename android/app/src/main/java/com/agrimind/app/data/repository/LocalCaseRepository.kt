package com.agrimind.app.data.repository

import android.content.Context
import android.content.SharedPreferences
import com.agrimind.app.data.model.LocalCaseRecord
import com.agrimind.app.data.model.ReassessmentResponse
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Local device repository persisting diagnostic investigations.
 * Stores cases in encrypted/private SharedPreferences as serialized JSON.
 * Dispatches updates to observing ViewModels via StateFlow.
 */
class LocalCaseRepository private constructor(context: Context) {

    private val prefs: SharedPreferences = context.applicationContext.getSharedPreferences(
        PREFS_NAME,
        Context.MODE_PRIVATE
    )
    private val gson = Gson()
    private val scope = CoroutineScope(Dispatchers.IO)

    private val _casesFlow = MutableStateFlow<List<LocalCaseRecord>>(emptyList())
    val casesFlow: StateFlow<List<LocalCaseRecord>> = _casesFlow.asStateFlow()

    init {
        loadCases()
    }

    private fun loadCases() {
        try {
            val json = prefs.getString(KEY_CASES, null)
            if (!json.isNullOrBlank()) {
                val type = object : TypeToken<List<LocalCaseRecord>>() {}.type
                val list: List<LocalCaseRecord> = gson.fromJson(json, type) ?: emptyList()
                _casesFlow.value = list
            } else {
                _casesFlow.value = emptyList()
            }
        } catch (e: Exception) {
            _casesFlow.value = emptyList()
        }
    }

    private fun persistCases(list: List<LocalCaseRecord>) {
        _casesFlow.value = list
        scope.launch {
            try {
                val json = gson.toJson(list)
                prefs.edit().putString(KEY_CASES, json).apply()
            } catch (e: Exception) {
                // Ignore or log persistence error
            }
        }
    }

    @Synchronized
    fun saveCase(record: LocalCaseRecord) {
        val current = _casesFlow.value.toMutableList()
        // Replace existing if already present, else add at top
        val index = current.indexOfFirst { it.caseId == record.caseId }
        if (index >= 0) {
            current[index] = record
        } else {
            current.add(0, record)
        }
        persistCases(current)
    }

    @Synchronized
    fun updateWithReassessment(caseId: String, reassessment: ReassessmentResponse): LocalCaseRecord? {
        val current = _casesFlow.value.toMutableList()
        val index = current.indexOfFirst { it.caseId == caseId }
        if (index >= 0) {
            val old = current[index]
            val updatedHistory = old.reassessmentHistory + reassessment
            val updated = old.copy(
                latestReassessment = reassessment,
                reassessmentCount = reassessment.reassessmentCount,
                reassessmentHistory = updatedHistory
            )
            current[index] = updated
            persistCases(current)
            return updated
        }
        return null
    }

    fun getAllCases(): List<LocalCaseRecord> {
        return _casesFlow.value
    }

    fun getCaseById(caseId: String): LocalCaseRecord? {
        return _casesFlow.value.find { it.caseId == caseId }
    }

    @Synchronized
    fun deleteCase(caseId: String) {
        val filtered = _casesFlow.value.filter { it.caseId != caseId }
        persistCases(filtered)
    }

    @Synchronized
    fun clearAll() {
        persistCases(emptyList())
    }

    companion object {
        private const val PREFS_NAME = "agrimind_case_history_prefs"
        private const val KEY_CASES = "persisted_cases_json"

        @Volatile
        private var INSTANCE: LocalCaseRepository? = null

        fun getInstance(context: Context): LocalCaseRepository {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: LocalCaseRepository(context).also { INSTANCE = it }
            }
        }
    }
}

