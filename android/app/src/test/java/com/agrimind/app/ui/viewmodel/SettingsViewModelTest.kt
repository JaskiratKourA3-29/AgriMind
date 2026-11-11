package com.agrimind.app.ui.viewmodel

import android.app.Application
import com.agrimind.app.data.local.UserSessionManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class SettingsViewModelTest {

    private lateinit var app: Application
    private lateinit var viewModel: SettingsViewModel

    @Before
    fun setUp() {
        Dispatchers.setMain(UnconfinedTestDispatcher())
        UserSessionManager.resetInstanceForTesting()
        app = Application()
        viewModel = SettingsViewModel(app)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
        UserSessionManager.resetInstanceForTesting()
    }

    @Test
    fun testDefaultGuestFarmerState() {
        val state = viewModel.uiState.value
        assertEquals("Guest Farmer", state.username)
        assertEquals("farmer", state.role)
        assertEquals("en", state.language)
        assertFalse(state.isLoggedIn)
    }

    @Test
    fun testLoginAsDemoFarmer() {
        viewModel.loginAsDemoFarmer()
        val state = viewModel.uiState.value
        assertEquals("jammu_farmer", state.username)
        assertEquals("farmer", state.role)
        assertTrue(state.isLoggedIn)
        assertEquals("Raghubir Singh (R.S. Pura)", state.fullName)
    }

    @Test
    fun testLoginAsDemoAdmin() {
        viewModel.loginAsDemoAdmin()
        val state = viewModel.uiState.value
        assertEquals("agri_admin", state.username)
        assertEquals("admin", state.role)
        assertTrue(state.isLoggedIn)
    }

    @Test
    fun testLanguageSelection() {
        viewModel.setLanguage("hi")
        assertEquals("hi", viewModel.uiState.value.language)

        viewModel.setLanguage("en")
        assertEquals("en", viewModel.uiState.value.language)
    }

    @Test
    fun testLogoutClearsSession() {
        viewModel.loginAsDemoFarmer()
        assertTrue(viewModel.uiState.value.isLoggedIn)

        viewModel.logout()
        val state = viewModel.uiState.value
        assertFalse(state.isLoggedIn)
        assertEquals("Guest Farmer", state.username)
        assertEquals("farmer", state.role)
    }
}
