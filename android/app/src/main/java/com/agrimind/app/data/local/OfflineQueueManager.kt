package com.agrimind.app.data.local

import android.content.ContentValues
import android.content.Context
import android.util.Log
import com.agrimind.app.data.api.AgriMindApiService
import com.agrimind.app.data.model.LocalCaseRecord
import com.agrimind.app.data.model.QueuedAction
import com.agrimind.app.data.repository.LocalCaseRepository
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Manages queued offline actions (such as diagnosis submissions when disconnected),
 * local file persistence, and automatic reconciliation upon connectivity restoration.
 */
class OfflineQueueManager private constructor(private val context: Context) {

    private val dbHelper = ChatDatabaseHelper(context)
    private val gson = Gson()

    companion object {
        private const val TAG = "OfflineQueueManager"
        @Volatile
        private var instance: OfflineQueueManager? = null

        fun getInstance(context: Context): OfflineQueueManager {
            return instance ?: synchronized(this) {
                instance ?: OfflineQueueManager(context.applicationContext).also { instance = it }
            }
        }
    }

    /**
     * Enqueues a diagnosis request to be submitted once connection is restored.
     * Caches image bytes safely to local private app storage.
     */
    suspend fun enqueueDiagnosis(
        imageBytes: ByteArray,
        fileName: String,
        damagePercentage: Float?,
        canopySpread: String?,
        affectedOrgans: String?,
        weatherConditions: String?,
        fieldNotes: String?
    ): Long = withContext(Dispatchers.IO) {
        val queueDir = File(context.filesDir, "offline_queue").apply { mkdirs() }
        val imageFile = File(queueDir, "queue_${System.currentTimeMillis()}_$fileName")
        FileOutputStream(imageFile).use { it.write(imageBytes) }

        val payload = mapOf(
            "fileName" to fileName,
            "damagePercentage" to damagePercentage,
            "canopySpread" to canopySpread,
            "affectedOrgans" to affectedOrgans,
            "weatherConditions" to weatherConditions,
            "fieldNotes" to fieldNotes
        )
        val payloadJson = gson.toJson(payload)
        val nowIso = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(Date())

        val db = dbHelper.writableDatabase
        val values = ContentValues().apply {
            put("action_type", "DIAGNOSE")
            put("payload_json", payloadJson)
            put("local_image_path", imageFile.absolutePath)
            put("status", "PENDING")
            put("created_at", nowIso)
        }
        val rowId = db.insert("offline_action_queue", null, values)
        Log.i(TAG, "Enqueued offline diagnosis action #$rowId with image ${imageFile.name}")
        rowId
    }

    /**
     * Returns count of actions currently pending synchronization.
     */
    suspend fun getPendingCount(): Int = withContext(Dispatchers.IO) {
        val db = dbHelper.readableDatabase
        val cursor = db.rawQuery("SELECT COUNT(*) FROM offline_action_queue WHERE status = 'PENDING'", null)
        var count = 0
        cursor.use {
            if (it.moveToFirst()) {
                count = it.getInt(0)
            }
        }
        count
    }

    /**
     * Retrieves all pending actions.
     */
    suspend fun getPendingActions(): List<QueuedAction> = withContext(Dispatchers.IO) {
        val list = mutableListOf<QueuedAction>()
        val db = dbHelper.readableDatabase
        val cursor = db.rawQuery(
            "SELECT id, action_type, payload_json, local_image_path, status, created_at FROM offline_action_queue WHERE status = 'PENDING' ORDER BY id ASC",
            null
        )
        cursor.use {
            while (it.moveToNext()) {
                list.add(
                    QueuedAction(
                        id = it.getLong(0),
                        actionType = it.getString(1),
                        payloadJson = it.getString(2),
                        localImageUri = it.getString(3),
                        status = it.getString(4),
                        createdAt = it.getString(5)
                    )
                )
            }
        }
        list
    }

    /**
     * Synchronizes all pending actions with the backend when connection is restored.
     */
    suspend fun syncPendingActions(
        apiService: AgriMindApiService,
        localCaseRepo: LocalCaseRepository?
    ): Int = withContext(Dispatchers.IO) {
        val pending = getPendingActions()
        var syncedCount = 0

        for (action in pending) {
            try {
                if (action.actionType == "DIAGNOSE" && action.localImageUri != null) {
                    val file = File(action.localImageUri)
                    if (!file.exists()) {
                        markActionFailed(action.id)
                        continue
                    }

                    val mimeType = if (file.name.endsWith(".png", true)) "image/png" else "image/jpeg"
                    val requestFile = file.asRequestBody(mimeType.toMediaTypeOrNull())
                    val filePart = MultipartBody.Part.createFormData("file", file.name, requestFile)

                    val payloadMap = try {
                        gson.fromJson(action.payloadJson, Map::class.java)
                    } catch (e: Exception) {
                        emptyMap<String, Any?>()
                    }

                    val damage = (payloadMap["damagePercentage"] as? Double)?.toFloat()
                    val canopy = payloadMap["canopySpread"] as? String
                    val organs = payloadMap["affectedOrgans"] as? String
                    val weather = payloadMap["weatherConditions"] as? String
                    val notes = payloadMap["fieldNotes"] as? String

                    val response = apiService.diagnose(
                        file = filePart,
                        leafDamagePercentage = damage?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull()),
                        canopySpread = canopy?.toRequestBody("text/plain".toMediaTypeOrNull()),
                        affectedOrgans = organs?.toRequestBody("text/plain".toMediaTypeOrNull()),
                        weatherConditions = weather?.toRequestBody("text/plain".toMediaTypeOrNull()),
                        fieldNotes = notes?.toRequestBody("text/plain".toMediaTypeOrNull())
                    )

                    if (response.isSuccessful && response.body() != null) {
                        val body = response.body()!!
                        val nowIso = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).format(Date())
                        val record = LocalCaseRecord(
                            caseId = body.caseId,
                            createdAtIso = nowIso,
                            primaryDiagnosis = body.primaryDiagnosis ?: "Unknown",
                            diagnosisConfidence = body.diagnosisConfidence ?: 0f,
                            assignedSeverity = body.assignedSeverity ?: "indeterminate",
                            epidemicRisk = body.epidemicRisk ?: "UNKNOWN",
                            planUrgency = body.planUrgency,
                            isVerified = body.isVerified,
                            imageUriString = action.localImageUri,
                            imageFileName = file.name,
                            initialDiagnosis = body
                        )
                        localCaseRepo?.saveCase(record)
                        markActionSynced(action.id)
                        syncedCount++
                        Log.i(TAG, "Successfully synced action #${action.id} -> Case ID ${body.caseId}")
                    } else {
                        Log.w(TAG, "Sync failed for action #${action.id}: HTTP ${response.code()}")
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "Error syncing action #${action.id}: ${e.message}")
            }
        }
        syncedCount
    }

    private fun markActionSynced(id: Long) {
        val db = dbHelper.writableDatabase
        db.delete("offline_action_queue", "id = ?", arrayOf(id.toString()))
    }

    private fun markActionFailed(id: Long) {
        val db = dbHelper.writableDatabase
        val cv = ContentValues().apply { put("status", "FAILED") }
        db.update("offline_action_queue", cv, "id = ?", arrayOf(id.toString()))
    }
}

