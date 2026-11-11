package com.agrimind.app.data.model

import com.google.gson.annotations.SerializedName

/**
 * Data model matching FastAPI GET /health response schema.
 */
data class HealthResponse(
    @SerializedName("status")
    val status: String,

    @SerializedName("timestamp")
    val timestamp: String,

    @SerializedName("version")
    val version: String,

    @SerializedName("models_available")
    val modelsAvailable: ModelsAvailable,

    @SerializedName("rag_chunks")
    val ragChunks: Int,

    @SerializedName("active_classes")
    val activeClasses: List<String>,

    @SerializedName("device")
    val device: String
)

data class ModelsAvailable(
    @SerializedName("resnet50")
    val resnet50: Boolean,

    @SerializedName("rag_chromadb")
    val ragChromaDb: Boolean
)

