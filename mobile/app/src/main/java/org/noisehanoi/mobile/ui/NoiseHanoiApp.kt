package org.noisehanoi.mobile.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import org.noisehanoi.mobile.form.FormSpec
import org.noisehanoi.mobile.outbox.Outbox
import org.noisehanoi.mobile.outbox.SubmitWorker
import org.noisehanoi.mobile.settings.Settings
import java.io.File

@Composable
fun NoiseHanoiApp() {
    val navController = rememberNavController()
    val context = LocalContext.current
    val outbox = remember {
        Outbox(File(context.filesDir, SubmitWorker.OUTBOX_DIR)).also {
            // Startup is the only moment at which no form is open, so it is the only
            // moment at which an unsaved directory is certainly an abandoned draft.
            it.discardDrafts()
            it.sweep()
        }
    }
    var pending by remember { mutableStateOf(outbox.pending().size) }
    var activeForm by remember { mutableStateOf<FormSpec?>(null) }
    val settings = remember { Settings(context) }

    // Consent comes before the first form, not before the app: the map and the
    // results send nothing, so gating them would be theatre.
    var consented by remember { mutableStateOf(settings.hasConsented) }
    val start = if (settings.acceptedConsentVersion == 0) "consent" else "home"

    NavHost(navController = navController, startDestination = start) {
        composable("consent") {
            ConsentScreen(
                onAgree = {
                    settings.acceptedConsentVersion = Settings.CONSENT_VERSION
                    consented = true
                    navController.navigate("home") { popUpTo("consent") { inclusive = true } }
                },
                onDecline = {
                    // Recorded as seen but not accepted, so it is not shown again
                    // unattended; the home screen offers it back.
                    settings.acceptedConsentVersion = -1
                    consented = false
                    navController.navigate("home") { popUpTo("consent") { inclusive = true } }
                },
                onBack = if (navController.previousBackStackEntry != null) {
                    { navController.popBackStack() }
                } else {
                    null
                },
            )
        }
        composable("home") {
            // Counted in an effect, not in the composition. Assigning to state while
            // composing is what Compose calls a backwards write: the value read to
            // build the frame changes while that frame is being built, which is an
            // invalidation loop waiting for a slow enough device.
            LaunchedEffect(Unit) { pending = outbox.pending().size }
            HomeScreen(
                pendingCount = pending,
                onOpenForm = { form ->
                    activeForm = form
                    navController.navigate("form")
                },
                onOpenOutbox = { navController.navigate("outbox") },
                onOpenSettings = { navController.navigate("settings") },
                onOpenMap = { navController.navigate("map") },
                onOpenResults = { navController.navigate("results") },
                deployedOf = { settings.deployedForm(it.title) },
                mayCollect = consented,
                onReviewConsent = { navController.navigate("consent") },
            )
        }
        composable("form") {
            val form = activeForm
            if (form == null) {
                navController.popBackStack()
            } else {
                FormScreen(
                    spec = form,
                    onDone = { navController.popBackStack("home", inclusive = false) },
                    onBack = { navController.popBackStack() },
                )
            }
        }
        composable("map") { MapScreen(onBack = { navController.popBackStack() }) }
        composable("results") { ResultsScreen(onBack = { navController.popBackStack() }) }
        composable("outbox") { OutboxScreen(onBack = { navController.popBackStack() }) }
        composable("settings") {
            SettingsScreen(
                onBack = { navController.popBackStack() },
                onCalibrate = { navController.navigate("calibration") },
            )
        }
        composable("calibration") { CalibrationScreen(onBack = { navController.popBackStack() }) }
    }
}
