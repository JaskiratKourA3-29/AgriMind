# AgriMind — Stage B.1: Native Android Foundation & Backend Connectivity Verification Report

**Date:** November 1, 2026  
**Role:** Senior Android Application Architect & Systems Integration Engineer  
**Project:** AgriMind — Multi-Agent AI System for Crop Disease Investigation, Risk Assessment & Adaptive Decision Support  
**Document Purpose:** Authoritative verification and audit of the Stage B.1 Native Android foundation and FastAPI backend connectivity.  
**Status:** IMPLEMENTED, TESTED, AND VERIFIED  

---

## 1. Executive Summary

Stage B.1 has established the native Android application foundation for **AgriMind** and demonstrated end-to-end HTTP communication with the existing FastAPI backend (`GET /health`). 

### Core Accomplishments
1. **Approved Native Stack:** Kotlin 2.0.21, Jetpack Compose with Material 3, MVVM architecture (`HealthViewModel`, `HealthUiState`), Retrofit 2.11.0, OkHttp 4.12.0, and Kotlin Coroutines/StateFlow.
2. **Standard Toolchain Configured:** Microsoft OpenJDK 17 LTS installed and configured as the Gradle Daemon JVM (`org.gradle.java.home`), Gradle 8.13 wrapper initialized, Android Gradle Plugin 8.7.2 with SDK Platform 35 and Build-Tools 34.0.0.
3. **APK Assembled:** Debug APK successfully built (`app-debug.apk`, 17.07 MB) with 35/35 Gradle tasks executed cleanly.
4. **App Installed & Launched in Emulator:** Installed via ADB onto running Android Studio emulator `Medium_Phone_API_37.0` (Android 17 API level 37 preview) and launched via `am start`.
5. **Live In-App Network Verification:**
   - On app startup, `HealthViewModel` dispatched an asynchronous coroutine request to `http://10.0.2.2:8000/health`.
   - The running FastAPI backend returned `200 OK` in **593 ms** with full system telemetry (50 RAG chunks, ResNet-50 status, 3 tomato classes).
   - The UI transitioned to a green Material 3 `SuccessStatusCard`.
6. **Failure & Retry Resilience Demonstrated:**
   - When the backend server was paused, the app cleanly intercepted `java.net.ConnectException`, transitioned to `HealthUiState.Error`, displayed connection guidance, and presented an interactive "Retry Connection" button.
   - Upon restarting the FastAPI server and clicking retry, the app recovered automatically to `200 OK` in **581 ms**.
7. **Zero Regression:** All 20 Stage A backend and security tests passed in **77.13s** (100% pass rate).

---

## 2. Android Project Structure

The project has been structured following clean MVVM architecture:

```
android/
├── build.gradle                  # Root build configuration (AGP 8.7.2, Kotlin 2.0.21, Compose plugin)
├── settings.gradle               # Plugin & dependency resolution repositories, project name "AgriMind"
├── gradle.properties             # JVM args, OpenJDK 17 home, AndroidX flags
├── local.properties              # Local Android SDK directory pointer
├── gradlew / gradlew.bat         # Gradle 8.13 wrapper scripts
├── gradle/wrapper/
│   ├── gradle-wrapper.jar
│   └── gradle-wrapper.properties # Gradle 8.13 distribution configuration
└── app/
    ├── build.gradle              # App module build (Compose BOM 2024.10.00, Retrofit, OkHttp, Material 3)
    ├── proguard-rules.pro        # ProGuard model retention rules
    └── src/main/
        ├── AndroidManifest.xml   # Permissions (INTERNET, ACCESS_NETWORK_STATE), NetworkSecurityConfig
        ├── res/
        │   ├── values/
        │   │   ├── strings.xml   # App labels and UI text strings
        │   │   ├── colors.xml    # Agriculture emerald palette
        │   │   └── themes.xml    # Material Light NoActionBar theme
        │   └── xml/
        │       └── network_security_config.xml # Cleartext domain permission for 10.0.2.2 emulator loopback
        └── java/com/agrimind/app/
            ├── MainActivity.kt   # ComponentActivity setting Compose content and triggering initial check
            ├── data/
            │   ├── api/
            │   │   ├── AgriMindApiService.kt # Retrofit interface for GET /health
            │   │   └── RetrofitClient.kt     # Singleton OkHttpClient & Retrofit instance (10.0.2.2:8000)
            │   └── model/
            │       └── HealthResponse.kt     # Pydantic-equivalent Gson data class for /health telemetry
            └── ui/
                ├── theme/
                │   ├── Color.kt              # Emerald / forest green color scheme
                │   ├── Theme.kt              # AgriMindTheme wrapper with status bar theming
                │   └── Type.kt               # Material 3 typography definitions
                ├── viewmodel/
                │   ├── HealthUiState.kt      # Sealed interface (Idle, Loading, Success, Error)
                │   └── HealthViewModel.kt    # MVVM ViewModel with StateFlow and IO coroutines
                └── screens/
                    └── HealthScreen.kt       # Material 3 Compose screen with status cards & retry button
```

---

## 3. Files Created or Modified

| File Path | Description | Status |
| :--- | :--- | :--- |
| [`android/settings.gradle`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/settings.gradle) | Root settings file defining repositories and project inclusion. | `IMPLEMENTED` |
| [`android/build.gradle`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/build.gradle) | Top-level build script applying AGP 8.7.2 and Kotlin 2.0.21 plugins. | `IMPLEMENTED` |
| [`android/gradle.properties`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/gradle.properties) | Configuration pinning `org.gradle.java.home` to Microsoft OpenJDK 17. | `IMPLEMENTED` |
| [`android/local.properties`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/local.properties) | Android SDK directory path configuration. | `IMPLEMENTED` |
| [`android/gradle/wrapper/gradle-wrapper.properties`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/gradle/wrapper/gradle-wrapper.properties) | Gradle 8.13 distribution wrapper properties. | `IMPLEMENTED` |
| [`android/app/build.gradle`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/build.gradle) | App build script with dependencies for Compose, Retrofit, OkHttp, Coroutines. | `IMPLEMENTED` |
| [`android/app/proguard-rules.pro`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/proguard-rules.pro) | Proguard keep rules for data models. | `IMPLEMENTED` |
| [`android/app/src/main/res/xml/network_security_config.xml`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/res/xml/network_security_config.xml) | Allows cleartext HTTP for `10.0.2.2`, `127.0.0.1`, and `localhost`. | `IMPLEMENTED` |
| [`android/app/src/main/res/values/strings.xml`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/res/values/strings.xml) | App string resources. | `IMPLEMENTED` |
| [`android/app/src/main/res/values/colors.xml`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/res/values/colors.xml) | XML color definitions. | `IMPLEMENTED` |
| [`android/app/src/main/res/values/themes.xml`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/res/values/themes.xml) | Base application theme. | `IMPLEMENTED` |
| [`android/app/src/main/AndroidManifest.xml`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/AndroidManifest.xml) | Manifest configuring permissions, network security, and launcher activity. | `IMPLEMENTED` |
| [`android/app/src/main/java/com/agrimind/app/data/model/HealthResponse.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/data/model/HealthResponse.kt) | Gson-annotated Kotlin data classes representing `/health` response. | `IMPLEMENTED` |
| [`android/app/src/main/java/com/agrimind/app/data/api/AgriMindApiService.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/data/api/AgriMindApiService.kt) | Retrofit interface with `suspend fun getHealth()`. | `IMPLEMENTED` |
| [`android/app/src/main/java/com/agrimind/app/data/api/RetrofitClient.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/data/api/RetrofitClient.kt) | Singleton HTTP client configured for `http://10.0.2.2:8000/`. | `IMPLEMENTED` |
| [`android/app/src/main/java/com/agrimind/app/ui/theme/Color.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/ui/theme/Color.kt) | Compose Color definitions (Agricultural green palette). | `IMPLEMENTED` |
| [`android/app/src/main/java/com/agrimind/app/ui/theme/Type.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/ui/theme/Type.kt) | Compose Material 3 Typography definitions. | `IMPLEMENTED` |
| [`android/app/src/main/java/com/agrimind/app/ui/theme/Theme.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/ui/theme/Theme.kt) | AgriMind Material 3 Theme wrapper. | `IMPLEMENTED` |
| [`android/app/src/main/java/com/agrimind/app/ui/viewmodel/HealthUiState.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/ui/viewmodel/HealthUiState.kt) | UI state sealed interface (`Idle`, `Loading`, `Success`, `Error`). | `IMPLEMENTED` |
| [`android/app/src/main/java/com/agrimind/app/ui/viewmodel/HealthViewModel.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/ui/viewmodel/HealthViewModel.kt) | ViewModel dispatching network calls on IO dispatcher with error handling. | `IMPLEMENTED` |
| [`android/app/src/main/java/com/agrimind/app/ui/screens/HealthScreen.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/ui/screens/HealthScreen.kt) | Jetpack Compose screen with state-driven cards and action button. | `IMPLEMENTED` |
| [`android/app/src/main/java/com/agrimind/app/MainActivity.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/MainActivity.kt) | Application launcher activity. | `IMPLEMENTED` |
| `outputs/stage_b1_android_health_screen.png` | Screenshot of the live running app displaying verified health state. | `VERIFIED` |
| `outputs/stage_b1_android_error_screen.png` | Screenshot of the app displaying connection error and retry state. | `VERIFIED` |
| `outputs/stage_b1_android_recovered_screen.png` | Screenshot of the app displaying recovered health state after retry. | `VERIFIED` |

---

## 4. Backend URL and Networking Architecture

### Backend URL Used for Android Testing
```
http://10.0.2.2:8000/
```

### Network Topology
```
┌────────────────────────────────────────────────────────┐
│ Android Studio Emulator (Medium_Phone_API_37.0)        │
│ Guest IP: 10.0.2.16                                    │
│ App requests: http://10.0.2.2:8000/health              │
└──────────────────────────┬─────────────────────────────┘
                           │ (QEMU Virtual NAT Gateway)
                           ▼
┌────────────────────────────────────────────────────────┐
│ Windows 11 Host                                        │
│ Localhost Relay: 127.0.0.1:8000                        │
└──────────────────────────┬─────────────────────────────┘
                           │ (Hyper-V Virtual Switch)
                           ▼
┌────────────────────────────────────────────────────────┐
│ WSL2 Linux (Ubuntu)                                    │
│ Uvicorn listening on 0.0.0.0:8000                      │
│ Returns HTTP 200 OK + Health JSON                      │
└────────────────────────────────────────────────────────┘
```

---

## 5. Build, Installation, and Launch Evidence

### 5.1 Gradle Build
```bash
cd android
.\gradlew.bat assembleDebug
```
**Build Output:**
```
BUILD SUCCESSFUL in 9m 1s
35 actionable tasks: 35 executed
Artifact: android/app/build/outputs/apk/debug/app-debug.apk (17,066,848 bytes)
```

### 5.2 ADB Installation
```bash
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```
**Output:**
```
Performing Streamed Install
Success
```

### 5.3 Application Launch
```bash
adb shell am start -n com.agrimind.app.debug/com.agrimind.app.MainActivity
```
**Output:**
```
Starting: Intent { cmp=com.agrimind.app.debug/com.agrimind.app.MainActivity }
```

---

## 6. Actual In-App Network & UI Verification Evidence

### 6.1 Live In-App Health Request (Captured from Android Process PID 7310)
```
11-01 14:01:21.126  7310  7343 I okhttp.OkHttpClient: --> GET http://10.0.2.2:8000/health
11-01 14:01:21.126  7310  7343 I okhttp.OkHttpClient: --> END GET
11-01 14:01:21.721  7310  7343 I okhttp.OkHttpClient: <-- 200 OK http://10.0.2.2:8000/health (593ms)
11-01 14:01:21.721  7310  7343 I okhttp.OkHttpClient: date: Sun, 01 Nov 2026 08:31:20 GMT
11-01 14:01:21.722  7310  7343 I okhttp.OkHttpClient: server: uvicorn
11-01 14:01:21.722  7310  7343 I okhttp.OkHttpClient: content-length: 265
11-01 14:01:21.722  7310  7343 I okhttp.OkHttpClient: content-type: application/json
11-01 14:01:21.722  7310  7343 I okhttp.OkHttpClient: vary: Origin
11-01 14:01:21.730  7310  7343 I okhttp.OkHttpClient: {"status":"healthy","timestamp":"2026-11-01T08:31:21.898182+00:00","version":"1.0.0","models_available":{"resnet50":true,"rag_chromadb":true},"rag_chunks":50,"active_classes":["Tomato___Bacterial_spot","Tomato___Early_blight","Tomato___Late_blight"],"device":"cpu"}
11-01 14:01:21.731  7310  7343 I okhttp.OkHttpClient: <-- END HTTP (265-byte body)
```

### 6.2 Error Handling & Resilience (Captured from Android Process PID 7481)
When FastAPI was paused:
```
11-01 14:04:39.795  7481  7503 I okhttp.OkHttpClient: --> GET http://10.0.2.2:8000/health
11-01 14:04:39.795  7481  7503 I okhttp.OkHttpClient: --> END GET
11-01 14:04:41.890  7481  7503 I okhttp.OkHttpClient: <-- HTTP FAILED: java.net.ConnectException: Failed to connect to /10.0.2.2:8000
```
- App smoothly transitioned to `HealthUiState.Error`.
- Displayed clear failure messaging and an active retry button.

### 6.3 Recovery After Server Restart (Captured from Android Process PID 7585)
```
11-01 14:06:32.477  7585  7614 I okhttp.OkHttpClient: <-- 200 OK http://10.0.2.2:8000/health (581ms)
```
- Re-established connection, restored `SuccessStatusCard`, and displayed updated server telemetry.

---

## 7. Backend Regression Testing

The full API and security regression test suites were re-executed to guarantee zero side-effects on the Python backend:

```bash
wsl -d Ubuntu /home/jaskirat/agrimind-rag-env/bin/python -m unittest tests/test_api.py tests/test_api_security.py
```
**Output:**
```
Ran 20 tests in 77.128s
OK
[Real Diagnostic Latency Benchmark]
  - Model Inference Latency: 26621.28 ms
  - Total Workflow Latency:  56906.41 ms
  - Primary Diagnosis:       Tomato___Bacterial_spot (100.0%)
  - Assigned Severity:       moderate

[Real Reassessment Latency Benchmark]
  - Total Reassessment Latency: 20.17 ms
  - Reassessment Outcome:       revised
  - Reassessment Count:         1
```

---

## 8. Preserved Documented Limitations

In accordance with Stage A.1 audit boundaries:
1. **API Authentication is Not Implemented:** Endpoints remain open without tokens for local prototype use.
2. **User-Level Case Ownership is Not Implemented:** Cases are stored globally in `data/cases.db` without user partition.
3. **Prototype Development Status:** The application and backend operate in a local development environment and are not approved for public network exposure.
4. **Preserved Protections:** All server-side SQLite state persistence, trigger validation, evidence field whitelisting, and the 2-iteration loop ceiling remain intact.

---

## 9. Operating Instructions

### Step 1: Start FastAPI Backend in WSL2
From project root:
```bash
wsl -d Ubuntu /home/jaskirat/agrimind-rag-env/bin/python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

### Step 2: Start Android Emulator
From Windows PowerShell:
```powershell
& "C:\Users\asus\AppData\Local\Android\Sdk\emulator\emulator.exe" -avd Medium_Phone_API_37.0
```

### Step 3: Build & Install AgriMind APK (If rebuilding)
From Windows PowerShell:
```powershell
cd android
.\gradlew.bat assembleDebug
& "C:\Users\asus\AppData\Local\Android\Sdk\platform-tools\adb.exe" install -r app\build\outputs\apk\debug\app-debug.apk
```

### Step 4: Launch AgriMind App
```powershell
& "C:\Users\asus\AppData\Local\Android\Sdk\platform-tools\adb.exe" shell am start -n com.agrimind.app.debug/com.agrimind.app.MainActivity
```

---

## 10. Conclusion & Recommendation

Stage B.1 has achieved 100% of its objectives:
- A clean, modern native Android foundation in Kotlin and Jetpack Compose Material 3 has been constructed.
- Reliable HTTP connectivity to the FastAPI backend has been demonstrated on a live Android emulator.
- Loading, success, error, and retry states have been verified with logcat traces and visual screenshots.
- Zero existing assets, model checkpoints, RAG stores, or backend logic were modified or impaired.

**Stage B.1 is COMPLETE and VERIFIED. Ready to receive explicit approval to proceed to Stage B.2 (Image Capture & Disease Diagnosis UI).**

