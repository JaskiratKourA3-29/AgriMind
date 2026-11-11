package com.agrimind.app.util

/**
 * Android client-side hybrid language detection engine.
 * Accurately detects English, Hindi (Devanagari and Romanized Hinglish),
 * and Dogri (dialect markers in Devanagari and Romanized script).
 */
object LanguageDetector {

    private val DEVANAGARI_REGEX = Regex("[\\u0900-\\u097F]")

    // Distinct grammatical Dogri markers only (excluding general Hindi words like rog, spray, tamatar)
    private val DOGRI_DEVANAGARI_MARKERS = setOf(
        "तुस", "तुसी", "तुहंदे", "मिगी", "तुगी", "कुत्थे", "आख्या", "गल्ल",
        "कन्ने", "दस्सो", "गेया", "गेन", "कचे", "इयां", "किदां"
    )

    private val DOGRI_ROMANIZED_MARKERS = setOf(
        "tusan", "miggi", "tugi", "kuthe", "gall", "kanne", "dasso",
        "kehn", "kareyo", "aakhya", "lai", "chhad"
    )

    private val ROMANIZED_HINDI_KEYWORDS = setOf(
        "tamatar", "patte", "patta", "patti", "pattiyan", "dawai", "rog",
        "khad", "paani", "keede", "keeda", "fasal", "khet", "podha", "paudha",
        "beej", "spray", "chhidkaw", "chhidkav", "sukh", "pila", "pile", "daag",
        "dhabba", "kya", "kaise", "kab", "kitna", "kitni", "kitne", "kare",
        "karna", "dale", "dalna", "batao", "hai", "hain", "hoga", "tha", "raha",
        "rahe", "mera", "meri", "mere", "iski", "iske", "pe", "se", "ko"
    )

    /**
     * Analyzes query text and returns ISO language code: "en", "hi", or "doi".
     */
    fun detectLanguage(text: String): String {
        if (text.isBlank()) return "en"

        val cleaned = text.trim()
        val words = cleaned.lowercase().split(Regex("[\\s.,?!:;\"'()\\[\\]{}]+")).filter { it.isNotBlank() }

        // 1. Devanagari script detection
        if (DEVANAGARI_REGEX.containsMatchIn(cleaned)) {
            val dogriDevCount = words.count { it in DOGRI_DEVANAGARI_MARKERS }
            return if (dogriDevCount >= 1) "doi" else "hi"
        }

        // 2. Romanized Dogri detection
        if (words.any { it in DOGRI_ROMANIZED_MARKERS }) {
            return "doi"
        }

        // 3. Romanized Hindi / Hinglish keyword detection
        val hindiCount = words.count { it in ROMANIZED_HINDI_KEYWORDS }
        if (hindiCount >= 2 || (hindiCount >= 1 && words.size <= 4)) {
            return "hi"
        }

        return "en"
    }
}
