package com.agrimind.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agrimind.app.ui.theme.ForestGreenDark
import com.agrimind.app.ui.theme.ForestGreenPrimary
import com.agrimind.app.ui.viewmodel.SettingsViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel,
    onNavigateToSystemHealth: () -> Unit = {},
    onNavigateToAuth: () -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsState()
    val scrollState = rememberScrollState()

    var showLoginDialog by remember { mutableStateOf(false) }
    var loginUser by remember { mutableStateOf("") }
    var loginPass by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Status Message Banner
        uiState.statusMessage?.let { msg ->
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFFE8F5E9)),
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Default.Info, contentDescription = null, tint = ForestGreenDark)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(text = msg, style = MaterialTheme.typography.bodyMedium, color = ForestGreenDark)
                }
            }
        }

        // 1. Account & Role Separation Card
        Card(
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = if (uiState.language == "hi") "उपयोगकर्ता प्रोफ़ाइल और भूमिका" else "User Profile & Role",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = ForestGreenDark
                )
                Spacer(modifier = Modifier.height(12.dp))

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Box(
                        modifier = Modifier
                            .size(54.dp)
                            .clip(CircleShape)
                            .background(
                                if (uiState.role.equals("admin", true)) Color(0xFFFFE0B2) else Color(0xFFC8E6C9)
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = if (uiState.role.equals("admin", true)) Icons.Default.AdminPanelSettings else Icons.Default.Person,
                            contentDescription = null,
                            tint = if (uiState.role.equals("admin", true)) Color(0xFFE65100) else ForestGreenPrimary,
                            modifier = Modifier.size(32.dp)
                        )
                    }

                    Spacer(modifier = Modifier.width(14.dp))

                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = uiState.fullName,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold
                        )
                        Text(
                            text = "@${uiState.username}",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color.Gray
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        val roleBadgeColor = when (uiState.role.lowercase()) {
                            "owner" -> Color(0xFFFFF9C4)
                            "admin" -> Color(0xFFFFF3E0)
                            else -> Color(0xFFE8F5E9)
                        }
                        val roleTextColor = when (uiState.role.lowercase()) {
                            "owner" -> Color(0xFFF57F17)
                            "admin" -> Color(0xFFE65100)
                            else -> ForestGreenDark
                        }
                        val roleText = when (uiState.role.lowercase()) {
                            "owner" -> "PROJECT OWNER"
                            "admin" -> "ADMINISTRATOR"
                            else -> "REGISTERED FARMER"
                        }
                        Surface(
                            shape = RoundedCornerShape(4.dp),
                            color = roleBadgeColor
                        ) {
                            Text(
                                text = roleText,
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.Bold,
                                color = roleTextColor,
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                if (uiState.isLoggedIn) {
                    OutlinedButton(
                        onClick = { viewModel.logout() },
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFFC62828)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.Logout, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(if (uiState.language == "hi") "लॉग आउट करें" else "Log Out")
                    }
                } else {
                    OutlinedButton(
                        onClick = onNavigateToAuth,
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = ForestGreenDark),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.Login, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(if (uiState.language == "hi") "साइन इन या नया खाता बनाएं" else "Sign In / Register Account")
                    }
                }
            }
        }

        // 2. Backend Gateway & Server Configuration Card
        Card(
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(
                        imageVector = Icons.Default.CloudSync,
                        contentDescription = null,
                        tint = ForestGreenDark,
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (uiState.language == "hi") "बैकएंड गेटवे कॉन्फ़िगरेशन" else "Backend Gateway URL",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = ForestGreenDark
                    )
                }

                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = if (uiState.language == "hi")
                        "स्थानीय एमुलेटर (10.0.2.2:8000) या क्लाउडफ़्लेयर HTTPS टनल URL दर्ज करें:"
                    else
                        "Configure connection to local emulator (10.0.2.2:8000) or Cloudflare HTTPS tunnel:",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.DarkGray
                )

                Spacer(modifier = Modifier.height(12.dp))

                OutlinedTextField(
                    value = uiState.gatewayInput,
                    onValueChange = { viewModel.setGatewayInput(it) },
                    label = { Text(if (uiState.language == "hi") "सर्वर गेटवे URL" else "Server Gateway URL") },
                    placeholder = { Text("https://xxxx.trycloudflare.com/") },
                    singleLine = true,
                    isError = uiState.gatewayError != null,
                    supportingText = {
                        uiState.gatewayError?.let { err ->
                            Text(text = err, color = MaterialTheme.colorScheme.error, fontSize = 12.sp)
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = ForestGreenPrimary,
                        unfocusedBorderColor = Color.Gray
                    )
                )

                Spacer(modifier = Modifier.height(10.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Button(
                        onClick = { viewModel.saveGatewayUrl() },
                        colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary),
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.Save, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(if (uiState.language == "hi") "लागू करें" else "Apply", fontSize = 13.sp)
                    }

                    OutlinedButton(
                        onClick = { viewModel.resetToEmulatorGateway() },
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.RestartAlt, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(if (uiState.language == "hi") "एमुलेटर डिफ़ॉल्ट" else "Reset Default", fontSize = 12.sp)
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                Button(
                    onClick = { viewModel.testGatewayConnection() },
                    colors = ButtonDefaults.buttonColors(containerColor = ForestGreenDark),
                    enabled = !uiState.isTestingGateway,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    if (uiState.isTestingGateway) {
                        CircularProgressIndicator(color = Color.White, modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(if (uiState.language == "hi") "परीक्षण जारी है..." else "Testing Connection...", fontSize = 13.sp)
                    } else {
                        Icon(Icons.Default.NetworkCheck, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(if (uiState.language == "hi") "गेटवे का परीक्षण करें" else "Test Gateway Health", fontSize = 13.sp)
                    }
                }

                // Test result banner
                uiState.gatewayTestResult?.let { result ->
                    Spacer(modifier = Modifier.height(10.dp))
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = if (uiState.gatewayTestSuccess == true) Color(0xFFE8F5E9) else Color(0xFFFFEBEE),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier.padding(10.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = if (uiState.gatewayTestSuccess == true) Icons.Default.CheckCircle else Icons.Default.Error,
                                contentDescription = null,
                                tint = if (uiState.gatewayTestSuccess == true) ForestGreenDark else Color(0xFFC62828),
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = result,
                                style = MaterialTheme.typography.bodySmall,
                                color = if (uiState.gatewayTestSuccess == true) ForestGreenDark else Color(0xFFC62828)
                            )
                        }
                    }
                }
            }
        }

        // 3. Language Selection Card
        Card(
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = if (uiState.language == "hi") "भाषा चयन (Language Selection)" else "Language Selection",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = ForestGreenDark
                )
                Spacer(modifier = Modifier.height(10.dp))

                // English Option
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    RadioButton(
                        selected = uiState.language == "en",
                        onClick = { viewModel.setLanguage("en") }
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Column {
                        Text("English", fontWeight = FontWeight.SemiBold)
                        Text("Active — Complete Voice & Advisory Support", fontSize = 12.sp, color = Color.Gray)
                    }
                }

                Divider(modifier = Modifier.padding(vertical = 6.dp))

                // Hindi Option
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    RadioButton(
                        selected = uiState.language == "hi",
                        onClick = { viewModel.setLanguage("hi") }
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Column {
                        Text("हिंदी (Hindi)", fontWeight = FontWeight.SemiBold)
                        Text("सक्रिय — पूर्ण आवाज और कृषि विस्तार परामर्श समर्थन", fontSize = 12.sp, color = Color.Gray)
                    }
                }

                Divider(modifier = Modifier.padding(vertical = 6.dp))

                // Dogri Option (Future Scope)
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    RadioButton(
                        selected = false,
                        onClick = {},
                        enabled = false
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Column {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("डोगरी (Dogri)", fontWeight = FontWeight.SemiBold, color = Color.Gray)
                            Spacer(modifier = Modifier.width(6.dp))
                            Surface(
                                shape = RoundedCornerShape(4.dp),
                                color = Color(0xFFEEEEEE)
                            ) {
                                Text(
                                    "Future Scope",
                                    fontSize = 10.sp,
                                    color = Color.DarkGray,
                                    modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
                                )
                            }
                        }
                        Text(
                            "विकासाधीन (In Development): डोगरी न्यूरल स्पीच मॉडल भविष्य के संस्करण में शामिल किए जाएंगे।",
                            fontSize = 11.sp,
                            color = Color(0xFF757575)
                        )
                    }
                }
            }
        }

        // 3. Admin Operational Status (Visible if Admin or Owner)
        if (uiState.role.equals("admin", true) || uiState.role.equals("owner", true)) {
            Card(
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF8E1)),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Admin Telemetry & Model Overview",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFBF360C)
                        )
                        IconButton(onClick = { viewModel.fetchAdminStatus() }) {
                            Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = Color(0xFFBF360C))
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    val admin = uiState.adminStatus
                    if (admin != null) {
                        Text("• Registered Users: ${admin.totalUsers}", fontSize = 13.sp)
                        Text("• Total Diagnosed Cases: ${admin.totalCases}", fontSize = 13.sp)
                        Text("• Shared Community Cases: ${admin.totalSharedCases}", fontSize = 13.sp)
                        Text("• Farmer Discussion Comments: ${admin.totalComments}", fontSize = 13.sp)
                        Text("• ChromaDB Vector Chunks: ${admin.vectorstoreChunks}", fontSize = 13.sp)
                        Text("• Supported Regional Crops: ${admin.supportedCrops.joinToString(", ")}", fontSize = 13.sp)
                    } else {
                        Text(
                            "Admin telemetry loaded or awaiting backend connection.",
                            fontSize = 13.sp,
                            color = Color.DarkGray
                        )
                    }

                    Spacer(modifier = Modifier.height(10.dp))
                    Button(
                        onClick = onNavigateToSystemHealth,
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE65100)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.Dns, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Open Full Backend Health Monitor", fontSize = 12.sp)
                    }
                }
            }
        }

        // 4. Model Scope & Certification Disclaimers
        Card(
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = if (uiState.language == "hi") "मॉडल दायरा और कानूनी अस्वीकरण" else "Vision Scope & Advisory Disclaimer",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = ForestGreenDark
                )
                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = "• Tomato Vision Model Scope: The camera vision classifier (ResNet-50) is strictly specialized for 3 tomato diseases: Early Blight (Alternaria solani), Late Blight (Phytophthora infestans), and Bacterial Spot (Xanthomonas).\n\n" +
                            "• Regional Crop Guidance: For Wheat, Rice/Paddy, Potato, Mustard, and Chili, AgriMind provides institutional agronomic and IPM guidance sourced from ICAR and SAU handbooks.\n\n" +
                            "• Official Disclaimer: AgriMind is an agricultural decision-support tool. It does not replace field inspection by certified agronomists or official statutory pesticide regulations.",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.DarkGray,
                    lineHeight = 18.sp
                )
            }
        }

        // 5. Build Information & Project Attribution
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "AgriMind Minor Project • COM71116-21",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
                color = ForestGreenDark
            )
            Text(
                text = "FastAPI Backend + ChromaDB (63 chunks) + Jetpack Compose Android",
                style = MaterialTheme.typography.labelSmall,
                color = Color.Gray
            )
        }
    }
}

