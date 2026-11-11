package com.agrimind.app.data.repository

import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.util.Log
import com.agrimind.app.data.local.ChatDatabaseHelper
import com.agrimind.app.data.model.ChatCitationItem
import com.agrimind.app.data.model.ConversationEntity
import com.agrimind.app.ui.viewmodel.UiChatMessage
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.UUID

/**
 * Common contract for AgriMind conversation and chat message persistence.
 */
interface IChatRepository {
    val conversationsFlow: StateFlow<List<ConversationEntity>>
    suspend fun getAllConversations(): List<ConversationEntity>
    suspend fun createConversation(title: String, language: String = "en", caseId: String? = null): ConversationEntity
    suspend fun saveMessage(conversationId: String, message: UiChatMessage)
    suspend fun getMessagesForConversation(conversationId: String): List<UiChatMessage>
    suspend fun updateConversationTitle(conversationId: String, newTitle: String)
    suspend fun deleteConversation(conversationId: String): Boolean
    suspend fun clearAllConversations()
}

/**
 * Repository providing persistent local SQLite storage for AgriMind conversations and chat messages.
 * Manages full thread persistence, message history, title derivation, and cascade deletion.
 */
class ChatRepository(context: Context) : IChatRepository {

    private val dbHelper = ChatDatabaseHelper(context)
    private val gson = Gson()
    private val scope = CoroutineScope(Dispatchers.IO)

    private val _conversationsFlow = MutableStateFlow<List<ConversationEntity>>(emptyList())
    override val conversationsFlow: StateFlow<List<ConversationEntity>> = _conversationsFlow.asStateFlow()

    companion object {
        private const val TAG = "ChatRepository"

        @Volatile
        private var INSTANCE: ChatRepository? = null

        fun getInstance(context: Context): ChatRepository {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: ChatRepository(context.applicationContext).also { INSTANCE = it }
            }
        }
    }

    init {
        refreshConversations()
    }

    fun refreshConversations() {
        scope.launch {
            val list = queryAllConversations()
            _conversationsFlow.value = list
        }
    }

    /**
     * Retrieves all saved conversations sorted by most recently updated.
     */
    override suspend fun getAllConversations(): List<ConversationEntity> = withContext(Dispatchers.IO) {
        queryAllConversations()
    }

    private fun queryAllConversations(): List<ConversationEntity> {
        val list = mutableListOf<ConversationEntity>()
        val db = dbHelper.readableDatabase
        val query = """
            SELECT c.${ChatDatabaseHelper.COL_CONV_ID},
                   c.${ChatDatabaseHelper.COL_CONV_TITLE},
                   c.${ChatDatabaseHelper.COL_CONV_CREATED_AT},
                   c.${ChatDatabaseHelper.COL_CONV_UPDATED_AT},
                   c.${ChatDatabaseHelper.COL_CONV_LANGUAGE},
                   c.${ChatDatabaseHelper.COL_CONV_CASE_ID},
                   COUNT(m.${ChatDatabaseHelper.COL_MSG_ID}) as msg_count
            FROM ${ChatDatabaseHelper.TABLE_CONVERSATIONS} c
            LEFT JOIN ${ChatDatabaseHelper.TABLE_MESSAGES} m 
              ON c.${ChatDatabaseHelper.COL_CONV_ID} = m.${ChatDatabaseHelper.COL_MSG_CONV_ID}
            GROUP BY c.${ChatDatabaseHelper.COL_CONV_ID}
            ORDER BY c.${ChatDatabaseHelper.COL_CONV_UPDATED_AT} DESC
        """.trimIndent()

        var cursor: Cursor? = null
        try {
            cursor = db.rawQuery(query, null)
            cursor?.let {
                while (it.moveToNext()) {
                    val id = it.getString(0)
                    val title = it.getString(1)
                    val createdAt = it.getLong(2)
                    val updatedAt = it.getLong(3)
                    val language = it.getString(4)
                    val caseId = it.getString(5)
                    val count = it.getInt(6)

                    list.add(
                        ConversationEntity(
                            id = id,
                            title = title,
                            createdAt = createdAt,
                            updatedAt = updatedAt,
                            language = language,
                            caseId = caseId,
                            messageCount = count
                        )
                    )
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error querying conversations from SQLite: ${e.message}")
        } finally {
            cursor?.close()
        }
        return list
    }

    /**
     * Creates a new persistent conversation thread.
     */
    override suspend fun createConversation(
        title: String,
        language: String,
        caseId: String?
    ): ConversationEntity = withContext(Dispatchers.IO) {
        val now = System.currentTimeMillis()
        val conv = ConversationEntity(
            id = UUID.randomUUID().toString(),
            title = title.ifBlank { "New Conversation" },
            createdAt = now,
            updatedAt = now,
            language = language,
            caseId = caseId,
            messageCount = 0
        )

        val db = dbHelper.writableDatabase
        val values = ContentValues().apply {
            put(ChatDatabaseHelper.COL_CONV_ID, conv.id)
            put(ChatDatabaseHelper.COL_CONV_TITLE, conv.title)
            put(ChatDatabaseHelper.COL_CONV_CREATED_AT, conv.createdAt)
            put(ChatDatabaseHelper.COL_CONV_UPDATED_AT, conv.updatedAt)
            put(ChatDatabaseHelper.COL_CONV_LANGUAGE, conv.language)
            put(ChatDatabaseHelper.COL_CONV_CASE_ID, conv.caseId)
        }

        db.insertWithOnConflict(
            ChatDatabaseHelper.TABLE_CONVERSATIONS,
            null,
            values,
            android.database.sqlite.SQLiteDatabase.CONFLICT_REPLACE
        )

        refreshConversations()
        Log.d(TAG, "Conversation created: id=${conv.id}, title='${conv.title}'")
        conv
    }

    /**
     * Saves a chat message to persistent SQLite storage.
     * Updates the parent conversation's last updated timestamp and sets the title if needed.
     */
    override suspend fun saveMessage(
        conversationId: String,
        message: UiChatMessage
    ): Unit = withContext(Dispatchers.IO) {
        val db = dbHelper.writableDatabase
        val citationsJson = if (message.citations.isNotEmpty()) {
            gson.toJson(message.citations)
        } else null

        val values = ContentValues().apply {
            put(ChatDatabaseHelper.COL_MSG_ID, message.id)
            put(ChatDatabaseHelper.COL_MSG_CONV_ID, conversationId)
            put(ChatDatabaseHelper.COL_MSG_ROLE, message.role)
            put(ChatDatabaseHelper.COL_MSG_CONTENT, message.content)
            put(ChatDatabaseHelper.COL_MSG_CITATIONS_JSON, citationsJson)
            put(ChatDatabaseHelper.COL_MSG_HAS_EVIDENCE, if (message.hasSufficientEvidence) 1 else 0)
            put(ChatDatabaseHelper.COL_MSG_GENERATION_MODE, message.generationMode)
            put(ChatDatabaseHelper.COL_MSG_DISEASE_TARGET, message.diseaseTarget)
            put(ChatDatabaseHelper.COL_MSG_LANGUAGE, message.language)
            put(ChatDatabaseHelper.COL_MSG_IS_ERROR, if (message.isError) 1 else 0)
            put(ChatDatabaseHelper.COL_MSG_TIMESTAMP, message.timestamp)
        }

        db.insertWithOnConflict(
            ChatDatabaseHelper.TABLE_MESSAGES,
            null,
            values,
            android.database.sqlite.SQLiteDatabase.CONFLICT_REPLACE
        )

        // Update conversation's updated_at timestamp
        val updateValues = ContentValues().apply {
            put(ChatDatabaseHelper.COL_CONV_UPDATED_AT, message.timestamp)
        }
        db.update(
            ChatDatabaseHelper.TABLE_CONVERSATIONS,
            updateValues,
            "${ChatDatabaseHelper.COL_CONV_ID} = ?",
            arrayOf(conversationId)
        )

        refreshConversations()
        Log.d(TAG, "Message saved: id=${message.id}, conv=$conversationId, role=${message.role}")
    }

    /**
     * Retrieves all messages for a specific conversation in chronological order.
     */
    override suspend fun getMessagesForConversation(conversationId: String): List<UiChatMessage> = withContext(Dispatchers.IO) {
        val list = mutableListOf<UiChatMessage>()
        val db = dbHelper.readableDatabase
        val query = """
            SELECT ${ChatDatabaseHelper.COL_MSG_ID},
                   ${ChatDatabaseHelper.COL_MSG_ROLE},
                   ${ChatDatabaseHelper.COL_MSG_CONTENT},
                   ${ChatDatabaseHelper.COL_MSG_CITATIONS_JSON},
                   ${ChatDatabaseHelper.COL_MSG_HAS_EVIDENCE},
                   ${ChatDatabaseHelper.COL_MSG_GENERATION_MODE},
                   ${ChatDatabaseHelper.COL_MSG_DISEASE_TARGET},
                   ${ChatDatabaseHelper.COL_MSG_LANGUAGE},
                   ${ChatDatabaseHelper.COL_MSG_IS_ERROR},
                   ${ChatDatabaseHelper.COL_MSG_TIMESTAMP}
            FROM ${ChatDatabaseHelper.TABLE_MESSAGES}
            WHERE ${ChatDatabaseHelper.COL_MSG_CONV_ID} = ?
            ORDER BY ${ChatDatabaseHelper.COL_MSG_TIMESTAMP} ASC
        """.trimIndent()

        var cursor: Cursor? = null
        try {
            cursor = db.rawQuery(query, arrayOf(conversationId))
            cursor?.let {
                while (it.moveToNext()) {
                    val id = it.getString(0)
                    val role = it.getString(1)
                    val content = it.getString(2)
                    val citJson = it.getString(3)
                    val hasEv = it.getInt(4) == 1
                    val genMode = it.getString(5) ?: "unknown"
                    val diseaseTarget = it.getString(6)
                    val lang = it.getString(7) ?: "en"
                    val isError = it.getInt(8) == 1
                    val ts = it.getLong(9)

                    val citations: List<ChatCitationItem> = if (!citJson.isNullOrBlank()) {
                        try {
                            val type = object : TypeToken<List<ChatCitationItem>>() {}.type
                            gson.fromJson(citJson, type) ?: emptyList()
                        } catch (e: Exception) {
                            emptyList()
                        }
                    } else emptyList()

                    list.add(
                        UiChatMessage(
                            id = id,
                            role = role,
                            content = content,
                            citations = citations,
                            hasSufficientEvidence = hasEv,
                            generationMode = genMode,
                            diseaseTarget = diseaseTarget,
                            language = lang,
                            isError = isError,
                            timestamp = ts
                        )
                    )
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error querying messages for $conversationId: ${e.message}")
        } finally {
            cursor?.close()
        }
        list
    }

    /**
     * Updates the readable title of a conversation.
     */
    override suspend fun updateConversationTitle(conversationId: String, newTitle: String): Unit = withContext(Dispatchers.IO) {
        val db = dbHelper.writableDatabase
        val values = ContentValues().apply {
            put(ChatDatabaseHelper.COL_CONV_TITLE, newTitle.trim())
            put(ChatDatabaseHelper.COL_CONV_UPDATED_AT, System.currentTimeMillis())
        }
        db.update(
            ChatDatabaseHelper.TABLE_CONVERSATIONS,
            values,
            "${ChatDatabaseHelper.COL_CONV_ID} = ?",
            arrayOf(conversationId)
        )
        refreshConversations()
    }

    /**
     * Deletes a conversation and its messages permanently via SQLite cascade.
     */
    override suspend fun deleteConversation(conversationId: String): Boolean = withContext(Dispatchers.IO) {
        val db = dbHelper.writableDatabase
        val count = db.delete(
            ChatDatabaseHelper.TABLE_CONVERSATIONS,
            "${ChatDatabaseHelper.COL_CONV_ID} = ?",
            arrayOf(conversationId)
        )
        refreshConversations()
        Log.d(TAG, "Deleted conversation $conversationId (affected rows: $count)")
        count > 0
    }

    /**
     * Clears all conversation history.
     */
    override suspend fun clearAllConversations(): Unit = withContext(Dispatchers.IO) {
        val db = dbHelper.writableDatabase
        db.delete(ChatDatabaseHelper.TABLE_CONVERSATIONS, null, null)
        refreshConversations()
    }
}

/**
 * In-memory implementation of IChatRepository for unit testing and offline isolated execution.
 */
class InMemoryChatRepository : IChatRepository {
    private val conversationsMap = mutableMapOf<String, ConversationEntity>()
    private val messagesMap = mutableMapOf<String, MutableList<UiChatMessage>>()

    private val _conversationsFlow = MutableStateFlow<List<ConversationEntity>>(emptyList())
    override val conversationsFlow: StateFlow<List<ConversationEntity>> = _conversationsFlow.asStateFlow()

    private fun updateFlow() {
        _conversationsFlow.value = conversationsMap.values.sortedByDescending { it.updatedAt }
    }

    override suspend fun getAllConversations(): List<ConversationEntity> {
        return conversationsMap.values.sortedByDescending { it.updatedAt }
    }

    override suspend fun createConversation(
        title: String,
        language: String,
        caseId: String?
    ): ConversationEntity {
        val now = System.currentTimeMillis()
        val conv = ConversationEntity(
            id = UUID.randomUUID().toString(),
            title = title.ifBlank { "New Conversation" },
            createdAt = now,
            updatedAt = now,
            language = language,
            caseId = caseId,
            messageCount = 0
        )
        conversationsMap[conv.id] = conv
        messagesMap[conv.id] = mutableListOf()
        updateFlow()
        return conv
    }

    override suspend fun saveMessage(conversationId: String, message: UiChatMessage) {
        val list = messagesMap.getOrPut(conversationId) { mutableListOf() }
        list.add(message)
        val conv = conversationsMap[conversationId]
        if (conv != null) {
            conversationsMap[conversationId] = conv.copy(
                updatedAt = message.timestamp,
                messageCount = list.size
            )
        }
        updateFlow()
    }

    override suspend fun getMessagesForConversation(conversationId: String): List<UiChatMessage> {
        return messagesMap[conversationId]?.sortedBy { it.timestamp } ?: emptyList()
    }

    override suspend fun updateConversationTitle(conversationId: String, newTitle: String) {
        val conv = conversationsMap[conversationId]
        if (conv != null) {
            conversationsMap[conversationId] = conv.copy(
                title = newTitle.trim(),
                updatedAt = System.currentTimeMillis()
            )
            updateFlow()
        }
    }

    override suspend fun deleteConversation(conversationId: String): Boolean {
        val removed = conversationsMap.remove(conversationId) != null
        messagesMap.remove(conversationId)
        updateFlow()
        return removed
    }

    override suspend fun clearAllConversations() {
        conversationsMap.clear()
        messagesMap.clear()
        updateFlow()
    }
}
