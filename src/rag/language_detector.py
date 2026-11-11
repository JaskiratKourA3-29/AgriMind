"""
AgriMind Multi-Lingual Language Detection Engine.
Accurately identifies English, Hindi (Devanagari and Romanized Hinglish),
and Dogri (Devanagari dialectal markers and Romanized vernacular).
"""

import re
from typing import Dict, Any, Tuple

# Devanagari Unicode Range
DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")

# Specific Dogri dialect lexical tokens (both Devanagari and Latin Romanized)
DOGRI_DEVANAGARI_MARKERS = {
    "तुस", "तुसी", "तुहंदे", "मिगी", "तुगी", "कुत्थे", "आख्या", "गल्ल",
    "कन्ने", "दस्सो", "गेया", "गेन", "कचे", "इयां", "किदां"
}

DOGRI_ROMANIZED_MARKERS = {
    "tusan", "miggi", "tugi", "kuthe", "gall", "kanne", "dasso",
    "kehn", "kareyo", "aakhya", "lai", "chhad"
}

# Romanized Hindi / Hinglish Agricultural & Conversational Keywords
ROMANIZED_HINDI_KEYWORDS = {
    # Agricultural specific
    "tamatar", "tamataron", "patte", "patta", "patti", "pattiyan", "dawai",
    "dawakhana", "rog", "khad", "paani", "keeda", "keede", "fasal", "khet",
    "podha", "paudha", "beej", "spray", "chhidkaw", "chhidkav",
    # Symptoms & Conditions
    "sukh", "sukha", "sukhe", "pila", "pile", "peela", "peele", "daag",
    "dhabba", "dhabbe", "sad", "sadan", "kharab", "jal", "kala", "kale",
    # Conversational function words
    "kya", "kaise", "kab", "kyu", "kyun", "kitna", "kitni", "kitne",
    "kare", "karein", "karna", "karni", "dale", "dalna", "batao", "bataiye",
    "hai", "hain", "ho", "hoga", "hogi", "tha", "thi", "the", "lag",
    "gaya", "gaye", "raha", "rahe", "rahi", "mera", "meri", "mere",
    "apne", "iske", "iski", "isko", "pe", "par", "me", "mein", "se",
    "ko", "aur", "ya", "nahi", "nahin", "mat"
}


def detect_language(text: str) -> Tuple[str, float, str]:
    """
    Detects language of incoming user query.
    Returns:
        (language_code, confidence, detection_method)
        where language_code is 'en', 'hi', or 'doi'.
    """
    if not text or not text.strip():
        return "en", 1.0, "default_empty"

    cleaned = text.strip()
    words = [w.lower().strip(".,?!:;\"'()[]{}") for w in cleaned.split()]

    # 1. Check for Devanagari script presence
    devanagari_chars = DEVANAGARI_REGEX.findall(cleaned)
    if devanagari_chars:
        # Check if specific Dogri lexical items are present in Devanagari
        dogri_dev_count = sum(1 for w in words if w in DOGRI_DEVANAGARI_MARKERS)
        if dogri_dev_count >= 1:
            return "doi", 0.95, "devanagari_dogri_markers"
        return "hi", 0.98, "devanagari_script_match"

    # 2. Check for Romanized Dogri markers
    dogri_matches = [w for w in words if w in DOGRI_ROMANIZED_MARKERS]
    if len(dogri_matches) >= 1:
        return "doi", 0.90, f"romanized_dogri_tokens: {','.join(dogri_matches)}"

    # 3. Check for Romanized Hindi / Hinglish keywords
    hindi_matches = [w for w in words if w in ROMANIZED_HINDI_KEYWORDS]
    total_words = max(len(words), 1)
    match_ratio = len(hindi_matches) / total_words

    # If at least 2 Hindi tokens are found or 1 strong keyword in short query
    if len(hindi_matches) >= 2 or (len(hindi_matches) >= 1 and total_words <= 4):
        confidence = min(0.60 + (len(hindi_matches) * 0.15), 0.99)
        return "hi", round(confidence, 2), f"romanized_hindi_tokens: {','.join(hindi_matches)}"

    # Default to English
    return "en", 0.95, "standard_latin_english"

