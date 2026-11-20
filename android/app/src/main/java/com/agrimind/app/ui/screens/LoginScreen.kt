package com.agrimind.app.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusDirection
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import com.agrimind.app.R
import com.agrimind.app.data.api.RetrofitClient
import com.agrimind.app.data.model.AuthTokenResponse
import com.agrimind.app.data.model.UserLoginRequest
import com.agrimind.app.ui.theme.ForestGreenDark
import com.agrimind.app.ui.theme.ForestGreenPrimary
import com.agrimind.app.ui.theme.LightGreenBackground

/**
 * Professional Branded Authentication Screen for AgriMind Mobile App.
 * Supports Farmer and Administrator sign-in, input validation, password toggle,
 * demo account presets for verification, and guest offline access.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LoginScreen(
    onLoginSuccess: (AuthTokenResponse) -> Unit,
    onNavigateToSignup: () -> Unit,
    onContinueAsGuest: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    val focusManager = LocalFocusManager.current
    val scrollState = rememberScrollState()

    var usernameOrEmail by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var isPasswordVisible by remember { mutableStateOf(false) }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    fun performLogin(targetUser: String = usernameOrEmail, targetPass: String = password) {
        val cleanUser = targetUser.trim()
        val cleanPass = targetPass.trim()

        if (cleanUser.isBlank()) {
            errorMessage = "Please enter your email or username."
            return
        }
        if (cleanPass.length < 6) {
            errorMessage = "Password must be at least 6 characters."
            return
        }

        errorMessage = null
        isLoading = true

        coroutineScope.launch {
            try {
                val req = UserLoginRequest(
                    email = if (cleanUser.contains("@")) cleanUser else null,
                    username = if (!cleanUser.contains("@")) cleanUser else null,
                    password = cleanPass
                )
                val response = RetrofitClient.apiService.login(req)
                if (response.isSuccessful && response.body() != null) {
                    val authData = response.body()!!
                    RetrofitClient.setAuthToken(authData.accessToken)
                    onLoginSuccess(authData)
                } else {
                    val errorBody = response.errorBody()?.string() ?: ""
                    errorMessage = when {
                        response.code() == 401 -> "Invalid credentials or account is deactivated."
                        errorBody.contains("detail") -> errorBody.substringAfter("\"detail\":\"").substringBefore("\"")
                        else -> "Sign-in failed (Code ${response.code()}). Check credentials."
                    }
                }
            } catch (e: Exception) {
                errorMessage = "Connection error: ${e.localizedMessage ?: "Backend server unreachable. Make sure your internet connection is active."}"
            } finally {
                isLoading = false
            }
        }
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = LightGreenBackground
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Spacer(modifier = Modifier.height(24.dp))

            // 1. Professional App Logo Branding
            Box(
                modifier = Modifier
                    .size(108.dp)
                    .clip(CircleShape)
                    .background(Color.White)
                    .padding(8.dp),
                contentAlignment = Alignment.Center
            ) {
                Image(
                    painter = painterResource(id = R.drawable.agrimind_logo),
                    contentDescription = "AgriMind Official Logo",
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Fit
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // 2. App Name & Title
            Text(
                text = "AgriMind",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.ExtraBold,
                color = ForestGreenDark,
                letterSpacing = 1.sp
            )

            Text(
                text = "AI Crop Health Decision Support",
                style = MaterialTheme.typography.bodyMedium,
                color = Color(0xFF2E7D32),
                fontWeight = FontWeight.SemiBold
            )

            Text(
                text = "Jammu & Kashmir Agricultural Extension Pilot",
                style = MaterialTheme.typography.bodySmall,
                color = Color(0xFF558B2F),
                fontSize = 11.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 2.dp)
            )

            Spacer(modifier = Modifier.height(24.dp))

            // 3. Login Credentials Card
            Card(
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Sign In to Your Account",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = ForestGreenDark,
                        modifier = Modifier.fillMaxWidth()
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    // Email / Username Input
                    OutlinedTextField(
                        value = usernameOrEmail,
                        onValueChange = {
                            usernameOrEmail = it
                            errorMessage = null
                        },
                        label = { Text("Email or Username") },
                        leadingIcon = {
                            Icon(Icons.Default.Person, contentDescription = null, tint = ForestGreenPrimary)
                        },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.Email,
                            imeAction = ImeAction.Next
                        ),
                        keyboardActions = KeyboardActions(
                            onNext = { focusManager.moveFocus(FocusDirection.Down) }
                        ),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = ForestGreenPrimary,
                            focusedLabelColor = ForestGreenPrimary
                        ),
                        modifier = Modifier.fillMaxWidth()
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    // Password Input with Visibility Toggle
                    OutlinedTextField(
                        value = password,
                        onValueChange = {
                            password = it
                            errorMessage = null
                        },
                        label = { Text("Password") },
                        leadingIcon = {
                            Icon(Icons.Default.Lock, contentDescription = null, tint = ForestGreenPrimary)
                        },
                        trailingIcon = {
                            IconButton(onClick = { isPasswordVisible = !isPasswordVisible }) {
                                Icon(
                                    imageVector = if (isPasswordVisible) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                                    contentDescription = if (isPasswordVisible) "Hide password" else "Show password",
                                    tint = Color.Gray
                                )
                            }
                        },
                        singleLine = true,
                        visualTransformation = if (isPasswordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.Password,
                            imeAction = ImeAction.Done
                        ),
                        keyboardActions = KeyboardActions(
                            onDone = {
                                focusManager.clearFocus()
                                performLogin()
                            }
                        ),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = ForestGreenPrimary,
                            focusedLabelColor = ForestGreenPrimary
                        ),
                        modifier = Modifier.fillMaxWidth()
                    )

                    // Error Message Banner
                    errorMessage?.let { error ->
                        Spacer(modifier = Modifier.height(12.dp))
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = Color(0xFFFFEBEE),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier.padding(10.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    Icons.Default.ErrorOutline,
                                    contentDescription = "Error",
                                    tint = Color(0xFFC62828),
                                    modifier = Modifier.size(18.dp)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = error,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = Color(0xFFC62828)
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    // Sign In Button
                    Button(
                        onClick = {
                            focusManager.clearFocus()
                            performLogin()
                        },
                        enabled = !isLoading,
                        shape = RoundedCornerShape(10.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp)
                    ) {
                        if (isLoading) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(22.dp),
                                color = Color.White,
                                strokeWidth = 2.5.dp
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Text("Signing In...")
                        } else {
                            Icon(Icons.Default.Login, contentDescription = null, modifier = Modifier.size(20.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Sign In",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Sign Up Navigation Link
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "New farmer to AgriMind? ",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color.Gray
                        )
                        TextButton(
                            onClick = onNavigateToSignup,
                            contentPadding = PaddingValues(0.dp)
                        ) {
                            Text(
                                text = "Register Here",
                                style = MaterialTheme.typography.bodySmall,
                                fontWeight = FontWeight.Bold,
                                color = ForestGreenPrimary
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // 4. Quick Testing Presets & Guest Access Card
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.9f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Quick Evaluation & Offline Access",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold,
                        color = Color.DarkGray
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    // Safe Autofill for Demo Farmer Evaluation (No auto-login; user must tap Sign In)
                    OutlinedButton(
                        onClick = {
                            usernameOrEmail = "farmer_local@agrimind.in"
                            password = "Password123"
                        },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(8.dp),
                        contentPadding = PaddingValues(vertical = 6.dp)
                    ) {
                        Icon(
                            Icons.Default.Edit,
                            contentDescription = null,
                            tint = ForestGreenDark,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Fill Demo Farmer Credentials",
                            fontSize = 12.sp,
                            color = ForestGreenDark,
                            fontWeight = FontWeight.Medium
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // Safe Autofill for Project Owner & Admin Console Evaluation
                    OutlinedButton(
                        onClick = {
                            usernameOrEmail = "jaskiratkourjk2005@gmail.com"
                            password = "AgriMind@Owner2026!"
                        },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(8.dp),
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = Color(0xFF6A1B9A)
                        ),
                        contentPadding = PaddingValues(vertical = 6.dp)
                    ) {
                        Icon(
                            Icons.Default.AdminPanelSettings,
                            contentDescription = null,
                            tint = Color(0xFF6A1B9A),
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Fill Verified Project Owner Credentials",
                            fontSize = 12.sp,
                            color = Color(0xFF6A1B9A),
                            fontWeight = FontWeight.Bold
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    TextButton(
                        onClick = onContinueAsGuest,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(
                            Icons.Default.Agriculture,
                            contentDescription = null,
                            tint = ForestGreenDark,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Continue as Guest Farmer (Field Offline Mode)",
                            style = MaterialTheme.typography.bodySmall,
                            color = ForestGreenDark,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))
        }
    }
}

