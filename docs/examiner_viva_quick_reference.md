# AgriMind — Project Viva Defense Quick-Reference & Demonstration Script

**Course Code:** COM71116-21 (7th-Semester CSE Minor Project)  
**Project:** AgriMind — Multi-Agent AI System for Crop Disease Investigation, Risk Assessment & Adaptive Decision Support  
**Team:** Jaskirat Kour (Lead), Palakjot Kour, Sayam Malhotra, Ikjot Singh  

---

## 1. 2-Minute Elevator Pitch for Examiners

> *"Respected examiners, existing agricultural mobile apps are monolithic: they feed a leaf photo into a CNN and output a disease label with no consideration of weather, canopy spread, or actionable safety precautions. AgriMind solves this by pairing a calibrated 3-class ResNet-50 vision classifier with a multi-agent reasoning core orchestrated by LangGraph.
> 
> Our system doesn't just name the disease; our Risk Assessment Agent dynamically escalates epidemic risk when cool, wet weather threatens explosive Late Blight outbreaks. Our Decision Planning Agent enforces a 4-tier Integrated Pest Management hierarchy grounded in 63 university extension fact sheets via ChromaDB RAG. All of this is integrated into a 100% native Jetpack Compose Android app with offline SQLite caching, bilingual English and Hindi voice interaction, and native on-device A4 PDF report generation. Across 94 automated tests, our system achieved a 100% pass rate."*

---

## 2. Step-by-Step Live Viva Demonstration Script

| Step | Action on Android App (`emulator-5554` or Phone) | What the Examiner Observes | Key Talking Point to Mention |
|:---:|:---|:---|:---|
| **1** | Open **System Health** Tab (Tab 3) | Green banner: `Backend Online & Healthy (v1.0.0)`, ResNet-50 loaded, **63 RAG chunks indexed** | *"Our backend provides live telemetry verifying model status, ChromaDB vector store health, and device compute hardware."* |
| **2** | Go to **Diagnosis** Tab (Tab 0) | Notice the yellow disclaimer at top: `AI-supported preliminary assessment...` | *"We prioritize agricultural safety: preliminary AI disclaimers are enforced before the user even takes a picture."* |
| **3** | Select sample Late Blight leaf and submit | Progress indicators animate $\rightarrow$ Diagnostic Card displays `Late blight (100.0%)`, `Severity: MODERATE` under hot/dry weather | *"The vision classifier outputs calibrated probabilities across the 3 in-scope tomato diseases."* |
| **4** | Show Weather Escalation | Re-run with `cool_wet` weather $\rightarrow$ Severity jumps from **MODERATE $\rightarrow$ HIGH / CRITICAL** | *"Notice how the Risk Assessment Agent dynamically escalates risk under cool wet conditions because Phytophthora infestans reproduces explosively in moisture."* |
| **5** | Tap on Case in **History** Tab | Case Detail Screen opens $\rightarrow$ scroll down to **Reassessment Timeline** | *"Our expandable chronological timeline tracks adaptive reassessments over time, showing directional severity transitions like Prior: INDETERMINATE to Revised: CRITICAL."* |
| **6** | Tap `"Generate & Export PDF Report"` | Green status appears: `PDF Ready: 95 KB` $\rightarrow$ Tap `"Share"` $\rightarrow$ Android Share Sheet appears | *"The PDF report is generated 100% locally on the device using native Android Canvas and PdfDocument without internet."* |
| **7** | Go to **Assistant** Tab (Tab 2) | Enter query in Hindi (or speak Hindi): *"पछेती झुलसा का उपचार"* | Grounded response in native Hindi with 4 extension citations from Cornell and UC IPM | *"Our assistant features automated Devanagari script detection, generating fluent Hindi agronomic advice grounded in university literature."* |

---

## 3. High-Probability Examiner Questions & Exact Defenses

### Q: "Why didn't you train on the entire 38-class PlantVillage dataset?"
- **Defense:** *"Generalist 38-class models frequently misclassify similar foliar symptoms across different crops. For smallholder tomato farmers in North India, Bacterial Spot, Early Blight, and Late Blight cause over 80% of preventable foliar yield loss. Bounding our vision model to these 3 pathogens allowed us to achieve 98.41% validation accuracy and conduct rigorous domain-shift evaluation on in-the-wild PlantDoc imagery."*

### Q: "What prevents the AI assistant from giving dangerous chemical advice?"
- **Defense:** *"We implement a three-layer guardrail: First, RAG grounding restricts information to 63 curated chunks from Cornell CALS, UC IPM, and Purdue Extension. Second, our Critic Agent programmatically audits all plans before generation, enforcing mandatory EPA pesticide notices and restricting curative fungicides (like Cymoxanil) to 24–48h kickback windows. Third, chemical recommendations are strictly withheld under diagnostic conflict."*

### Q: "How does the app work if the farmer has no internet in the field?"
- **Defense:** *"AgriMind has full offline resilience: all previous cases and conversations are stored on the device in SQLite (`agrimind_chat.db`). PDF generation happens 100% on the phone's CPU. The backend itself is designed to run on a local farm laptop or edge micro-PC connected over local Wi-Fi without requiring external internet."*

### Q: "What was the hardest bug you encountered and how did you resolve it?"
- **Defense:** *"During Stage B.7 and C.1, we discovered that Devanagari Hindi questions were receiving English answers because the backend LLM defaulted to English prompts without explicit script detection. We resolved this by implementing regex-based Devanagari Unicode detection (`\u0900..\u097F`) on both the Android client and the FastAPI backend, paired with an agronomic Hindi dictionary (`AGRONOMIC_SENTENCE_PATTERNS_HI`) to guarantee vernacular consistency."*

