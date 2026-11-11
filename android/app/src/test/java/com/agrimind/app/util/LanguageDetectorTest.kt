package com.agrimind.app.util

import org.junit.Assert.assertEquals
import org.junit.Test

class LanguageDetectorTest {

    @Test
    fun testEnglishDetection() {
        val query1 = "How do I treat Early Blight in tomatoes?"
        val query2 = "What is the recommended fungicide dosage?"
        val query3 = "What are the early signs of disease?"

        assertEquals("en", LanguageDetector.detectLanguage(query1))
        assertEquals("en", LanguageDetector.detectLanguage(query2))
        assertEquals("en", LanguageDetector.detectLanguage(query3))
    }

    @Test
    fun testHindiDevanagariDetection() {
        val query1 = "टमाटर के पत्तों पर काले धब्बे दिख रहे हैं, क्या करूँ?"
        val query2 = "अर्ली ब्लाइट की रोकथाम के लिए कौन सी दवाई डालें?"

        assertEquals("hi", LanguageDetector.detectLanguage(query1))
        assertEquals("hi", LanguageDetector.detectLanguage(query2))
    }

    @Test
    fun testHinglishRomanizedDetection() {
        val query1 = "tamatar ke patte par dhabba hai konsi dawai spray kare?"
        val query2 = "kya kare rog rokne ke liye?"

        assertEquals("hi", LanguageDetector.detectLanguage(query1))
        assertEquals("hi", LanguageDetector.detectLanguage(query2))
    }

    @Test
    fun testDogriVernacularDetection() {
        val query1 = "तुस दस्सो टमाटर दे पत्ते सुक्की गेन"
        val query2 = "मिगी दस्सो केहड़ा स्प्रे करना ऐ"
        val query3 = "tusan dasso miggi ke spray kareyo"

        assertEquals("doi", LanguageDetector.detectLanguage(query1))
        assertEquals("doi", LanguageDetector.detectLanguage(query2))
        assertEquals("doi", LanguageDetector.detectLanguage(query3))
    }

    @Test
    fun testBlankFallbackToEnglish() {
        assertEquals("en", LanguageDetector.detectLanguage(""))
        assertEquals("en", LanguageDetector.detectLanguage("   "))
    }
}

