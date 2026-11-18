package com.agrimind.app.data.api

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Singleton Retrofit HTTP client for AgriMind Android application.
 * Configured with Android Emulator host loopback address (10.0.2.2:8000)
 * and extended timeouts to accommodate CPU-based neural network inference.
 */
object RetrofitClient {

    // Default cloud production gateway URL (Vercel HTTPS deployment):
    const val DEFAULT_BASE_URL = "https://agrimind-backend.vercel.app/"
    const val EMULATOR_FALLBACK_URL = "http://10.0.2.2:8000/"

    private var currentBaseUrl: String = DEFAULT_BASE_URL
    private var cachedApiService: AgriMindApiService? = null
    private var currentAuthToken: String? = null

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        // Headers level to avoid dumping entire image bytes to logcat
        level = HttpLoggingInterceptor.Level.HEADERS
    }

    private val authInterceptor = okhttp3.Interceptor { chain ->
        val original = chain.request()
        val builder = original.newBuilder()
        currentAuthToken?.let { token ->
            if (token.isNotBlank()) {
                builder.header("Authorization", "Bearer $token")
            }
        }
        chain.proceed(builder.build())
    }

    private val okHttpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(120, TimeUnit.SECONDS)   // Accommodates ResNet-50 CPU workflow latency
            .writeTimeout(60, TimeUnit.SECONDS)   // Allows multipart image upload
            .addInterceptor(authInterceptor)
            .addInterceptor(loggingInterceptor)
            .retryOnConnectionFailure(true)
            .build()
    }

    fun setAuthToken(token: String?) {
        currentAuthToken = token
    }

    val apiService: AgriMindApiService
        get() {
            if (cachedApiService == null) {
                cachedApiService = buildRetrofit(currentBaseUrl).create(AgriMindApiService::class.java)
            }
            return cachedApiService!!
        }

    fun setBaseUrl(newUrl: String) {
        val sanitized = if (newUrl.endsWith("/")) newUrl else "$newUrl/"
        if (sanitized != currentBaseUrl) {
            currentBaseUrl = sanitized
            cachedApiService = buildRetrofit(currentBaseUrl).create(AgriMindApiService::class.java)
        }
    }

    fun getBaseUrl(): String = currentBaseUrl

    private fun buildRetrofit(baseUrl: String): Retrofit {
        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }
}
