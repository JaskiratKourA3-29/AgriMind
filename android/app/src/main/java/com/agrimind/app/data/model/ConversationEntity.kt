package com.agrimind.app.data.model

import java.util.UUID

/**
 * Entity representing a persistent conversation thread in AgriMind.
 * Stores metadata including readable title, timestamps, language, and optional case context.
 */
data class ConversationEntity(
    val id: String = UUID.randomUUID().toString(),
    val title: String,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis(),
    val language: String = "en",
    val caseId: String? = null,
    val messageCount: Int = 0
)
