package com.agrimind.app.data.local

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import android.util.Log

/**
 * Native Android SQLiteOpenHelper providing persistent device storage for AgriMind chat conversations.
 * Manages schema creation, migrations, and referential integrity via ON DELETE CASCADE.
 */
class ChatDatabaseHelper(context: Context) : SQLiteOpenHelper(
    context.applicationContext,
    DATABASE_NAME,
    null,
    DATABASE_VERSION
) {

    companion object {
        const val DATABASE_NAME = "agrimind_chat.db"
        const val DATABASE_VERSION = 1

        // Table: conversations
        const val TABLE_CONVERSATIONS = "conversations"
        const val COL_CONV_ID = "id"
        const val COL_CONV_TITLE = "title"
        const val COL_CONV_CREATED_AT = "created_at"
        const val COL_CONV_UPDATED_AT = "updated_at"
        const val COL_CONV_LANGUAGE = "language"
        const val COL_CONV_CASE_ID = "case_id"

        // Table: chat_messages
        const val TABLE_MESSAGES = "chat_messages"
        const val COL_MSG_ID = "id"
        const val COL_MSG_CONV_ID = "conversation_id"
        const val COL_MSG_ROLE = "role"
        const val COL_MSG_CONTENT = "content"
        const val COL_MSG_CITATIONS_JSON = "citations_json"
        const val COL_MSG_HAS_EVIDENCE = "has_sufficient_evidence"
        const val COL_MSG_GENERATION_MODE = "generation_mode"
        const val COL_MSG_DISEASE_TARGET = "disease_target"
        const val COL_MSG_LANGUAGE = "language"
        const val COL_MSG_IS_ERROR = "is_error"
        const val COL_MSG_TIMESTAMP = "timestamp"

        private const val TAG = "ChatDatabaseHelper"
    }

    override fun onConfigure(db: SQLiteDatabase) {
        super.onConfigure(db)
        // Enable foreign key constraints for ON DELETE CASCADE
        db.setForeignKeyConstraintsEnabled(true)
    }

    override fun onCreate(db: SQLiteDatabase) {
        Log.i(TAG, "Creating AgriMind SQLite chat tables (version $DATABASE_VERSION)...")

        val createConversationsTable = """
            CREATE TABLE $TABLE_CONVERSATIONS (
                $COL_CONV_ID TEXT PRIMARY KEY,
                $COL_CONV_TITLE TEXT NOT NULL,
                $COL_CONV_CREATED_AT INTEGER NOT NULL,
                $COL_CONV_UPDATED_AT INTEGER NOT NULL,
                $COL_CONV_LANGUAGE TEXT NOT NULL,
                $COL_CONV_CASE_ID TEXT
            );
        """.trimIndent()

        val createMessagesTable = """
            CREATE TABLE $TABLE_MESSAGES (
                $COL_MSG_ID TEXT PRIMARY KEY,
                $COL_MSG_CONV_ID TEXT NOT NULL,
                $COL_MSG_ROLE TEXT NOT NULL,
                $COL_MSG_CONTENT TEXT NOT NULL,
                $COL_MSG_CITATIONS_JSON TEXT,
                $COL_MSG_HAS_EVIDENCE INTEGER NOT NULL DEFAULT 1,
                $COL_MSG_GENERATION_MODE TEXT,
                $COL_MSG_DISEASE_TARGET TEXT,
                $COL_MSG_LANGUAGE TEXT NOT NULL,
                $COL_MSG_IS_ERROR INTEGER NOT NULL DEFAULT 0,
                $COL_MSG_TIMESTAMP INTEGER NOT NULL,
                FOREIGN KEY ($COL_MSG_CONV_ID) REFERENCES $TABLE_CONVERSATIONS ($COL_CONV_ID) ON DELETE CASCADE
            );
        """.trimIndent()

        val createMsgIndex = """
            CREATE INDEX idx_messages_conv_time ON $TABLE_MESSAGES ($COL_MSG_CONV_ID, $COL_MSG_TIMESTAMP ASC);
        """.trimIndent()

        val createConvIndex = """
            CREATE INDEX idx_conversations_updated ON $TABLE_CONVERSATIONS ($COL_CONV_UPDATED_AT DESC);
        """.trimIndent()

        db.execSQL(createConversationsTable)
        db.execSQL(createMessagesTable)
        db.execSQL(createMsgIndex)
        db.execSQL(createConvIndex)
        createOfflineQueueTable(db)
        Log.i(TAG, "AgriMind chat tables created successfully.")
    }

    override fun onOpen(db: SQLiteDatabase) {
        super.onOpen(db)
        createOfflineQueueTable(db)
    }

    private fun createOfflineQueueTable(db: SQLiteDatabase) {
        db.execSQL("""
            CREATE TABLE IF NOT EXISTS offline_action_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                local_image_path TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL
            );
        """.trimIndent())
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        Log.i(TAG, "Upgrading database from $oldVersion to $newVersion")
        // Safe incremental migrations can be placed here in future versions
    }
}
