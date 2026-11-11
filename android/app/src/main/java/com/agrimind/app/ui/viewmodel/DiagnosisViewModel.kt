package com.agrimind.app.ui.viewmodel

import android.app.Application
import android.content.ContentResolver
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.provider.OpenableColumns
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.agrimind.app.data.api.RetrofitClient
import com.agrimind.app.data.local.OfflineQueueManager
import com.agrimind.app.data.model.LiveWeatherData
import com.agrimind.app.data.model.LocalCaseRecord
import com.agrimind.app.data.repository.LocalCaseRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * ViewModel managing the image selection, validation, and multi-agent diagnosis pipeline.
 * Keeps all IO and network operations off the main Android UI thread.
 * Automatically records completed investigations to the local case repository.
 */
class DiagnosisViewModel(application: Application) : AndroidViewModel(application) {

    private val localCaseRepository by lazy {
        try {
            if (application.applicationContext != null) {
                LocalCaseRepository.getInstance(application)
            } else null
        } catch (e: Exception) {
            null
        }
    }

    private val offlineQueueManager by lazy {
        try {
            if (application.applicationContext != null) {
                OfflineQueueManager.getInstance(application)
            } else null
        } catch (e: Exception) {
            null
        }
    }

    private val _uiState = MutableStateFlow<DiagnosisUiState>(DiagnosisUiState.Idle)
    val uiState: StateFlow<DiagnosisUiState> = _uiState.asStateFlow()

    private val _liveWeather = MutableStateFlow<LiveWeatherData?>(null)
    val liveWeather: StateFlow<LiveWeatherData?> = _liveWeather.asStateFlow()

    private val _isLoadingWeather = MutableStateFlow(false)
    val isLoadingWeather: StateFlow<Boolean> = _isLoadingWeather.asStateFlow()

    private val _offlinePendingCount = MutableStateFlow(0)
    val offlinePendingCount: StateFlow<Int> = _offlinePendingCount.asStateFlow()

    private var isSubmittingDiagnosis = false

    // Cached raw image bytes ready for multipart submission
    private var selectedImageBytes: ByteArray? = null
    private var selectedImageMimeType: String = "image/jpeg"
    private var selectedFileName: String = "tomato_leaf.jpg"
    private var cachedBitmap: Bitmap? = null
    private var cachedUri: Uri? = null

    init {
        refreshOfflineCount()
        fetchLiveWeather()
    }

    fun refreshOfflineCount() {
        viewModelScope.launch {
            try {
                _offlinePendingCount.value = offlineQueueManager?.getPendingCount() ?: 0
            } catch (e: Exception) {
                // Ignore failure
            }
        }
    }

    fun fetchLiveWeather(latitude: Double = 32.7266, longitude: Double = 74.8570) {
        viewModelScope.launch {
            _isLoadingWeather.value = true
            try {
                val resp = withContext(Dispatchers.IO) {
                    RetrofitClient.apiService.getLiveWeather(latitude, longitude)
                }
                if (resp.isSuccessful && resp.body() != null) {
                    _liveWeather.value = resp.body()
                }
            } catch (e: Exception) {
                // Weather server offline or network unavailable
            } finally {
                _isLoadingWeather.value = false
            }
        }
    }

    fun syncOfflineQueue() {
        viewModelScope.launch {
            try {
                offlineQueueManager?.syncPendingActions(RetrofitClient.apiService, localCaseRepository)
                refreshOfflineCount()
            } catch (e: Exception) {
                // Ignore failure
            }
        }
    }

    companion object {
        const val MAX_FILE_SIZE_BYTES = 15L * 1024 * 1024 // 15 MB backend contract
    }

    /**
     * Validates and loads an image selected from the Android Photo Picker.
     */
    fun onImageSelected(uri: Uri, contentResolver: ContentResolver) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                // 1. Resolve file name and size metadata
                var fileName = "tomato_leaf.jpg"
                var fileSize = 0L

                contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                    val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    val sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE)
                    if (cursor.moveToFirst()) {
                        if (nameIndex != -1) fileName = cursor.getString(nameIndex) ?: fileName
                        if (sizeIndex != -1) fileSize = cursor.getLong(sizeIndex)
                    }
                }

                // 2. Read bytes into memory
                val inputStream = contentResolver.openInputStream(uri)
                    ?: throw IOException("Unable to open input stream for selected image.")

                val bytes = inputStream.use { it.readBytes() }
                if (fileSize == 0L) fileSize = bytes.size.toLong()

                // 3. Client-side size validation (matching backend MAX_FILE_SIZE_BYTES = 15MB)
                if (bytes.size > MAX_FILE_SIZE_BYTES) {
                    _uiState.value = DiagnosisUiState.Error(
                        errorMessage = "Selected image exceeds maximum allowed limit of 15 MB (${bytes.size / (1024 * 1024)} MB detected).",
                        bitmap = null,
                        canRetry = false
                    )
                    return@launch
                }

                if (bytes.isEmpty()) {
                    _uiState.value = DiagnosisUiState.Error(
                        errorMessage = "Selected image file is empty (0 bytes).",
                        bitmap = null,
                        canRetry = false
                    )
                    return@launch
                }

                // 4. Magic bytes validation (JPEG, PNG, GIF, BMP)
                val mimeType = detectMimeType(bytes)
                if (mimeType == null) {
                    _uiState.value = DiagnosisUiState.Error(
                        errorMessage = "Unsupported file format. The AgriMind backend only accepts JPEG, PNG, GIF, or BMP images.",
                        bitmap = null,
                        canRetry = false
                    )
                    return@launch
                }

                // 5. Decode downsampled thumbnail for memory-safe Compose preview
                val previewBitmap = decodeSampledBitmap(bytes, maxWidth = 1024, maxHeight = 1024)
                if (previewBitmap == null) {
                    _uiState.value = DiagnosisUiState.Error(
                        errorMessage = "Selected image file is corrupted or could not be decoded. Please choose a valid tomato leaf image.",
                        bitmap = null,
                        canRetry = false
                    )
                    return@launch
                }

                // Cache validated data
                selectedImageBytes = bytes
                selectedImageMimeType = mimeType
                selectedFileName = fileName
                cachedBitmap = previewBitmap
                cachedUri = uri

                _uiState.value = DiagnosisUiState.ImageSelected(
                    uri = uri,
                    bitmap = previewBitmap,
                    fileName = fileName,
                    fileSizeBytes = bytes.size.toLong()
                )

            } catch (e: Exception) {
                _uiState.value = DiagnosisUiState.Error(
                    errorMessage = "Error loading image: ${e.localizedMessage ?: "Unknown file access error"}",
                    bitmap = null,
                    canRetry = false
                )
            }
        }
    }

    /**
     * Validates and loads a direct photo captured from the camera.
     */
    fun onBitmapCaptured(bitmap: Bitmap) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val app = getApplication<Application>()
                val captureDir = File(app.cacheDir, "camera_captures").apply { mkdirs() }
                val file = File(captureDir, "camera_${System.currentTimeMillis()}.jpg")
                val outputStream = FileOutputStream(file)
                bitmap.compress(Bitmap.CompressFormat.JPEG, 92, outputStream)
                outputStream.flush()
                outputStream.close()

                val bytes = file.readBytes()
                val uri = Uri.fromFile(file)
                val fileName = file.name

                if (bytes.size > MAX_FILE_SIZE_BYTES) {
                    _uiState.value = DiagnosisUiState.Error(
                        errorMessage = "Captured photo exceeds maximum allowed limit of 15 MB.",
                        bitmap = null,
                        canRetry = false
                    )
                    return@launch
                }

                selectedImageBytes = bytes
                selectedImageMimeType = "image/jpeg"
                selectedFileName = fileName
                cachedBitmap = bitmap
                cachedUri = uri

                _uiState.value = DiagnosisUiState.ImageSelected(
                    uri = uri,
                    bitmap = bitmap,
                    fileName = fileName,
                    fileSizeBytes = bytes.size.toLong()
                )
            } catch (e: Exception) {
                _uiState.value = DiagnosisUiState.Error(
                    errorMessage = "Error processing camera capture: ${e.localizedMessage ?: "Unknown error"}",
                    bitmap = null,
                    canRetry = false
                )
            }
        }
    }

    /**
     * Clears current image selection and resets to Idle state.
     */
    fun onRemoveImage() {
        selectedImageBytes = null
        cachedBitmap = null
        cachedUri = null
        _uiState.value = DiagnosisUiState.Idle
    }

    /**
     * Submits the selected leaf image to the FastAPI /diagnose endpoint.
     */
    fun runDiagnosis() {
        if (isSubmittingDiagnosis || _uiState.value is DiagnosisUiState.Diagnosing) {
            return
        }

        val bytes = selectedImageBytes
        val bitmap = cachedBitmap
        val uri = cachedUri

        if (bytes == null || bitmap == null || uri == null) {
            _uiState.value = DiagnosisUiState.Error(
                errorMessage = "No valid image selected. Please choose a tomato leaf photo first.",
                bitmap = null,
                canRetry = false
            )
            return
        }

        isSubmittingDiagnosis = true
        _uiState.value = DiagnosisUiState.Diagnosing(uri = uri, bitmap = bitmap)

        viewModelScope.launch {
            try {
                val mediaType = selectedImageMimeType.toMediaTypeOrNull()
                val requestBody = bytes.toRequestBody(mediaType)
                val filePart = MultipartBody.Part.createFormData("file", selectedFileName, requestBody)

                val latBody = "32.7266".toRequestBody("text/plain".toMediaTypeOrNull())
                val lonBody = "74.8570".toRequestBody("text/plain".toMediaTypeOrNull())
                val useWeatherBody = "true".toRequestBody("text/plain".toMediaTypeOrNull())

                val response = withContext(Dispatchers.IO) {
                    RetrofitClient.apiService.diagnose(
                        file = filePart,
                        latitude = latBody,
                        longitude = lonBody,
                        useLiveWeather = useWeatherBody
                    )
                }

                if (response.isSuccessful && response.body() != null) {
                    val body = response.body()!!

                    // Guard against failed/aborted workflow diagnoses returning HTTP 200
                    if (body.workflowStatus == "error" || body.primaryDiagnosis.isNullOrBlank()) {
                        val errorMsg = body.errorMessage ?: "Diagnostic pipeline failed to classify the tomato leaf specimen."
                        _uiState.value = DiagnosisUiState.Error(
                            errorMessage = errorMsg,
                            bitmap = bitmap,
                            canRetry = true
                        )
                        return@launch
                    }

                    // Automatically record new diagnostic case into local repository
                    try {
                        val timestamp = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).format(Date())
                        val record = LocalCaseRecord(
                            caseId = body.caseId,
                            createdAtIso = timestamp,
                            primaryDiagnosis = body.primaryDiagnosis,
                            diagnosisConfidence = body.diagnosisConfidence ?: 0f,
                            assignedSeverity = body.assignedSeverity ?: "indeterminate",
                            epidemicRisk = body.epidemicRisk ?: "UNKNOWN",
                            planUrgency = body.planUrgency,
                            isVerified = body.isVerified,
                            imageUriString = uri.toString(),
                            imageFileName = selectedFileName,
                            initialDiagnosis = body
                        )
                        localCaseRepository?.saveCase(record)
                    } catch (e: Exception) {
                        // Non-fatal persistence logging
                    }

                    _uiState.value = DiagnosisUiState.Success(
                        response = body,
                        bitmap = bitmap
                    )
                } else {
                    val code = response.code()
                    val rawError = response.errorBody()?.string() ?: ""
                    val errorDetail = parseErrorMessage(rawError)
                    _uiState.value = DiagnosisUiState.Error(
                        errorMessage = if (errorDetail.isNotBlank()) errorDetail else "Diagnostic service error (HTTP $code)",
                        bitmap = bitmap,
                        canRetry = true
                    )
                }

            } catch (e: Exception) {
                if (e is SocketTimeoutException || e is ConnectException || e is IOException) {
                    try {
                        offlineQueueManager?.enqueueDiagnosis(
                            imageBytes = bytes,
                            fileName = selectedFileName,
                            damagePercentage = null,
                            canopySpread = null,
                            affectedOrgans = null,
                            weatherConditions = _liveWeather.value?.conditionSummary,
                            fieldNotes = null
                        )
                        refreshOfflineCount()
                        _uiState.value = DiagnosisUiState.QueuedOffline(
                            uri = uri,
                            bitmap = bitmap,
                            message = "Offline Mode: Vision diagnosis requires edge server connectivity. Specimen image securely saved to offline queue and will sync automatically when connected."
                        )
                    } catch (queueEx: Exception) {
                        _uiState.value = DiagnosisUiState.Error(
                            errorMessage = "Offline queueing failed: ${queueEx.localizedMessage}",
                            bitmap = bitmap,
                            canRetry = true
                        )
                    }
                } else {
                    _uiState.value = DiagnosisUiState.Error(
                        errorMessage = "Unexpected diagnosis error: ${e.localizedMessage ?: e.javaClass.simpleName}",
                        bitmap = bitmap,
                        canRetry = true
                    )
                }
            } finally {
                isSubmittingDiagnosis = false
            }
        }
    }

    internal fun parseErrorMessage(rawJson: String): String {
        if (rawJson.isBlank()) return ""
        return try {
            val match = Regex("\"detail\"\\s*:\\s*\"([^\"]+)\"").find(rawJson)
            match?.groups?.get(1)?.value ?: rawJson
        } catch (e: Exception) {
            rawJson
        }
    }

    /**
     * Inspects magic header bytes (JPEG, PNG, GIF, BMP) matching backend validation.
     */
    internal fun detectMimeType(bytes: ByteArray): String? {
        if (bytes.size < 4) return null
        return when {
            bytes[0] == 0xFF.toByte() && bytes[1] == 0xD8.toByte() -> "image/jpeg"
            bytes[0] == 0x89.toByte() && bytes[1] == 0x50.toByte() && bytes[2] == 0x4E.toByte() && bytes[3] == 0x47.toByte() -> "image/png"
            bytes[0] == 0x47.toByte() && bytes[1] == 0x49.toByte() && bytes[2] == 0x46.toByte() -> "image/gif"
            bytes[0] == 0x42.toByte() && bytes[1] == 0x4D.toByte() -> "image/bmp"
            else -> null
        }
    }

    /**
     * Memory-safe bitmap decoding using inSampleSize downsampling.
     */
    private fun decodeSampledBitmap(bytes: ByteArray, maxWidth: Int, maxHeight: Int): Bitmap? {
        val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, options)

        var inSampleSize = 1
        if (options.outHeight > maxHeight || options.outWidth > maxWidth) {
            val halfHeight = options.outHeight / 2
            val halfWidth = options.outWidth / 2
            while ((halfHeight / inSampleSize) >= maxHeight && (halfWidth / inSampleSize) >= maxWidth) {
                inSampleSize *= 2
            }
        }

        val decodeOptions = BitmapFactory.Options().apply {
            this.inSampleSize = inSampleSize
            inPreferredConfig = Bitmap.Config.RGB_565 // Conserves memory
        }
        return BitmapFactory.decodeByteArray(bytes, 0, bytes.size, decodeOptions)
    }
}

