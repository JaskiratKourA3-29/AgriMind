package com.agrimind.app.data.model

import com.google.gson.annotations.SerializedName

/**
 * Supported message roles for conversational dialogue.
 */
enum class ChatRole(val value: String) {
    @SerializedName("user")
    USER("user"),

    @SerializedName("assistant")
    ASSISTANT("assistant")
}

/**
 * Citation metadata returned by RAG evidence synthesis.
 */
data class ChatCitationItem(
    @SerializedName("citation_number")
    val citationNumber: Int,

    @SerializedName("doc_id")
    val docId: String,

    @SerializedName("title")
    val title: String,

    @SerializedName("institution")
    val institution: String,

    @SerializedName("source_url")
    val sourceUrl: String,

    @SerializedName("chunk_id")
    val chunkId: String? = null,

    @SerializedName("similarity_score")
    val similarityScore: Float? = null
)

/**
 * Single dialogue message formatted strictly for backend JSON serialization.
 * Excludes client-only properties to comply with backend extra="forbid" schema.
 */
data class ChatMessageItem(
    @SerializedName("role")
    val role: String,

    @SerializedName("content")
    val content: String
)

/**
 * Request payload for conversational question-answering (POST /chat).
 */
data class ChatRequest(
    @SerializedName("query")
    val query: String,

    @SerializedName("case_id")
    val caseId: String? = null,

    @SerializedName("conversation_history")
    val conversationHistory: List<ChatMessageItem> = emptyList(),

    @SerializedName("language")
    val language: String = "en"
)

/**
 * Evidence-grounded conversational response payload from POST /chat.
 */
data class ChatResponse(
    @SerializedName("query")
    val query: String,

    @SerializedName("answer")
    val answer: String,

    @SerializedName("citations")
    val citations: List<ChatCitationItem> = emptyList(),

    @SerializedName("has_sufficient_evidence")
    val hasSufficientEvidence: Boolean = false,

    @SerializedName("generation_mode")
    val generationMode: String = "unknown",

    @SerializedName("case_id")
    val caseId: String? = null,

    @SerializedName("disease_target")
    val diseaseTarget: String? = null,

    @SerializedName("language")
    val language: String = "en",

    @SerializedName("model")
    val model: String? = null,

    @SerializedName("error")
    val error: String? = null
)

