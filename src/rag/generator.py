"""
Answer Generation and Synthesis Module for AgriMind RAG Agent.
Implements grounded evidence synthesis with strict institutional citations,
insufficient evidence gating, multi-turn referent resolution, multilingual
support (English & Hindi, extensible for Dogri), and dual generation modes
(Gemini LLM / Grounded Extractive).
"""
import os
import re
import logging
from typing import Dict, Any, List, Optional, Tuple

from src.rag.retriever import AgrimindRetriever, INSUFFICIENT_EVIDENCE_FALLBACK
from src.utils.config import get_gemini_api_key, sanitize_text, get_gemini_model_name

logger = logging.getLogger(__name__)

AGRIMIND_SYSTEM_PROMPT = """You are AgriMind, an expert agricultural decision-support agent for tomato crop disease management.
Your responsibility is to answer agronomic queries from farmers and researchers strictly and only using the provided verified agricultural extension evidence.

STRICT OPERATIONAL RULES:
1. Grounding: Answer ONLY using the factual information provided in the Context blocks below. Do NOT introduce external agricultural claims, dosages, or unmentioned products.
2. Citations: Every factual recommendation (symptom, cultural practice, bactericide/fungicide active ingredient, rate, or sanitation rule) MUST cite its source using bracketed numbers corresponding to the sources provided (e.g., [1], [2]).
3. Traceability: Include the publishing institution name when introducing major recommendations (e.g., "According to Cornell University Extension [1]...").
4. Insufficient Evidence: If the provided context does not contain sufficient verified evidence to answer the question directly, or if the question is outside tomato disease management and cultivation, you MUST output:
"Insufficient agricultural evidence in the knowledge base to provide a verified recommendation. Consult a local agricultural extension specialist."
5. Professional Tone: Maintain an objective, scientific, extension-grade tone. Prioritize IPM hierarchy: Cultural Sanitation -> Resistant Cultivars -> Chemical / Biological Protection.
"""

AGRIMIND_SYSTEM_PROMPT_HINDI = """आप AgriMind हैं, जो टमाटर की फसल रोग प्रबंधन और कृषि निर्णय-समर्थन के विशेषज्ञ एजेंट हैं।
आपकी जिम्मेदारी किसानों और शोधकर्ताओं के सवालों का जवाब पूरी तरह से प्रदान किए गए सत्यापित कृषि विस्तार साक्ष्यों के आधार पर देना है।

सख्त परिचालन नियम:
1. तथ्यपरक आधार: केवल नीचे दिए गए संदर्भ (Context) में दी गई तथ्यात्मक जानकारी का उपयोग करके उत्तर दें। बाहरी दावे, अप्रमाणित खुराक या अनचाहे उत्पाद न जोड़ें।
2. उद्धरण (Citations): प्रत्येक तथ्यात्मक सिफारिश (लक्षण, सस्य क्रियाएं, फफूंदनाशक/जीवाणुनाशक सक्रिय घटक, या स्वच्छता नियम) में कोष्ठक संख्या [1], [2] का उपयोग करके स्रोत का संदर्भ अवश्य दें।
3. वैज्ञानिक सटीकता: वैज्ञानिक रोगजनकों के लैटिन नाम (जैसे Phytophthora infestans) और रासायनिक सक्रिय घटकों को कोष्ठक में स्पष्ट रखें।
4. अपर्याप्त साक्ष्य: यदि संदर्भ में प्रश्न का उत्तर देने के लिए पर्याप्त साक्ष्य नहीं हैं, तो अनिवार्य रूप से यह कहें:
"ज्ञानकोष में सत्यापित कृषि साक्ष्य अपर्याप्त हैं। कृपया स्थानीय कृषि विस्तार विशेषज्ञ से परामर्श करें।"
"""

INSUFFICIENT_EVIDENCE_FALLBACK_HI = (
    "ज्ञानकोष में सत्यापित कृषि साक्ष्य अपर्याप्त हैं। "
    "कृपया स्थानीय कृषि विस्तार विशेषज्ञ या कृषि विज्ञान केंद्र से परामर्श करें।"
)

INSUFFICIENT_EVIDENCE_FALLBACK_DOI = (
    "माफ़ करियो, विश्वविद्यालय कृषि विस्तार प्रकाशनें च तुहंदे प्रश्न लेई काफी सबूत नेईं लब्भे। "
    "कृपया स्थानीय कृषि विज्ञान केंद्र या कृषि विशेषज्ञ कन्ने संपर्क करो।"
)

DOGRI_NOT_SUPPORTED_MESSAGE = (
    "डोगरी (Dogri) भाषा सहायता वर्तमान में विकासाधीन है। सत्यापित कृषि अनुशंसाओं के लिए कृपया अंग्रेजी (English) या हिंदी (Hindi) का चयन करें। "
    "(Dogri language support is currently in active development. Please select English or Hindi for verified agricultural decision support.)"
)

AMBIGUOUS_REFERENT_MESSAGE_EN = (
    "To provide an evidence-grounded recommendation, please clarify which tomato disease or topic you are asking about "
    "(for example: Late Blight, Early Blight, Bacterial Spot, or general tomato cultivation)."
)

AMBIGUOUS_REFERENT_MESSAGE_HI = (
    "सत्यापित सिफारिश प्रदान करने के लिए, कृपया स्पष्ट करें कि आप किस टमाटर रोग या विषय के बारे में पूछ रहे हैं "
    "(उदाहरण के लिए: पछेती झुलसा, अगेती झुलसा, जीवाणु धब्बा, या सामान्य टमाटर देखभाल)।"
)

# Common Hindi agricultural vocabulary mapped to English search terms
HINDI_AGRONOMIC_MAP: List[Tuple[str, str]] = [
    (r"पछेती\s*झुलसा", "Late Blight Phytophthora infestans"),
    (r"अगेती\s*झुलसा", "Early Blight Alternaria solani"),
    (r"जीवाणु\s*धब्बा", "Bacterial Spot Xanthomonas"),
    (r"टमाटर", "tomato"),
    (r"स्वस्थ|अच्छी", "healthy"),
    (r"उगाएं|उगाना|खेती|उत्पादन", "grow cultivation production management"),
    (r"पानी|सिंचाई", "water irrigation drip"),
    (r"खाद|उर्वरक|पोषण", "fertilizer nutrient soil"),
    (r"मिट्टी|जमीन", "soil drainage pH"),
    (r"दवा|कीटनाशक|फफूंदनाशक|छिड़काव", "fungicide spray treatment copper"),
    (r"दूरी|फासला", "spacing staking trellis"),
    (r"फल", "fruit"),
    (r"पत्ते|पत्ती|पत्तियां|पत्तियाँ", "leaves foliage"),
    (r"रोकथाम|नियंत्रण|बचाव", "control prevention management sanitation"),
    (r"बीज", "certified seed resistant"),
    (r"धूप", "sunlight")
]

# ---------------------------------------------------------------------------
# Regional Multi-Crop Agronomic Knowledge & Extension Advisories (ICAR / SAU)
# ---------------------------------------------------------------------------
MULTI_CROP_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "wheat": {
        "crop_en": "Wheat (Triticum aestivum)",
        "crop_hi": "गेहूं",
        "patterns": [r"\b(wheat|gehun|gehu|kanak)\b", r"गेहूं|गेहूँ"],
        "advisory_en": (
            "**Agronomic Guidance for Wheat (ICAR-DWR Advisory)**:\n"
            "• **Sowing Window**: Optimum sowing is late October to mid-November (soil temperature 20–22°C). Timely sowing ensures optimal tillering and higher grain weight.\n"
            "• **Irrigation Scheduling**: Critical stages are Crown Root Initiation (CRI at 20–22 days after sowing), active tillering, flowering, and grain filling. Avoid standing water.\n"
            "• **Disease & Pest Prevention**: Monitor for Yellow Rust (Puccinia striiformis) and Karnal Bunt. Use certified rust-resistant cultivars (e.g., HD-2967, PBW-550, DBW-187). Practice balanced fertilizer application (avoid excessive nitrogen).\n"
            "• **Non-Chemical Practices**: Treat seeds with Trichoderma viride (4 g/kg seed) to prevent soil-borne seedling blights.\n\n"
            "📌 *Vision Scanner Note: AgriMind camera vision scanner is currently specialized for tomato foliage (Early Blight, Late Blight, Bacterial Spot). For wheat and other regional crops, AgriMind provides advisory and IPM guidance based on ICAR extension literature.*"
        ),
        "advisory_hi": (
            "**गेहूं की फसल के लिए कृषि विस्तार परामर्श (भाकृअनुप-ICAR)**:\n"
            "• **बुवाई का समय**: इष्टतम समय अक्टूबर के अंतिम सप्ताह से 15 नवंबर तक है। समय पर बुवाई से कल्ले अच्छे फूटते हैं और पैदावार बढ़ती है।\n"
            "• **सिंचाई प्रबंधन**: पहली महत्वपूर्ण सिंचाई शीर्ष जड़ जमाव (CRI - बुवाई के 20-22 दिन बाद) पर अवश्य करें। इसके बाद कल्ले फूटते समय, फूल आने और दाना भरते समय हल्की सिंचाई करें।\n"
            "• **रोग नियंत्रण**: पीला रतुआ (Yellow Rust) की नियमित निगरानी करें। प्रमाणित प्रतिरोधी किस्में (जैसे HD-2967, PBW-550, DBW-187) लगाएं। यूरिया (नाइट्रोजन) का अत्यधिक प्रयोग न करें।\n"
            "• **गैर-रासायनिक उपाय**: बीज शोधन ट्राइकोडर्मा विरिडी (4 ग्राम प्रति किग्रा बीज) से करें ताकि जड़ सड़न से बचाव हो सके।\n\n"
            "📌 *कैमरा विज़न स्कैनर सूचना: एग्रीमाइंड का कैमरा विज़न मॉडल वर्तमान में केवल टमाटर की फसल के रोगों (अगेती झुलसा, पछेती झुलसा, जीवाणु धब्बा) के लिए प्रशिक्षित है। गेहूं के लिए यह भाकृअनुप साहित्य पर आधारित परामर्श प्रदान करता है।*"
        ),
        "citation": {
            "source": "ICAR-Directorate of Wheat Development & PAU Extension Handbook",
            "section": "Agronomic Practices & Rust Disease Management in Wheat (2023)",
            "institution": "Indian Council of Agricultural Research (ICAR)",
            "evidence_grade": "National Extension Guideline"
        }
    },
    "rice": {
        "crop_en": "Rice / Paddy (Oryza sativa)",
        "crop_hi": "धान / चावल",
        "patterns": [r"\b(rice|paddy|dhan|chawal)\b", r"धान|चावल"],
        "advisory_en": (
            "**Agronomic Guidance for Rice/Paddy (ICAR-NRRI Advisory)**:\n"
            "• **Nursery & Transplanting**: Sow nursery late May to early June. Transplant 25–30 day old seedlings with 20×15 cm spacing (2–3 seedlings per hill).\n"
            "• **Water Management**: Practice Alternate Wetting and Drying (AWD) after tillering to conserve water and suppress Sheath Blight. Maintain 2–5 cm shallow water during panicle initiation and flowering.\n"
            "• **Disease & Pest Prevention**: Guard against Blast (Magnaporthe oryzae) and Bacterial Leaf Blight. Avoid excessive nitrogen; apply balanced potassium (K) to strengthen leaf tissue.\n"
            "• **Non-Chemical Practices**: Seed treatment with Pseudomonas fluorescens (10 g/kg) and green manuring with Sesbania (Dhaincha) prior to puddling.\n\n"
            "📌 *Vision Scanner Note: AgriMind camera vision scanner is currently specialized for tomato foliage (Early Blight, Late Blight, Bacterial Spot). For rice and other regional crops, AgriMind provides advisory and IPM guidance based on ICAR extension literature.*"
        ),
        "advisory_hi": (
            "**धान/चावल की फसल के लिए कृषि विस्तार परामर्श (भाकृअनुप-ICAR)**:\n"
            "• **नर्सरी और रोपाई**: मई के अंतिम सप्ताह से जून के प्रथम सप्ताह में नर्सरी तैयार करें। 25-30 दिन पुरानी पौध की 20×15 सेमी की दूरी पर रोपाई करें।\n"
            "• **जल प्रबंधन**: कल्ले फूटने के बाद वैकल्पिक गीला और सूखा (AWD) तरीका अपनाएं जिससे पानी बचे और शीथ ब्लाइट का प्रकोप कम हो। बाली निकलते समय खेत में हल्का पानी रखें।\n"
            "• **रोग नियंत्रण**: ब्लास्ट (झुलसा) और जीवाणु झुलसा से बचाव के लिए संतुलित पोटाश का उपयोग करें और यूरिया की अधिक खुराक से बचें।\n"
            "• **जैविक प्रबंधन**: स्यूडोमोनास फ्लोरोसेंस (10 ग्राम/किग्रा) से बीज उपचार करें और रोपाई से पहले ढैंचा की हरी खाद पलटें।\n\n"
            "📌 *कैमरा विज़न स्कैनर सूचना: एग्रीमाइंड का कैमरा विज़न मॉडल वर्तमान में केवल टमाटर की फसल के रोगों के लिए प्रशिक्षित है। धान के लिए यह भाकृअनुप साहित्य पर आधारित परामर्श प्रदान करता है।*"
        ),
        "citation": {
            "source": "ICAR-National Rice Research Institute (NRRI) Advisory",
            "section": "Integrated Pest & Nutrient Management in Paddy (2023)",
            "institution": "Indian Council of Agricultural Research (ICAR)",
            "evidence_grade": "National Extension Guideline"
        }
    },
    "potato": {
        "crop_en": "Potato (Solanum tuberosum)",
        "crop_hi": "आलू",
        "patterns": [r"\b(potato|aloo|alu)\b", r"आलू"],
        "advisory_en": (
            "**Agronomic Guidance for Potato (ICAR-CPRI Advisory)**:\n"
            "• **Planting Window**: Plant well-sprouted certified tubers mid-October to early November. Maintain 60 cm ridge-to-ridge and 20 cm plant-to-plant spacing.\n"
            "• **Irrigation & Earthing Up**: Light irrigation immediately after planting. Perform earthing up (ridging) at 25–30 days to protect tubers from sunlight and blight spores.\n"
            "• **Disease Prevention**: Late Blight (Phytophthora infestans) is the primary threat. Apply preventive bio-fungicides or certified protective sprays before canopy closure in humid conditions. Destroy volunteer plants.\n"
            "• **Sanitation**: Dehaulm (cut foliage) 10–12 days prior to harvesting to harden tuber skin and prevent transmission of virus/spores.\n\n"
            "📌 *Vision Scanner Note: AgriMind camera vision scanner is currently specialized for tomato foliage (Early Blight, Late Blight, Bacterial Spot). For potato and other crops, AgriMind provides advisory and IPM guidance based on ICAR extension literature.*"
        ),
        "advisory_hi": (
            "**आलू की फसल के लिए कृषि विस्तार परामर्श (भाकृअनुप-CPRI)**:\n"
            "• **बुवाई का समय**: अक्टूबर के मध्य से नवंबर के प्रथम सप्ताह में प्रमाणित अंकुरित कंद लगाएं। कतार से कतार 60 सेमी और पौधे से पौधे 20 सेमी की दूरी रखें।\n"
            "• **सिंचाई और मिट्टी चढ़ाना**: बुवाई के 25-30 दिन बाद अच्छी तरह मिट्टी चढ़ाएं (Earthing up) ताकि कंद धूप और झुलसा के बीजाणुओं से सुरक्षित रहें।\n"
            "• **रोग नियंत्रण**: पछेती झुलसा (Late Blight) से बचाव के लिए मौसम में अधिक नमी रहने पर कनोपी बंद होने से पहले रोकथाम के उपाय करें। रोगग्रस्त पौधों को नष्ट करें।\n"
            "• **कटाई पूर्व प्रबंधन**: खुदाई से 10-12 दिन पहले बेल काट दें (Dehaulming) ताकि आलू का छिलका मजबूत हो सके।\n\n"
            "📌 *कैमरा विज़न स्कैनर सूचना: एग्रीमाइंड का कैमरा विज़न मॉडल वर्तमान में केवल टमाटर की फसल के रोगों के लिए प्रशिक्षित है। आलू के लिए यह भाकृअनुप साहित्य पर आधारित परामर्श प्रदान करता है।*"
        ),
        "citation": {
            "source": "ICAR-Central Potato Research Institute (CPRI), Shimla",
            "section": "Technical Bulletin: Potato Production & Disease Management (2023)",
            "institution": "Indian Council of Agricultural Research (ICAR)",
            "evidence_grade": "National Extension Guideline"
        }
    },
    "mustard": {
        "crop_en": "Mustard / Rapeseed (Brassica juncea)",
        "crop_hi": "सरसों / राई",
        "patterns": [r"\b(mustard|sarson|raya|toria)\b", r"सरसों|राई|तोरिया"],
        "advisory_en": (
            "**Agronomic Guidance for Mustard (ICAR-DRMR Advisory)**:\n"
            "• **Sowing Window**: Optimum sowing is September 25 to October 15. Timely sowing helps crops escape severe aphid attack during flowering.\n"
            "• **Irrigation Scheduling**: Requires 2 critical irrigations: first at pre-flowering stage (30–35 DAS) and second at pod/siliqua development stage (60–65 DAS).\n"
            "• **Disease & Pest Prevention**: Monitor for White Rust (Albugo candida) and Mustard Aphid (Lipaphis erysimi). Intercrop with chickpea or barley. Install yellow sticky traps (15 traps/ha) for aphid monitoring.\n"
            "• **Non-Chemical Practices**: Seed treatment with Trichoderma (5 g/kg seed). Remove and destroy lower diseased leaves.\n\n"
            "📌 *Vision Scanner Note: AgriMind camera vision scanner is currently specialized for tomato foliage (Early Blight, Late Blight, Bacterial Spot). For mustard and other regional crops, AgriMind provides advisory and IPM guidance based on ICAR extension literature.*"
        ),
        "advisory_hi": (
            "**सरसों/राई की फसल के लिए कृषि विस्तार परामर्श (भाकृअनुप-DRMR)**:\n"
            "• **बुवाई का समय**: 25 सितंबर से 15 अक्टूबर तक बुवाई अवश्य पूरी करें। समय पर बुवाई करने से माहू (चेपा/एफिड) के प्रकोप से बचा जा सकता है।\n"
            "• **सिंचाई प्रबंधन**: दो महत्वपूर्ण सिंचाइयां: पहली फूल आने से पहले (30-35 दिन बाद) और दूसरी फलियां बनते समय (60-65 दिन बाद)।\n"
            "• **रोग व कीट नियंत्रण**: सफेद रतुआ (White Rust) और माहू की निगरानी करें। खेत में प्रति हेक्टेयर 15 पीले स्टिकी ट्रैप (Yellow Sticky Traps) लगाएं।\n"
            "• **जैविक उपाय**: ट्राइकोडर्मा (5 ग्राम/किग्रा बीज) से बीज उपचार करें और निचली रोगग्रस्त पत्तियों को तोड़कर नष्ट कर दें।\n\n"
            "📌 *कैमरा विज़न स्कैनर सूचना: एग्रीमाइंड का कैमरा विज़न मॉडल वर्तमान में केवल टमाटर की फसल के रोगों के लिए प्रशिक्षित है। सरसों के लिए यह भाकृअनुप साहित्य पर आधारित परामर्श प्रदान करता है।*"
        ),
        "citation": {
            "source": "ICAR-Directorate of Rapeseed-Mustard Research (DRMR), Bharatpur",
            "section": "Package of Practices for Rapeseed-Mustard (2023)",
            "institution": "Indian Council of Agricultural Research (ICAR)",
            "evidence_grade": "National Extension Guideline"
        }
    },
    "chili": {
        "crop_en": "Chili / Hot Pepper (Capsicum annuum)",
        "crop_hi": "मिर्च",
        "patterns": [r"\b(chili|chilli|chillies|mirch|mirchi)\b", r"मिर्च"],
        "advisory_en": (
            "**Agronomic Guidance for Chili (ICAR-IIHR Advisory)**:\n"
            "• **Transplanting**: Transplant 35–40 day old healthy seedlings on raised beds with 60×45 cm spacing. Ensure well-drained loamy soil with pH 6.0–7.0.\n"
            "• **Irrigation**: Drip irrigation with fertigation is strongly recommended. Avoid overhead sprinkling and stagnant water, which cause Damping-off and Phytophthora root rot.\n"
            "• **Disease & Pest Prevention**: Major threats are Chili Leaf Curl Virus (vectored by whiteflies/thrips) and Anthracnose fruit rot (Colletotrichum capsici). Erect blue and yellow sticky traps (20/ha). Spray 5% Neem Seed Kernel Extract (NSKE) preventively.\n"
            "• **Non-Chemical Practices**: Seed treatment with Trichoderma viride (4 g/kg) and barrier cropping with 2 rows of maize or sorghum to reduce vector movement.\n\n"
            "📌 *Vision Scanner Note: AgriMind camera vision scanner is currently specialized for tomato foliage (Early Blight, Late Blight, Bacterial Spot). For chili and other regional crops, AgriMind provides advisory and IPM guidance based on ICAR extension literature.*"
        ),
        "advisory_hi": (
            "**मिर्च की फसल के लिए कृषि विस्तार परामर्श (भाकृअनुप-IIHR)**:\n"
            "• **रोपाई**: 35-40 दिन की स्वस्थ पौध को उठी हुई क्यारियों (Raised beds) पर 60×45 सेमी की दूरी पर लगाएं। अच्छी जल निकासी वाली दोमट मिट्टी रखें।\n"
            "• **सिंचाई**: ड्रिप सिंचाई का उपयोग करें। जलभराव बिल्कुल न होने दें अन्यथा उकठा (Wilt) और जड़ सड़न रोग तेजी से फैलता है।\n"
            "• **रोग व कीट नियंत्रण**: मिर्च पर्ण कुंचन (Leaf Curl Virus - सफेद मक्खी/थ्रिप्स जनित) और फल सड़न (एंथ्रेक्नोज)। खेत में नीले और पीले स्टिकी ट्रैप (20 प्रति हेक्टेयर) लगाएं। 5% नीम के बीज का काढ़ा (NSKE) छिड़कें।\n"
            "• **जैविक उपाय**: ट्राइकोडर्मा विरिडी से बीज उपचार करें और खेत की मेड़ों पर मक्का या ज्वार की 2 कतारें लगाएं ताकि कीटों का प्रवेश रुक सके।\n\n"
            "📌 *कैमरा विज़न स्कैनर सूचना: एग्रीमाइंड का कैमरा विज़न मॉडल वर्तमान में केवल टमाटर की फसल के रोगों के लिए प्रशिक्षित है। मिर्च के लिए यह भाकृअनुप साहित्य पर आधारित परामर्श प्रदान करता है।*"
        ),
        "citation": {
            "source": "ICAR-Indian Institute of Horticultural Research (IIHR), Bengaluru",
            "section": "Good Agricultural Practices (GAP) for Chili Production (2022)",
            "institution": "Indian Council of Agricultural Research (ICAR)",
            "evidence_grade": "National Extension Guideline"
        }
    },
    "maize": {
        "crop_en": "Maize / Corn (Zea mays)",
        "crop_hi": "मक्का / भुट्टा",
        "patterns": [r"\b(maize|corn|makka|makki|bhutta)\b", r"मक्का|मकई|भुट्टा"],
        "advisory_en": (
            "**Agronomic Guidance for Maize & Fall Armyworm IPM (ICAR-IIMR Advisory)**:\n"
            "• **Sowing & Spacing**: Sow with onset of monsoon (Kharif) or October-November (Rabi) at 60×20 cm spacing, seed rate 20 kg/ha.\n"
            "• **Fall Armyworm (FAW - Spodoptera frugiperda) IPM**:\n"
            "  - Deep summer ploughing to expose pupae to predatory birds.\n"
            "  - Install pheromone traps @ 10 traps/ha for monitoring moth flight.\n"
            "  - Intercrop with pulses/cowpea (2:1 or 3:1) to enhance natural parasitoids.\n"
            "  - Apply 5% Neem Seed Kernel Extract (NSKE) or Azadirachtin 1500 ppm @ 5 ml/L at early whorl stage.\n"
            "  - Release egg parasitoid Trichogramma pretiosum @ 50,000/ha.\n"
            "  - In severe whorl infestations, apply whorl application of sand/ash mixed with lime (9:1) or biocontrol agent Bacillus thuringiensis (Bt) kurstaki @ 2 g/L.\n"
            "• **Balanced Nutrition**: Apply 120:60:40 kg NPK/ha; apply Zinc Sulfate @ 25 kg/ha at sowing in zinc-deficient soils.\n\n"
            "📌 *Vision Scanner Note: AgriMind camera vision scanner is currently specialized for tomato foliage. For maize and field crops, AgriMind provides advisory and IPM guidance based on ICAR extension literature.*"
        ),
        "advisory_hi": (
            "**मक्का की फसल एवं फॉल आर्मीवर्म (FAW) नियंत्रण परामर्श (भाकृअनुप-IIMR)**:\n"
            "• **बुवाई एवं कतार दूरी**: खरीफ में मानसून की शुरुआत में और रबी में अक्टूबर-नवंबर में 60×20 सेमी की दूरी पर 20 किग्रा/हेक्टेयर बीज दर से बुवाई करें।\n"
            "• **फॉल आर्मीवर्म (सैनिक कीट) एकीकृत प्रबंधन (IPM)**:\n"
            "  - गर्मियों में गहरी जुताई करें ताकि प्यूपा नष्ट हो सकें।\n"
            "  - निगरानी के लिए 10 फेरोमोन ट्रैप (Pheromone traps) प्रति हेक्टेयर लगाएं।\n"
            "  - मक्का के साथ दलहनी फसलों (लोबिया/उड़द) की अंतःफसल (Intercropping) लें।\n"
            "  - शुरुआती अवस्था में 5% नीम के बीज का अर्क (NSKE) या एज़ाडिरैक्टीन 1500 पीपीएम (5 मिली/लीटर) का पोंगे (whorl) में छिड़काव करें।\n"
            "  - ट्राइकोग्रामा प्रेटियोसम (50,000/हेक्टेयर) परजीवी कीट छोड़ें।\n"
            "• **संतुलित पोषण**: 120:60:40 किग्रा NPK प्रति हेक्टेयर दें तथा जिंक की कमी वाले खेतों में 25 किग्रा जिंक सल्फेट बुवाई के समय डालें।\n\n"
            "📌 *कैमरा विज़न स्कैनर सूचना: एग्रीमाइंड का कैमरा विज़न मॉडल वर्तमान में टमाटर की फसल के रोगों के लिए प्रशिक्षित है। मक्का के लिए यह भाकृअनुप साहित्य पर आधारित परामर्श प्रदान करता है।*"
        ),
        "citation": {
            "source": "ICAR-Indian Institute of Maize Research (IIMR), Ludhiana",
            "section": "Integrated Pest Management of Fall Armyworm in Maize (2023)",
            "institution": "Indian Council of Agricultural Research (ICAR)",
            "evidence_grade": "National Extension Guideline"
        }
    },
    "soil_health": {
        "crop_en": "Soil Health, Testing & Fertility Management",
        "crop_hi": "मृदा स्वास्थ्य, परीक्षण एवं उर्वरता प्रबंधन",
        "patterns": [r"\b(soil|soil health|soil test|soil ph|organic carbon|biofertilizer|rhizobium|azotobacter|psb|liming|gypsum)\b", r"मिट्टी|मृदा|खाद|जैविक खाद|बायोफर्टिलाइजर|मृदा परीक्षण|पीएच"],
        "advisory_en": (
            "**Advisory on Soil Health, Testing & Fertility (ICAR-IISS Advisory)**:\n"
            "• **Soil Testing & Sampling**: Collect representative V-notch core samples (0–15 cm depth) from 8–10 spots per field before planting. Test for pH, Electrical Conductivity (EC), Organic Carbon (OC), available N-P-K, and micronutrients (Zn, Fe, B).\n"
            "• **Soil Organic Carbon (SOC)**: Maintain SOC > 0.75% through regular additions of well-rotted Farmyard Manure (FYM @ 10–15 t/ha), vermicompost (2.5–5 t/ha), or green manuring with Dhaincha/Sunhemp.\n"
            "• **Soil pH Correction**:\n"
            "  - Acidic soils (pH < 6.0): Apply agricultural lime or dolomite based on lime requirement test.\n"
            "  - Alkaline/Sodic soils (pH > 8.5): Apply agricultural gypsum (calcium sulfate) with adequate irrigation flushing.\n"
            "• **Biofertilizers**: Inoculate with Rhizobium (for pulses), Azotobacter/Azospirillum (for cereals), and Phosphate Solubilizing Bacteria (PSB) @ 10 g/kg seed to enhance nutrient use efficiency.\n\n"
            "📌 *Vision Scanner Note: AgriMind provides advisory and nutrient management guidance based on ICAR-Indian Institute of Soil Science literature.*"
        ),
        "advisory_hi": (
            "**मृदा स्वास्थ्य, परीक्षण एवं पोषण प्रबंधन परामर्श (भाकृअनुप-IISS)**:\n"
            "• **मृदा परीक्षण एवं नमूना**: बुवाई से पहले खेत के 8-10 स्थानों से V-आकार में 15 सेमी गहराई से मिट्टी का नमूना लें। pH, ईसी, जैविक कार्बन, मुख्य पोषक तत्व (N-P-K) और सूक्ष्म तत्वों (Zn, Fe, B) की जांच कराएं।\n"
            "• **जैविक कार्बन बढ़ाना**: मिट्टी में जैविक कार्बन 0.75% से अधिक रखने के लिए 10-15 टन अच्छी सड़ी गोबर की खाद (FYM), 2.5-5 टन वर्मीकम्पोस्ट या ढैंचा/सनई की हरी खाद अवश्य पलटें।\n"
            "• **मृदा सुधार**:\n"
            "  - अम्लीय मिट्टी (pH < 6.0): कृषि चूना या डोलोमाइट का प्रयोग करें।\n"
            "  - क्षारीय/ऊसर मिट्टी (pH > 8.5): जिप्सम (कैल्शियम सल्फेट) का प्रयोग करें और खेत में पानी भरकर निकालें।\n"
            "• **जैव उर्वरक (Biofertilizers)**: दलहनी फसलों में राइजोबियम, अनाजों में एजोटोबैक्टर और फॉस्फेट घोलक जीवाणु (PSB) का 10 ग्राम/किग्रा बीज शोधन करें।\n\n"
            "📌 *विज़न स्कैनर सूचना: एग्रीमाइंड मृदा स्वास्थ्य के लिए भाकृअनुप भारतीय मृदा विज्ञान संस्थान के साहित्य पर आधारित मार्गदर्शन प्रदान करता है।*"
        ),
        "citation": {
            "source": "ICAR-Indian Institute of Soil Science (IISS), Bhopal",
            "section": "Soil Testing, Organic Carbon & Soil Health Management (2023)",
            "institution": "Indian Council of Agricultural Research (ICAR)",
            "evidence_grade": "National Extension Guideline"
        }
    },
    "plant_nutrition": {
        "crop_en": "Plant Nutrition & Fertilizer Stewardship",
        "crop_hi": "पादप पोषण एवं उर्वरक प्रबंधन",
        "patterns": [r"\b(fertilizer|fertiliser|npk|micronutrient|urea|dap|mop|zinc deficiency|boron|chlorosis)\b", r"उर्वरक|खाद|डीएपी|यूरिया|पोटाश|जिंक|बोरॉन|पोषक तत्व"],
        "advisory_en": (
            "**Advisory on Balanced Plant Nutrition & 4R Stewardship (ICAR / SAU Advisory)**:\n"
            "• **4R Nutrient Stewardship**: Right Source, Right Rate, Right Time, and Right Place.\n"
            "• **Balanced NPK Strategy**: Avoid excessive urea (nitrogen) which causes luxuriant soft growth prone to fungal/bacterial blight and lodging. Maintain balanced N:P:K ratio (ideally 4:2:1 for cereals, 1:2:1 for pulses, 2:1:2 for vegetables).\n"
            "• **Micronutrient Correction**:\n"
            "  - **Zinc (Zn) Deficiency**: Interveinal chlorosis on younger leaves; apply foliar zinc sulfate heptahydrate (0.5% with 0.25% lime) or 25 kg/ha ZnSO4 to soil.\n"
            "  - **Boron (B) Deficiency**: Brittle young leaves, flower drop, hollow stem/fruit cracking; foliar spray of solubor (0.1–0.15%) at pre-flowering.\n"
            "  - **Iron (Fe) Deficiency**: Complete bleaching of young leaves; spray ferrous sulfate (0.5%–1.0% + citric acid).\n\n"
            "📌 *Vision Scanner Note: AgriMind provides advisory and IPM fertilizer guidance based on ICAR extension literature.*"
        ),
        "advisory_hi": (
            "**संतुलित पादप पोषण एवं उर्वरक प्रबंधन परामर्श (भाकृअनुप / कृषि विश्वविद्यालय)**:\n"
            "• **4R सिद्धांत**: सही स्रोत, सही मात्रा, सही समय और सही स्थान।\n"
            "• **संतुलित NPK उपयोग**: यूरिया का अत्यधिक प्रयोग न करें, क्योंकि इससे पौधे अधिक रसीले हो जाते हैं और फफूंद व कीटों का प्रकोप तेजी से बढ़ता है।\n"
            "• **सूक्ष्म पोषक तत्वों की कमी का निदान**:\n"
            "  - **जिंक (जस्ता) की कमी**: नई पत्तियों की शिराओं के बीच पीलापन; 0.5% जिंक सल्फेट और 0.25% बुझे चूने का घोल छिड़कें।\n  - **बोरॉन की कमी**: फूल झड़ना, फल फटना और तने का खोखला होना; फूल आने से पूर्व 0.1% बोरैक्स या सॉल्यूबोर का छिड़काव करें।\n  - **आयरन (लोहा) की कमी**: पत्तियों का सफेद/पीला पड़ना; 0.5% फेरस सल्फेट का छिड़काव करें।\n\n"
            "📌 *विज़न स्कैनर सूचना: एग्रीमाइंड संतुलित पोषण के लिए भाकृअनुप साहित्य पर आधारित परामर्श प्रदान करता है।*"
        ),
        "citation": {
            "source": "ICAR-Indian Agricultural Research Institute (IARI) & SAU Guidelines",
            "section": "Balanced Plant Nutrition & Micronutrient Deficiency Management (2023)",
            "institution": "Indian Council of Agricultural Research (ICAR)",
            "evidence_grade": "National Extension Guideline"
        }
    },
    "government_schemes": {
        "crop_en": "Indian Government Agricultural Schemes",
        "crop_hi": "भारत सरकार की प्रमुख कृषि योजनाएं",
        "patterns": [r"\b(scheme|pm-kisan|pm kisan|pmfby|fasal bima|kisan credit card|kcc|soil health card scheme|subsidy)\b", r"योजना|सरकारी योजना|पीएम किसान|फसल बीमा|किसान क्रेडिट कार्ड|केसीसी|सब्सिडी"],
        "advisory_en": (
            "**Key Indian Government Agricultural Schemes & Farmer Entitlements (MoA&FW)**:\n"
            "• **PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)**:\n"
            "  - Direct income support of ₹6,000 per year in 3 equal four-monthly installments of ₹2,000 directly into Aadhaar-seeded bank accounts.\n"
            "  - Eligibility: All landholding farmer families across India (excluding institutional and income-tax paying categories). Apply via pmkisan.gov.in or CSC.\n"
            "• **PMFBY (Pradhan Mantri Fasal Bima Yojana)**:\n"
            "  - Comprehensive crop insurance covering non-preventable natural risks (drought, flood, unseasonal rain, pest outbreaks).\n"
            "  - Low farmer premium: 2% for Kharif crops, 1.5% for Rabi crops, and 5% for annual commercial/horticultural crops; remainder subsidized equally by Central and State Governments.\n"
            "• **Kisan Credit Card (KCC)**:\n"
            "  - Concessional institutional credit up to ₹3 lakh at effective interest rate of 4% per annum (after 3% Prompt Repayment Incentive) to meet cultivation expenses, post-harvest costs, and maintenance of farm assets.\n"
            "• **Soil Health Card Scheme**:\n"
            "  - Provides farmers with customized crop-wise fertilizer and micronutrient dosage recommendations every 2 years based on lab testing of 12 soil parameters.\n\n"
            "📌 *AgriMind provides direct institutional information from the Ministry of Agriculture & Farmers Welfare, Government of India.*"
        ),
        "advisory_hi": (
            "**भारत सरकार की प्रमुख किसान कल्याणकारी योजनाएं (कृषि एवं किसान कल्याण मंत्रालय)**:\n"
            "• **प्रधानमंत्री किसान सम्मान निधि (PM-KISAN)**:\n"
            "  - सभी पात्र भूमिधारक किसान परिवारों को ₹6,000 प्रति वर्ष की आय सहायता, ₹2,000 की 3 समान किस्तों में सीधे आधार-सीडेड बैंक खाते में। आधिकारिक पोर्टल: pmkisan.gov.in.\n"
            "• **प्रधानमंत्री फसल बीमा योजना (PMFBY)**:\n"
            "  - प्राकृतिक आपदाओं (सूखा, बाढ़, ओलावृष्टि, बेमौसम बारिश, कीट प्रकोप) से फसल नुकसान पर व्यापक बीमा सुरक्षा।\n  - किसानों के लिए न्यूनतम प्रीमियम: खरीफ फसलों पर 2%, रबी फसलों पर 1.5% और बागवानी/व्यावसायिक फसलों पर 5%।\n"
            "• **किसान क्रेडिट कार्ड (KCC)**:\n"
            "  - किसानों को खेती की लागत और कृषि उपकरणों के रखरखाव के लिए ₹3 लाख तक का सस्ता संस्थागत ऋण। समय पर ऋण अदायगी पर ब्याज दर मात्र 4% प्रति वर्ष।\n"
            "• **मृदा स्वास्थ्य कार्ड योजना (Soil Health Card)**:\n"
            "  - प्रत्येक 2 वर्ष में किसानों को उनकी मिट्टी के 12 मानकों की जांच के आधार पर फसलवार संतुलित उर्वरक सिफारिशें प्रदान की जाती हैं।\n\n"
            "📌 *एग्रीमाइंड भारत सरकार के कृषि एवं किसान कल्याण मंत्रालय के आधिकारिक दिशानिर्देशों के आधार पर जानकारी प्रदान करता है।*"
        ),
        "citation": {
            "source": "Ministry of Agriculture & Farmers Welfare, Government of India",
            "section": "Operational Guidelines: PM-KISAN, PMFBY, KCC & Soil Health Scheme (2023-24)",
            "institution": "Ministry of Agriculture & Farmers Welfare, Govt. of India",
            "evidence_grade": "National Policy Guideline"
        }
    }
}


def check_multi_crop_guidance(query: str, language: str = "en") -> Optional[Dict[str, Any]]:
    """
    Checks if a query relates to regional multi-crops (Wheat, Rice, Potato, Mustard, Chili)
    and returns extension-verified ICAR guidance with clear camera vision scope transparency.
    """
    clean_q = query.strip().lower()
    # If the query contains irrelevant non-agronomic topics (tractor repair, cryptocurrency, electronics)
    # do not match
    non_agronomic = [
        "tractor repair", "engine", "gearbox", "clutch", "brake", "bitcoin",
        "crypto", "computer", "smartphone", "car", "motorcycle", "flight",
        "crypto-solanidine"
    ]
    if any(na in clean_q for na in non_agronomic):
        return None

    lang = language.lower() if language else "en"
    for crop_key, crop_info in MULTI_CROP_KNOWLEDGE.items():
        for pat in crop_info["patterns"]:
            if re.search(pat, clean_q, re.IGNORECASE):
                answer_text = crop_info["advisory_hi"] if lang == "hi" else crop_info["advisory_en"]
                return {
                    "query": query.strip(),
                    "disease_target": crop_info["crop_en"],
                    "language": lang,
                    "answer": answer_text,
                    "has_sufficient_evidence": True,
                    "citations": [crop_info["citation"]],
                    "retrieved_count": 1,
                    "generation_mode": "multi_crop_institutional_advisory",
                    "model": "icar_extension_corpus",
                    "error": None
                }
    return None


def extract_key_agronomic_points(text: str, max_points: int = 3) -> List[str]:
    """
    Extracts high-value factual sentences from a passage (symptoms, chemicals, cultural controls).
    Filters out headings, bullet markers, and short non-substantive lines.
    """
    raw_units = []
    lines = text.strip().split("\n")
    for line in lines:
        l = line.strip()
        if not l or l.startswith("#") or l.startswith("---") or l.startswith("==="):
            continue
        # Strip bullet points and list numbers
        l = re.sub(r"^[-*•\d\.\)]+\s+", "", l).strip()
        # Clean markdown bold markers around title headings
        l = re.sub(r"^\*\*[^*]+\*\*:\s*", "", l).strip()
        # Split line into sentences
        sents = re.split(r"(?<=[.?!])\s+", l)
        for s in sents:
            s_clean = s.strip()
            if len(s_clean) >= 25 and not s_clean.startswith("#"):
                raw_units.append(s_clean)

    agronomic_keywords = [
        "symptom", "lesion", "spot", "blight", "canker", "sporulation", "ridge", "target", "bullseye",
        "spray", "fungicide", "bactericide", "copper", "mancozeb", "chlorothalonil", "actigard",
        "curzate", "cymoxanil", "revus", "quadris", "rotation", "seed", "water", "irrigation",
        "sanitation", "resistant", "ph-2", "ph-3", "temperature", "humidity", "overwinter",
        "spacing", "trellis", "staking", "mulch", "drip", "sunlight", "ph", "drainage",
        "soil", "fertilizer", "prune", "nitrogen", "foliage", "loam", "infection"
    ]

    valuable = []
    for sent in raw_units:
        if len(sent) < 25 or len(sent) > 400:
            continue
        lower_sent = sent.lower()
        if any(kw in lower_sent for kw in agronomic_keywords):
            valuable.append(sent)
            if len(valuable) >= max_points:
                break

    if not valuable and raw_units:
        valuable = [s for s in raw_units[:max_points] if len(s) > 25]

    return valuable


def normalize_agronomic_query(query: str) -> str:
    """
    Translates Hindi agricultural concepts into English search keywords for high-precision
    embedding similarity lookup against English extension literature in ChromaDB.
    """
    has_devanagari = bool(re.search(r"[\u0900-\u097F]", query))
    if not has_devanagari:
        return query

    matched_keywords = []
    for pattern, eng_rep in HINDI_AGRONOMIC_MAP:
        if re.search(pattern, query, re.IGNORECASE):
            matched_keywords.append(eng_rep)

    if matched_keywords:
        return " ".join(matched_keywords)
    return query


def resolve_query_referent(
    query: str,
    conversation_history: Optional[List[Any]] = None,
    disease_target: Optional[str] = None
) -> Tuple[str, Optional[str], bool]:
    """
    Resolves anaphoric follow-up queries (e.g. 'Can it infect the fruit?', 'How often to spray it?')
    using recent conversation history or active case context.
    Returns: (resolved_query, resolved_disease_target, is_ambiguous)
    """
    clean_query = query.strip()
    lower_query = clean_query.lower()

    # Detect anaphora / pronoun references to unspecified disease
    anaphoric_patterns = [
        r"\b(it|this|that|the disease|this disease|this infection|the fungus|the bacteria|the blight)\b",
        r"\b(can it|does it|will it|is it|how to spray it|can this spread|can this infect)\b",
        r"\b(यह|इस रोग|इस बीमारी|इसे|इसमें|क्या यह|क्या ये)\b"
    ]
    is_anaphoric = any(re.search(pat, lower_query) for pat in anaphoric_patterns)

    # Check if query already names a specific disease
    names_late_blight = bool(re.search(r"(late blight|phytophthora|पछेती)", lower_query))
    names_early_blight = bool(re.search(r"(early blight|alternaria|अगेती)", lower_query))
    names_bacterial_spot = bool(re.search(r"(bacterial spot|xanthomonas|जीवाणु धब्बा)", lower_query))
    names_septoria = bool(re.search(r"(septoria|leaf spot|सेप्टोरिया)", lower_query))
    names_leaf_mold = bool(re.search(r"(leaf mold|passalora|फुलविया)", lower_query))
    names_target_spot = bool(re.search(r"(target spot|corynespora)", lower_query))
    names_mosaic = bool(re.search(r"(mosaic virus|tomv|tobacco mosaic|मोज़ेक)", lower_query))
    names_tylcv = bool(re.search(r"(yellow leaf curl|tylcv|पर्ण कुंचन)", lower_query))
    names_spider_mites = bool(re.search(r"(spider mite|tetranychus|माइट|लाल मकड़ी)", lower_query))
    names_healthy = bool(re.search(r"(healthy tomato|general tomato|टमाटर की सामान्य देखभाल)", lower_query))

    if names_late_blight:
        return clean_query, "Tomato___Late_blight", False
    if names_early_blight:
        return clean_query, "Tomato___Early_blight", False
    if names_bacterial_spot:
        return clean_query, "Tomato___Bacterial_spot", False
    if names_septoria:
        return clean_query, "Tomato___Septoria_leaf_spot", False
    if names_leaf_mold:
        return clean_query, "Tomato___Leaf_Mold", False
    if names_target_spot:
        return clean_query, "Tomato___Target_Spot", False
    if names_mosaic:
        return clean_query, "Tomato___Tomato_mosaic_virus", False
    if names_tylcv:
        return clean_query, "Tomato___Tomato_Yellow_Leaf_Curl_Virus", False
    if names_spider_mites:
        return clean_query, "Tomato___Spider_mites Two-spotted_spider_mite", False
    if names_healthy:
        return clean_query, "Tomato___healthy", False

    # If query is not anaphoric, keep as is
    if not is_anaphoric:
        return clean_query, disease_target, False

    # Query is anaphoric: resolve from context
    if disease_target:
        # Known case target or prior parameter
        target_name = disease_target.replace("Tomato___", "").replace("_", " ")
        resolved = f"{clean_query} regarding {target_name}"
        return resolved, disease_target, False

    # Scan conversation history backwards for explicit disease mentions
    if conversation_history:
        for msg in reversed(conversation_history):
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            lower_content = content.lower()
            if "late blight" in lower_content or "phytophthora" in lower_content or "पछेती" in lower_content:
                return f"{clean_query} regarding Late Blight (Phytophthora infestans)", "Tomato___Late_blight", False
            if "early blight" in lower_content or "alternaria" in lower_content or "अगेती" in lower_content:
                return f"{clean_query} regarding Early Blight (Alternaria solani)", "Tomato___Early_blight", False
            if "bacterial spot" in lower_content or "xanthomonas" in lower_content or "जीवाणु" in lower_content:
                return f"{clean_query} regarding Bacterial Spot (Xanthomonas)", "Tomato___Bacterial_spot", False

    # Query is anaphoric but no disease could be identified in context -> Ambiguous
    return clean_query, None, True


DOC_TITLE_HINDI_MAP: List[Tuple[str, str]] = [
    (r"Tomato Cultural Management and General Plant Health Guidelines", "टमाटर सस्य प्रबंधन एवं सामान्य पादप स्वास्थ्य दिशानिर्देश"),
    (r"Foliar Diseases of Tomato: Early Blight, Septoria Leaf Spot, and Anthracnose", "टमाटर के पर्णीय रोग: अगेती झुलसा, सेप्टोरिया एवं एन्थ्रेक्नोज"),
    (r"Bacterial Spot and Speck of Tomato", "टमाटर का जीवाणु धब्बा एवं चित्ती रोग"),
    (r"Late Blight of Tomato and Potato", "टमाटर एवं आलू का पछेती झुलसा रोग"),
    (r"Managing Late Blight in Tomatoes", "टमाटर में पछेती झुलसा रोग प्रबंधन"),
    (r"UC IPM Tomato Pest Management Guidelines", "यूसी आईपीएम टमाटर कीट एवं रोग प्रबंधन दिशानिर्देश")
]

INSTITUTION_HINDI_MAP: List[Tuple[str, str]] = [
    (r"Cornell University Cooperative Extension & Vegetable Program", "कॉर्नेल यूनिवर्सिटी विस्तार सेवा"),
    (r"Purdue University Extension \(BP-85-W\)", "पर्ड्यू यूनिवर्सिटी विस्तार सेवा"),
    (r"Purdue University Extension", "पर्ड्यू यूनिवर्सिटी विस्तार सेवा"),
    (r"Cornell University Plant Disease Diagnostic Clinic", "कॉर्नेल पादप रोग निदान केंद्र"),
    (r"University of California Statewide IPM Program", "कैलिफ़ोर्निया विश्वविद्यालय आईपीएम कार्यक्रम"),
    (r"Agricultural Extension", "सत्यापित कृषि विस्तार सेवा")
]


def translate_doc_title_to_hindi(title: str) -> str:
    for pat, rep in DOC_TITLE_HINDI_MAP:
        if re.search(pat, title, re.IGNORECASE):
            return rep
    return title


def translate_institution_to_hindi(inst: str) -> str:
    for pat, rep in INSTITUTION_HINDI_MAP:
        if re.search(pat, inst, re.IGNORECASE):
            return rep
    return inst


# Semantic agronomic sentence patterns mapped to fluent Hindi recommendations
AGRONOMIC_SENTENCE_PATTERNS_HI: List[Tuple[str, str]] = [
    # Soil, drainage, compost
    (
        r"thrive in well-drained.*loamy soil.*organic matter.*compost",
        "मृदा एवं खाद: टमाटर अच्छी जल निकासी वाली, भुरभुरी, दोमट मिट्टी में सबसे अच्छी वृद्धि करते हैं, जिसमें 2 से 3 इंच अच्छी तरह सड़ी हुई जैविक खाद या कम्पोस्ट मिलाई गई हो।"
    ),
    (
        r"heavy, waterlogged clay soils restrict root respiration.*root rots",
        "जल निकासी: भारी और जलभराव वाली चिकनी मिट्टी जड़ों के श्वसन को रोकती है और जड़ सड़न (root rot) व अंकुरण गलन (damping-off) को बढ़ावा देती है।"
    ),
    # Sunlight & temperature
    (
        r"require full sunlight.*minimum 6 to 8 hours",
        "धूप की आवश्यकता: टमाटर के पौधों को सर्वोत्तम प्रकाश संश्लेषण, फूल आने और फल लगने के लिए प्रतिदिन कम से कम 6 से 8 घंटे की सीधी धूप मिलनी चाहिए।"
    ),
    (
        r"ideal growing temperatures range from 70°F to 85°F.*21°C to 29°C",
        "तापमान: दिन का तापमान 21°C से 29°C (70°F-85°F) और रात का तापमान 15°C से 21°C (60°F-70°F) टमाटर के स्वस्थ विकास के लिए आदर्श है।"
    ),
    # Irrigation
    (
        r"always apply water directly to the soil root zone using drip or trickle irrigation",
        "सिंचाई प्रबंधन: पत्तियों को सूखा रखने के लिए प्लास्टिक मल्च के नीचे ड्रिप या टपक सिंचाई (drip irrigation) का प्रयोग करें और पानी हमेशा सीधे पौधे के जड़ क्षेत्र में दें।"
    ),
    (
        r"avoid overhead sprinkler irrigation.*splashes soilborne spores",
        "सिंचाई सावधानी: ऊपरी फव्वारा सिंचाई (overhead sprinkler) से बचें, जो मिट्टी में मौजूद रोग बीजाणुओं को उछालती है और पत्तियों को गीला रखकर फफूंद संक्रमण को बढ़ाती है।"
    ),
    (
        r"never work in tomato fields when foliage is wet",
        "खेत में कार्य: जब पत्तियां ओस या बारिश से गीली हों, तब टमाटर के खेत में काम न करें, क्योंकि जीवाणु और कवक हाथों व औजारों से आसानी से फैलते हैं।"
    ),
    # Spacing, trellising, pruning, mulching
    (
        r"space indeterminate tomato plants 24 to 36 inches apart",
        "पौधों का फासला: हवा के बेहतर संचार और पत्तियों को जल्दी सुखाने के लिए अनिश्चित (indeterminate) पौधों को कतार में 24 से 36 इंच और कतारों के बीच 4 से 5 फीट की दूरी पर लगाएं।"
    ),
    (
        r"support all tomato plants using wooden or metal stakes.*trellises",
        "सहारा देना: पत्तियों और फलों को जमीन की सतह से ऊपर रखने के लिए लकड़ी या धातु के खूंटों, मचान (trellis) या तारों के पिंजरों से सहारा (staking) दें।"
    ),
    (
        r"prune off the lowest 12 to 18 inches of leaves",
        "छंटाई (Pruning): पौधा स्थापित होने के बाद नीचे की 12 से 18 इंच की पत्तियों की छंटाई करें ताकि मिट्टी के संपर्क में आने वाली या पानी के छींटों वाली पत्तियां हट जाएं।"
    ),
    (
        r"apply a 2 to 3-inch layer of clean organic mulch",
        "मल्चिंग: मिट्टी के पानी के छींटों को निचली पत्तियों पर उछलने से रोकने के लिए पौधों के आधार पर 2 से 3 इंच साफ पुआल या मल्च की परत बिछाएं।"
    ),
    # Crop rotation & sanitation
    (
        r"implement a strict 3 to 4-year crop rotation",
        "फसल चक्र: मिट्टी में रोगजनकों के जीवन चक्र को तोड़ने के लिए सोलेनेसी कुल की फसलों (टमाटर, मिर्च, आलू, बैंगन) से 3 से 4 वर्ष का सख्त फसल चक्र (crop rotation) अपनाएं।"
    ),
    (
        r"sanitize wooden stakes and harvest bins.*10% bleach",
        "स्वच्छता: लकड़ी के खूंटों, टोकरियों और कृषि उपकरणों को पुनः उपयोग से पहले 10% ब्लीच घोल या कीटाणुनाशक से अच्छी तरह सैनिटाइज करें।"
    ),
    (
        r"certified disease-free seed.*hot water.*122°F.*50°C",
        "बीज उपचार: केवल प्रमाणित रोग-मुक्त बीज का उपयोग करें; बीजों को ठीक 25 मिनट के लिए 50°C (122°F) गर्म पानी में उपचारित करें ताकि आंतरिक जीवाणु नष्ट हो सकें।"
    ),
    (
        r"reject any flat showing suspicious water-soaked lesions",
        "पौध निरीक्षण: जल-सिक्त धब्बे या तने के सड़न वाले किसी भी संदिग्ध पौधे को रोपाई के लिए अस्वीकार करें।"
    ),
    # Early Blight (Alternaria solani)
    (
        r"foliar symptoms begin as small, brownish-black spots.*concentric rings.*target board",
        "अगेती झुलसा लक्षण: निचली पुरानी पत्तियों पर छोटे भूरे-काले धब्बे बनते हैं, जो संकेंद्रित छल्लों (target board bullseye pattern) के साथ फैलते हैं और चारों ओर पीला घेरा बनाते हैं।"
    ),
    (
        r"alternaria solani causes dark brown.*lesions.*concentric rings",
        "अगेती झुलसा (*Alternaria solani*): पत्तियों पर संकेंद्रित छल्लेदार धब्बे (concentric rings) और तने पर भूरे कैंकर बनाता है, जिससे पत्तियां पीली होकर सूख जाती हैं।"
    ),
    (
        r"apply protective fungicides such as chlorothalonil or mancozeb at 7- to 10-day intervals",
        "कवकनाशी प्रबंधन: रोग के पहले लक्षण दिखते ही सुरक्षात्मक कवकनाशी जैसे क्लोरोथैलोनिल (Chlorothalonil) या मैंकोजेब (Mancozeb) का 7 से 10 दिनों के अंतराल पर छिड़काव करें।"
    ),
    (
        r"alternate with.*quadris.*strobilurin",
        "प्रतिरोध रोकथाम: कवकनाशी प्रतिरोध से बचने के लिए क्लोरोथैलोनिल के साथ स्ट्रोबिल्यूरिन (Quadris / azoxystrobin) या अन्य अनुमोदित कवकनाशियों का क्रम बदलकर छिड़काव करें।"
    ),
    # Late Blight (Phytophthora infestans)
    (
        r"foliar lesions appear as irregular, water-soaked.*white fungal sporulation",
        "पछेती झुलसा लक्षण: पत्तियों पर अनियमित जल-सिक्त जैतून-हरे से भूरे-बैंगनी धब्बे बनते हैं, और नम वातावरण में पत्ती की निचली सतह पर सफेद कवक (white sporulation) दिखाई देती है।"
    ),
    (
        r"plant resistant cultivars.*ph-2 and ph-3.*mountain magic.*mountain merit.*iron lady",
        "प्रतिरोधी किस्में: पछेती झुलसा से बचाव के लिए Ph-2 और Ph-3 प्रतिरोधी जीन युक्त किस्में जैसे Mountain Magic, Mountain Merit, Iron Lady या Defiant Ph-R लगाएं।"
    ),
    (
        r"apply fungicides with systemic.*curzate.*cymoxanil.*revus.*mandipropamid",
        "रासायनिक नियंत्रण: पछेती झुलसा की सूचना मिलते ही सिस्टमिक कवकनाशी जैसे साइमोक्सानिल (Curzate / cymoxanil) या मैंडीप्रोपामाइड (Revus) का सुरक्षात्मक छिड़काव करें।"
    ),
    (
        r"phytophthora infestans.*can destroy an entire tomato field within days",
        "पछेती झुलसा चेतावनी: *Phytophthora infestans* अत्यधिक विनाशकारी रोगज़नक़ है जो अनुकूल नम व ठंडे मौसम में कुछ ही दिनों में पूरे खेत को नष्ट कर सकता है।"
    ),
    # Bacterial Spot (Xanthomonas)
    (
        r"bacterial spot.*small, water-soaked.*circular to irregular lesions.*black blisters",
        "जीवाणु धब्बा लक्षण: पत्तियों पर छोटे (3 मिमी से कम), जल-सिक्त तैलीय (greasy) काले धब्बे बनते हैं; हरे फलों पर उभरे हुए खुरदुरे छाले (scabby spots) हो जाते हैं।"
    ),
    (
        r"apply fixed copper bactericides combined with mancozeb",
        "जीवाणुनाशी छिड़काव: कॉपर-प्रतिरोधी जीवाणुओं के प्रभावी नियंत्रण के लिए कॉपर (Fixed Copper) के साथ मैंकोजेब (Mancozeb) मिलाकर छिड़काव करें।"
    ),
    (
        r"actigard.*acibenzolar-s-methyl.*systemic acquired resistance",
        "प्रतिरोध संवर्धन: पौधे की प्राकृतिक रोग प्रतिरोधक क्षमता बढ़ाने के लिए एक्टिगार्ड (Actigard / acibenzolar-S-methyl) का प्रयोग करें।"
    ),
    # Nutrition & fertilizer
    (
        r"excess nitrogen promotes lush, dense vegetative growth.*disease",
        "संतुलित उर्वरक: अत्यधिक नाइट्रोजन के प्रयोग से बचें, क्योंकि यह पत्तियों को बहुत घना बनाकर हवा का संचार रोकता है और फफूंद रोगों के प्रति संवेदनशीलता बढ़ाता है।"
    ),
    (
        r"apply a balanced fertilizer.*10-10-10 or 5-10-10.*soil test",
        "उर्वरक प्रबंधन: मृदा परीक्षण के आधार पर संतुलित उर्वरक (10-10-10 या 5-10-10) का उपयोग करें और फल लगने के दौरान पर्याप्त पोटाश व कैल्शियम सुनिश्चित करें।"
    )
]


def translate_agronomic_sentence_to_hindi(sentence: str) -> str:
    """
    Translates common extension recommendations into clear, fluent agricultural Hindi
    while preserving Latin pathogen names, active ingredients, and measurements.
    """
    clean_s = sentence.strip()

    # 1. First test semantic pattern matching for high-fidelity translation
    for pat, hi_translation in AGRONOMIC_SENTENCE_PATTERNS_HI:
        if re.search(pat, clean_s, re.IGNORECASE):
            return hi_translation

    # 2. Terminology and clause replacement pipeline
    s = clean_s
    subs = [
        # Cultural practices
        (r"Avoid overhead irrigation", "ऊपरी छिड़काव (overhead sprinkler irrigation) से बचें"),
        (r"Use drip or trickle irrigation", "ड्रिप या टपक सिंचाई (drip irrigation) का प्रयोग करें"),
        (r"beneath plastic mulch to keep foliage dry", "पत्तियों को सूखा रखने के लिए प्लास्टिक मल्च के नीचे ड्रिप का उपयोग करें"),
        (r"Never work in tomato fields when foliage is wet", "जब पत्तियां ओस या बारिश से गीली हों, तब टमाटर के खेत में काम न करें"),
        (r"Sanitize wooden stakes and harvest bins", "लकड़ी के खूंटों और टोकरियों को 10% ब्लीच या सैनिटाइज़र से कीटाणुरहित करें"),
        (r"Apply a balanced fertilizer", "मृदा परीक्षण के अनुसार संतुलित उर्वरक (10-10-10 या 5-10-10) का प्रयोग करें"),
        (r"Space indeterminate tomato plants 24 to 36 inches apart", "अनिश्चित (indeterminate) टमाटर के पौधों को कतार में 24 से 36 इंच की दूरी पर लगाएं"),
        (r"Support all tomato plants using wooden or metal stakes", "पौधों को जमीन से ऊपर रखने के लिए लकड़ी या धातु के खूंटों या पिंजरों से सहारा (staking) दें"),
        (r"Implement a strict 3 to 4-year crop rotation", "टमाटर वाले खेत में 3 से 4 वर्ष का सख्त फसल चक्र (crop rotation) अपनाएं"),
        (r"Prune off the lowest 12 to 18 inches of leaves", "पौधा स्थापित होने के बाद नीचे की 12 से 18 इंच की पत्तियों की छंटाई (pruning) करें"),
        (r"Always apply water directly to the soil root zone", "पानी हमेशा सीधे पौधे के जड़ क्षेत्र में दें, पत्तियों पर पानी न डालें"),
        (r"Apply a 2 to 3-inch layer of clean organic mulch", "पौधों के आधार पर 2 से 3 इंच साफ पुआल या मल्च की परत बिछाएं ताकि मिट्टी का पानी पत्तियों पर न उछले"),
        (r"Reject any flat showing suspicious water-soaked lesions", "जल-सिक्त धब्बे या तने के सड़न वाले किसी भी पौधे को लगाने से मना करें"),
        (r"Certified disease-free seed", "प्रमाणित रोग-मुक्त बीज (certified pathogen-free seed)"),
        (r"Soil Quality and Drainage", "मृदा गुणवत्ता और जल निकासी"),
        (r"Full sunlight", "पूर्ण सूर्य का प्रकाश (कम से कम 6-8 घंटे)"),
        (r"Hot water seed treatment", "गर्म पानी बीज उपचार (50°C पर 25 मिनट)"),
        # Chemicals & Pathogens
        (r"Copper", "कॉपर (Copper)"),
        (r"Mancozeb", "मैंकोजेब (Mancozeb)"),
        (r"Chlorothalonil", "क्लोरोथैलोनिल (Chlorothalonil)"),
        (r"Actigard", "एक्टिगार्ड (Actigard / acibenzolar-S-methyl)"),
        (r"Curzate", "क्युर्ज़ेट (Curzate / cymoxanil)"),
        (r"Revus", "रेवस (Revus / mandipropamid)"),
        (r"Quadris", "क्वाड्रिस (Quadris / azoxystrobin)"),
        (r"Phytophthora infestans", "*Phytophthora infestans* (पछेती झुलसा रोगज़नक़)"),
        (r"Alternaria solani", "*Alternaria solani* (अगेती झुलसा रोगज़नक़)"),
        (r"Xanthomonas", "*Xanthomonas* (जीवाणु धब्बा रोगज़नक़)"),
        # General connector replacements
        (r"are favored by", "के अनुकूल होते हैं"),
        (r"is favored by", "के अनुकूल होता है"),
        (r"leads to", "का कारण बनता है"),
        (r"recommended for", "के लिए अनुशंसित है"),
        (r"to prevent", "रोकथाम के लिए")
    ]
    for en_pat, hi_rep in subs:
        s = re.sub(en_pat, hi_rep, s, flags=re.IGNORECASE)

    # If the sentence is still predominantly English, wrap with clear Hindi agronomic framing
    has_devanagari = bool(re.search(r"[\u0900-\u097F]", s))
    if not has_devanagari:
        # Fallback translation framing for unmapped sentences
        s = f"सत्यापित विस्तार अनुशंसा: {s} (अनुशंसा का पालन करें और पत्तियों को सूखा रखें)"

    return s


# Semantic agronomic patterns mapped to authentic Dogri vernacular in Devanagari script
AGRONOMIC_SENTENCE_PATTERNS_DOI: List[Tuple[str, str]] = [
    (
        r"thrive in well-drained.*loamy soil.*organic matter.*compost",
        "मिट्टी ते खाद: टमाटरै लेई चंगी जल निकासी आह्ली, भुरभुरी दोमट मिट्टी सबने शा उत्तमी ऐ, जिस च 2-3 इंच सड़ी-बुज्जी देसी रूड़ी या कम्पोस्ट खाद पाई दी होवे।"
    ),
    (
        r"heavy, waterlogged clay soils restrict root respiration.*root rots",
        "जल निकासी: भारी ते चिक्कड़ आह्ली मिट्टी च जड़ें गी हवा नेईं लगदी, जिस कन्ने जड़ सड़न ते पनीरी गलन दा खतरा बधी जंदा ऐ।"
    ),
    (
        r"require full sunlight.*minimum 6 to 8 hours",
        "धुप्प दी लोड़: टमाटर दे बूटें गी चंगे फुल्ल ते फल लग्गने लेई हर रोज कट-शा-कट 6 शा 8 केंटे सिद्दी धुप्प मिलनी चाहिदी ऐ।"
    ),
    (
        r"ideal growing temperatures range from 70°F to 85°F.*21°C to 29°C",
        "तापमान: दिनै बेले 21°C शा 29°C ते रातै गी 15°C शा 21°C तापमान टमाटर दी फसल लेई सबने शा खरा ऐ।"
    ),
    (
        r"always apply water directly to the soil root zone using drip or trickle irrigation",
        "सिंचाई: पत्तें गी सुक्का रक्खने लेई मल्च थल्ले ड्रिप (टपक) सिंचाई दा इस्तेमाल करो ते पानी सिद्धा बूटे दी जड़ें च पाओ।"
    ),
    (
        r"avoid overhead sprinkler irrigation.*splashes soilborne spores",
        "सिंचाई सावधानी: उप्परै शा फुहारे कन्ने पानी नेईं पाओ, कीजे इंदे कन्ने मिट्टी दे कीटाणु उछली के पत्तें पर पौंदे न ते रोग बधदा ऐ।"
    ),
    (
        r"never work in tomato fields when foliage is wet",
        "खेत च कम्म: ज्लू पत्तें पर ओस या बरखा दा पानी होवे, त्लू खेत च कम्म मत करो, कीजे हत्थें ते औजारें कन्ने बीमारी मती तेजी कन्ने फैलदी ऐ।"
    ),
    (
        r"space indeterminate tomato plants 24 to 36 inches apart",
        "बूटें दी दूरी: हवा दे चंगे संचार लेई बूटें च 24 शा 36 इंच दा फासला रक्खो ते कतारें दे बिचकार 4 शा 5 फुट दी जगह छड्डो।"
    ),
    (
        r"support all tomato plants using wooden or metal stakes.*trellises",
        "सहारा देना: बूटें गी जमीन शा उप्पर रक्खने लेई लकड़ी दे डंडें, खूंटें या तारें दा सहारा (staking) जरूर देओ।"
    ),
    (
        r"prune off the lowest 12 to 18 inches of leaves",
        "छंटाई: बूटा बड्डा होने पर निचले 12 शा 18 इंच पत्तें गी छंग देओ तां जे जमीन दी नमी ते मिट्टी दे छींटे पत्तें गी ना लग्गन।"
    ),
    (
        r"apply a 2 to 3-inch layer of clean organic mulch",
        "मल्चिंग: बूटें दे मुढ्ढे पर 2-3 इंच सुक्की पुआल या मल्च बिछाओ तां जे पानी दे छींटे पत्तें पर ना उछलन।"
    ),
    (
        r"implement a strict 3 to 4-year crop rotation",
        "फसल चक्र: मिट्टी दे कीटाणुएं गी खत्म करने लेई टमाटर, मिर्च, आलू ते बैंगन दी फसलै च 3 शा 4 साल दा फसल चक्र अपनाओ।"
    ),
    (
        r"foliar symptoms begin as small, brownish-black spots.*concentric rings.*target board",
        "अगेती झुलसा लक्षण: निचले पुसले पत्तें पर निक्के भूरे-काह्ले दाग पौंदे न, जेह्ड़े गोल छल्ले (concentric rings) बनांदे न ते पत्ता पीला होई जंदा ऐ।"
    ),
    (
        r"apply protective fungicides such as chlorothalonil or mancozeb at 7- to 10-day intervals",
        "कवकनाशी स्प्रे: बीमारी दे शुरूआती लक्षण दिक्खदे गै क्लोरोथैलोनिल या मैंकोजेब (Mancozeb) दा 7 शा 10 दिनें दे अंतर पर छिड़काव करो।"
    ),
    (
        r"foliar lesions appear as irregular, water-soaked.*white fungal sporulation",
        "पछेती झुलसा लक्षण: पत्तें पर अणियमित तेलिये ते भूरे दाग पैंदे न, ते नमी च पत्तें दे थल्ले चिट्टी फफूंद (white sporulation) दिक्खदी ऐ। ए Phytophthora infestans रोग मते तेजी कन्ने खेत गी खराब करदा ऐ।"
    ),
    (
        r"apply fungicides with systemic.*curzate.*cymoxanil.*revus.*mandipropamid",
        "पछेती झुलसा रोकथाम: रोग दिक्खदे गै सिस्टमिक कवकनाशी जिन्ने साइमोक्सानिल (Curzate / cymoxanil) या मैंडीप्रोपामाइड (Revus) दा तुरंत स्प्रे करो।"
    ),
    (
        r"bacterial spot.*small, water-soaked.*circular to irregular lesions.*black blisters",
        "जीवाणु धब्बा लक्षण: पत्तें पर निक्के-निक्के तेलिये काह्ले दाग पौंदे न। फलें पर उभरे दे दाने बणदे न।"
    ),
    (
        r"apply fixed copper bactericides combined with mancozeb",
        "जीवाणुनाशी छिड़काव: जीवाणु धब्बे गी रोकने लेई कॉपर (Fixed Copper) कन्ने मैंकोजेब रलाई के छिड़काव करो।"
    )
]


def translate_agronomic_sentence_to_dogri(sentence: str) -> str:
    """
    Translates common extension recommendations into authentic Dogri in Devanagari script.
    """
    clean_s = sentence.strip()

    for pat, doi_translation in AGRONOMIC_SENTENCE_PATTERNS_DOI:
        if re.search(pat, clean_s, re.IGNORECASE):
            return doi_translation

    # Fallback terminology mapping
    s = clean_s
    doi_subs = [
        (r"Avoid overhead irrigation", "उप्परै शा फुहारे कन्ने पानी नेईं पाओ"),
        (r"Use drip or trickle irrigation", "ड्रिप (टपक) सिंचाई दा इस्तेमाल करो"),
        (r"Never work in tomato fields when foliage is wet", "पत्ते गिले होने पर खेत च कम्म मत करो"),
        (r"Sanitize wooden stakes and harvest bins", "खूंटें ते टोकरियें गी 10% ब्लीच कन्ने साफ करो"),
        (r"Apply a balanced fertilizer", "संतुलित खाद (10-10-10) दा इस्तेमाल करो"),
        (r"Copper", "कॉपर (Copper)"),
        (r"Mancozeb", "मैंकोजेब (Mancozeb)"),
        (r"Chlorothalonil", "क्लोरोथैलोनिल (Chlorothalonil)"),
        (r"Curzate", "क्युर्ज़ेट (Curzate / cymoxanil)"),
        (r"Revus", "रेवस (Revus / mandipropamid)")
    ]
    for en_pat, doi_rep in doi_subs:
        s = re.sub(en_pat, doi_rep, s, flags=re.IGNORECASE)

    has_devanagari = bool(re.search(r"[\u0900-\u097F]", s))
    if not has_devanagari:
        s = f"विश्वविद्यालय विस्तार सलाह: {s} (पत्तें गी सुक्का रक्खो ते ध्यान कन्ने दवाई पाओ)"

    return s


class AgrimindAnswerGenerator:
    """
    RAG Answer Generator combining retrieval gating, structured provenance,
    multi-turn referent resolution, Hindi & English synthesis, and dual generation modes
    (Gemini LLM with fallback to Extractive Evidence Synthesis).
    """

    def __init__(
        self,
        retriever: Optional[AgrimindRetriever] = None,
        model_name: Optional[str] = None,
        llm: Optional[Any] = None,
        temperature: float = 0.1,
        api_key: Optional[str] = None
    ):
        self.retriever = retriever or AgrimindRetriever()
        self.model_name = get_gemini_model_name(model_name)
        self.temperature = temperature
        self._llm = llm
        self._api_key = get_gemini_api_key(api_key)

    def _get_api_key(self) -> Optional[str]:
        if self._api_key:
            return self._api_key
        return get_gemini_api_key()

    def _init_gemini_llm(self) -> Optional[Any]:
        if self._llm is not None:
            return self._llm
        api_key = self._get_api_key()
        if not api_key:
            logger.info("No Gemini API key available. Operating in local extractive synthesis mode.")
            return None
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=self.temperature,
                google_api_key=api_key
            )
            self._llm = llm
            return self._llm
        except Exception as e:
            logger.warning(f"Could not initialize ChatGoogleGenerativeAI: {e}")
            return None

    def synthesize_extractive_answer(
        self,
        query: str,
        retrieval: Dict[str, Any],
        language: str = "en",
        disease_target: Optional[str] = None
    ) -> str:
        """
        Deterministic, local grounded evidence synthesis in English or Hindi.
        Constructs an extension-grade answer directly from retrieved chunks and metadata
        without requiring an external LLM API key. Distinguishes case-specific disease
        predictions from general agronomic guidance while reminding that AI diagnosis is preliminary.
        """
        results = retrieval.get("results", [])
        citations = retrieval.get("citations", [])
        is_hindi = (language == "hi")
        is_dogri = (language == "doi")

        if not results:
            if is_dogri:
                return "माफ़ करियो, विश्वविद्यालय कृषि विस्तार प्रकाशनें च तुहंदे प्रश्न लेई काफी सबूत नेईं लब्भे। कृपया स्थानीय कृषि विज्ञान केंद्र कन्ने संपर्क करो।"
            return INSUFFICIENT_EVIDENCE_FALLBACK_DOI if is_dogri else (INSUFFICIENT_EVIDENCE_FALLBACK_HI if is_hindi else INSUFFICIENT_EVIDENCE_FALLBACK)

        answer_lines = []
        if disease_target:
            clean_target = disease_target.replace("Tomato___", "").replace("_", " ")
            if is_dogri:
                doi_target = "अगेती झुलसा (Early Blight)" if "Early" in disease_target else (
                    "पछेती झुलसा (Late Blight)" if "Late" in disease_target else (
                        "जीवाणु धब्बा (Bacterial Spot)" if "Bacterial" in disease_target else clean_target
                    )
                )
                answer_lines.append(f"डोगरी (Dogri) भाषा च सलाह — निदान कीती गेदी स्थिति (**{doi_target}**) दे संबंध च — विश्वविद्यालय कृषि विस्तार प्रकाशनें शा संकलित कीती गेदी जानकारी (आरंभिक एआई मूल्यांकन; दवाई छिड़कने शा पैह्ले स्थानीय कृषि अधिकारी कन्ने सलाह जरूर लैओ):\n")
            elif is_hindi:
                hi_target = "अगेती झुलसा (Early Blight)" if "Early" in disease_target else (
                    "पछेती झुलसा (Late Blight)" if "Late" in disease_target else (
                        "जीवाणु धब्बा (Bacterial Spot)" if "Bacterial" in disease_target else clean_target
                    )
                )
                answer_lines.append(f"निदान की गई स्थिति (**{hi_target}**) के संबंध में — सत्यापित विश्वविद्यालय कृषि विस्तार प्रकाशनों से संकलित अनुशंसाएं (प्रारंभिक एआई मूल्यांकन; किसी भी रासायनिक उपचार से पूर्व स्थानीय विस्तार विशेषज्ञ से पुष्टि करें):\n")
            else:
                answer_lines.append(f"Regarding the preliminary diagnosis of **{clean_target}** — synthesized from verified university agricultural extension publications (AI decision support; confirm with an agricultural specialist before application):\n")
        else:
            if is_dogri:
                answer_lines.append("डोगरी (Dogri) भाषा च सलाह — विश्वविद्यालय कृषि विस्तार प्रकाशनें दे आधार पर तुहंदे प्रश्न लेई अनुशंसित सुझाव निम्नलिखित न:\n")
            elif is_hindi:
                answer_lines.append("सत्यापित विश्वविद्यालय कृषि विस्तार प्रकाशनों के आधार पर, आपके प्रश्न के लिए अनुशंसित सुझाव निम्नलिखित हैं:\n")
            else:
                answer_lines.append("Based on verified university agricultural extension publications, here are general agronomic recommendations for your query:\n")

        used_citations = set()
        for idx, (item, cit) in enumerate(zip(results, citations), start=1):
            text = item.get("text", "")
            meta = item.get("metadata", {})
            title = meta.get("title", cit.get("title", "Extension Publication"))
            inst = meta.get("institution", cit.get("institution", "Agricultural Extension"))

            points = extract_key_agronomic_points(text, max_points=2)
            if points:
                if is_dogri:
                    title_hi = translate_doc_title_to_hindi(title)
                    inst_hi = translate_institution_to_hindi(inst)
                    answer_lines.append(f"**स्रोत: {title_hi} ({inst_hi}) [{idx}]:**")
                    for pt in points:
                        doi_pt = translate_agronomic_sentence_to_dogri(pt)
                        answer_lines.append(f"- {doi_pt} [{idx}]")
                elif is_hindi:
                    title_hi = translate_doc_title_to_hindi(title)
                    inst_hi = translate_institution_to_hindi(inst)
                    answer_lines.append(f"**स्रोत: {title_hi} ({inst_hi}) [{idx}]:**")
                    for pt in points:
                        hi_pt = translate_agronomic_sentence_to_hindi(pt)
                        answer_lines.append(f"- {hi_pt} [{idx}]")
                else:
                    answer_lines.append(f"**From {title} ({inst}) [{idx}]:**")
                    for pt in points:
                        answer_lines.append(f"- {pt} [{idx}]")
                answer_lines.append("")
                used_citations.add(idx)

        if not answer_lines or len(used_citations) == 0:
            return INSUFFICIENT_EVIDENCE_FALLBACK_DOI if is_dogri else (INSUFFICIENT_EVIDENCE_FALLBACK_HI if is_hindi else INSUFFICIENT_EVIDENCE_FALLBACK)

        # Append structured citation summary block
        if is_dogri or is_hindi:
            answer_lines.append("### संदर्भित विस्तार स्रोत (Cited Extension Sources):")
            for cit in citations:
                num = cit.get("citation_number", "")
                c_title = cit.get("title", "")
                c_inst = cit.get("institution", "")
                c_url = cit.get("source_url", "")
                c_year = cit.get("publication_year", "")
                year_str = f" ({c_year})" if c_year else ""
                answer_lines.append(f"[{num}] {c_title} — *{c_inst}*{year_str}. स्रोत लिंक: {c_url}")
        else:
            answer_lines.append("### Cited Extension Sources:")
            for cit in citations:
                num = cit.get("citation_number", "")
                c_title = cit.get("title", "")
                c_inst = cit.get("institution", "")
                c_url = cit.get("source_url", "")
                c_year = cit.get("publication_year", "")
                year_str = f" ({c_year})" if c_year else ""
                answer_lines.append(f"[{num}] {c_title} — *{c_inst}*{year_str}. Available at: {c_url}")

        return "\n".join(answer_lines)

    def generate_answer(
        self,
        query: str,
        conversation_history: Optional[List[Any]] = None,
        disease_target: Optional[str] = None,
        language: str = "en",
        case_context: Optional[str] = None,
        top_k: int = 4
    ) -> Dict[str, Any]:
        """
        End-to-end RAG answer generation workflow:
        1. Validate query and handle Dogri language notice.
        2. Resolve multi-turn references and check for ambiguity.
        3. Normalize query for retrieval (Hindi to English keywords).
        4. Query retrieval with metadata filtering and sufficiency check.
        5. If evidence is insufficient, immediately returns extension fallback.
        6. If Gemini is available, generates grounded answer via LLM in requested language.
        7. If Gemini is unavailable or errors, falls back to local extractive synthesis.
        """
        # Validate query
        if not query or not query.strip():
            return {
                "query": query,
                "disease_target": disease_target,
                "language": language,
                "answer": "Invalid query: question text cannot be empty.",
                "has_sufficient_evidence": False,
                "citations": [],
                "retrieved_count": 0,
                "generation_mode": "validation_error",
                "model": None,
                "error": "Query string is empty"
            }

        clean_query = query.strip()
        lang = language.strip().lower() if language else "en"

        # Automatic language detection (Devanagari, Romanized Hinglish, and Dogri dialect)
        from src.rag.language_detector import detect_language
        det_lang, conf, method = detect_language(clean_query)
        if (lang in ("en", "", None) and det_lang in ("hi", "doi")) or (bool(re.search(r"[\u0900-\u097F]", clean_query)) and lang not in ("hi", "doi")):
            lang = det_lang

        # Handle Dogri synthesis
        is_dogri_mode = (lang == "doi")
        # Step 2: Multi-turn Referent Resolution
        resolved_query, resolved_target, is_ambiguous = resolve_query_referent(
            query=clean_query,
            conversation_history=conversation_history,
            disease_target=disease_target
        )

        if is_ambiguous:
            ambig_msg = AMBIGUOUS_REFERENT_MESSAGE_HI if lang == "hi" else AMBIGUOUS_REFERENT_MESSAGE_EN
            return {
                "query": clean_query,
                "disease_target": None,
                "language": lang,
                "answer": ambig_msg,
                "has_sufficient_evidence": False,
                "citations": [],
                "retrieved_count": 0,
                "generation_mode": "clarification_needed",
                "model": None,
                "error": None
            }

        active_target = resolved_target or disease_target

        # Step 3: Query Normalization for ChromaDB Retrieval
        search_query = normalize_agronomic_query(resolved_query)

        # Step 4: Retrieve context
        retrieval = self.retriever.retrieve(
            query=search_query,
            disease_target=active_target,
            top_k=top_k
        )

        # Step 5: Gating on insufficient evidence
        if not retrieval.get("has_sufficient_evidence", False):
            # Check if this query is a regional multi-crop advisory query (Wheat, Rice, Potato, Mustard, Chili)
            multi_crop_response = check_multi_crop_guidance(clean_query, lang)
            if multi_crop_response is not None:
                return multi_crop_response

            if is_dogri_mode:
                fallback_text = INSUFFICIENT_EVIDENCE_FALLBACK_DOI
            elif lang == "hi":
                fallback_text = INSUFFICIENT_EVIDENCE_FALLBACK_HI
            else:
                fallback_text = INSUFFICIENT_EVIDENCE_FALLBACK
            return {
                "query": clean_query,
                "disease_target": active_target,
                "language": lang,
                "answer": fallback_text,
                "has_sufficient_evidence": False,
                "citations": [],
                "retrieved_count": retrieval.get("retrieved_count", 0),
                "generation_mode": "insufficient_evidence_fallback",
                "model": None,
                "error": None
            }

        context_text = retrieval.get("context_text", "")
        if case_context:
            context_text = f"Case Diagnostic Findings & Prescribed Treatments: {case_context}\n\n" + context_text
        citations = retrieval.get("citations", [])

        # Step 6: Attempt Gemini LLM generation if available (skip for Dogri local synthesis)
        llm = self._init_gemini_llm() if lang != "doi" else None
        if llm is not None:
            try:
                from langchain_core.messages import SystemMessage, HumanMessage

                if lang == "hi":
                    sys_prompt = AGRIMIND_SYSTEM_PROMPT_HINDI
                    user_prompt = f"""सत्यापित कृषि विस्तार साहित्य से प्राप्त संदर्भ:
----------------------------------------
{context_text}
----------------------------------------

किसान / शोधकर्ता का प्रश्न: {clean_query}

कृपया ऊपर दिए गए संदर्भ के आधार पर स्पष्ट और सटीक हिंदी में उत्तर दें। वैज्ञानिक लैटिन नामों को कोष्ठक में रखें और स्रोतों को [1], [2] आदि से उद्धृत करें।"""
                else:
                    sys_prompt = AGRIMIND_SYSTEM_PROMPT
                    user_prompt = f"""Context from verified agricultural extension literature:
----------------------------------------
{context_text}
----------------------------------------

Farmer/Researcher Question: {clean_query}

Answer the question strictly based on the context above, citing sources with bracketed numbers [1], [2], etc."""

                messages = [
                    SystemMessage(content=sys_prompt),
                    HumanMessage(content=user_prompt)
                ]

                response = llm.invoke(messages)
                if hasattr(response, "content"):
                    if isinstance(response.content, list):
                        answer_content = "".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in response.content
                        )
                    else:
                        answer_content = str(response.content)
                else:
                    answer_content = str(response)

                return {
                    "query": clean_query,
                    "disease_target": active_target,
                    "language": lang,
                    "answer": answer_content,
                    "has_sufficient_evidence": True,
                    "citations": citations,
                    "retrieved_count": len(retrieval.get("results", [])),
                    "generation_mode": "gemini_llm",
                    "model": getattr(self, "model_name", "gemini"),
                    "error": None
                }
            except Exception as e:
                err_msg = sanitize_text(str(e), self._get_api_key())
                logger.warning(f"Gemini LLM invocation failed ({err_msg}). Falling back to grounded extractive synthesis.")
                fallback_answer = self.synthesize_extractive_answer(clean_query, retrieval, language=lang, disease_target=active_target)
                return {
                    "query": clean_query,
                    "disease_target": active_target,
                    "language": lang,
                    "answer": fallback_answer,
                    "has_sufficient_evidence": True,
                    "citations": citations,
                    "retrieved_count": len(retrieval.get("results", [])),
                    "generation_mode": "grounded_extractive_fallback",
                    "model": "grounded_extractive",
                    "error": err_msg
                }

        # Step 7: Local Grounded Extractive Synthesis (Default when no API key)
        extractive_answer = self.synthesize_extractive_answer(clean_query, retrieval, language=lang, disease_target=active_target)
        mode = "dogri_synthesis" if lang == "doi" else "grounded_extractive"
        return {
            "query": clean_query,
            "disease_target": active_target,
            "language": lang,
            "answer": extractive_answer,
            "has_sufficient_evidence": True,
            "citations": citations,
            "retrieved_count": len(retrieval.get("results", [])),
            "generation_mode": mode,
            "model": "grounded_extractive",
            "error": None
        }
