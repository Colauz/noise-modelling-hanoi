package org.noisehanoi.mobile.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.noisehanoi.mobile.odk.OpenRosaClient
import org.noisehanoi.mobile.settings.Settings
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(onBack: () -> Unit, onCalibrate: () -> Unit) {
    val context = LocalContext.current
    val settings = remember { Settings(context) }
    val scope = rememberCoroutineScope()

    var server by remember { mutableStateOf(settings.serverUrl) }
    var username by remember { mutableStateOf(settings.username) }
    var password by remember { mutableStateOf(settings.password) }
    var token by remember { mutableStateOf(settings.token) }
    var offset by remember { mutableStateOf(settings.micOffsetDb) }
    var useMeter by remember { mutableStateOf(settings.useInAppMeter) }
    var extended by remember { mutableStateOf(settings.extendedForm) }
    var publicMode by remember { mutableStateOf(settings.publicMode) }
    var check by remember { mutableStateOf<String?>(null) }
    var deployed by remember { mutableStateOf(settings.deployedFormNames()) }
    var fetch by remember { mutableStateOf<String?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings") },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
            )
        },
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(16.dp).verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("KoboToolbox server", style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(
                value = server,
                onValueChange = { server = it; settings.serverUrl = it },
                label = { Text("Server URL") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = username,
                onValueChange = { username = it; settings.username = it },
                label = { Text("Kobo username (blank = POST to /submission)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = password,
                onValueChange = { password = it; settings.password = it },
                label = { Text("Password (blank = anonymous)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = token,
                onValueChange = { token = it; settings.token = it },
                label = { Text("API token (used instead of the password)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Text(
                "Anonymous submission works only if the receiving account has `require_auth` turned " +
                    "off. That is what a publicly distributed APK needs, and it is also what makes " +
                    "the endpoint open to anyone who finds it.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Button(onClick = {
                    check = "Checking…"
                    scope.launch {
                        val outcome = withContext(Dispatchers.IO) {
                            OpenRosaClient().checkConnection(settings.openRosaConfig())
                        }
                        check = when (outcome) {
                            is OpenRosaClient.Outcome.Accepted ->
                                "Reachable, form list returned ${outcome.code}"
                            is OpenRosaClient.Outcome.Rejected -> when (outcome.code) {
                                401, 403 ->
                                    "Reached the server, which wants credentials. Fill them in, or " +
                                        "turn require_auth off on the receiving account for anonymous " +
                                        "submission."
                                404 ->
                                    "Reached the server, but there is no form list at that path. " +
                                        "Check the URL and the username."
                                else -> "Refused: HTTP ${outcome.code} ${outcome.message}"
                            }
                            is OpenRosaClient.Outcome.Retryable -> "Unreachable: ${outcome.message}"
                        }
                    }
                }) { Text("Test connection") }
                check?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
            }

            Text("Deployed forms", style = MaterialTheme.typography.titleMedium)
            Button(
                onClick = {
                    fetch = "Reading the form list…"
                    scope.launch {
                        val result = withContext(Dispatchers.IO) {
                            OpenRosaClient().formList(settings.openRosaConfig())
                        }
                        fetch = result.fold(
                            onSuccess = { forms ->
                                settings.rememberDeployedForms(forms)
                                deployed = settings.deployedFormNames()
                                if (forms.isEmpty()) {
                                    "The server listed no forms. Is one deployed on this account?"
                                } else {
                                    forms.joinToString("\n") { "${it.name} → ${it.formId} (v${it.version})" }
                                }
                            },
                            onFailure = { "Could not read the form list: ${it.message}" },
                        )
                    }
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Fetch the deployed forms") }

            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        "Kobo assigns its own form identifier on deployment; a submission must " +
                            "name it. Once per account, and after each redeployment.",
                        style = MaterialTheme.typography.bodySmall,
                    )
                    fetch?.let {
                        Text(
                            it,
                            style = MaterialTheme.typography.bodySmall,
                            fontFamily = FontFamily.Monospace,
                        )
                    }
                    if (deployed.isEmpty()) {
                        Text(
                            "No form list read yet. Submissions will be refused until this is done.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error,
                        )
                    }
                }
            }

            Text("Who is collecting", style = MaterialTheme.typography.titleMedium)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Switch(checked = publicMode, onCheckedChange = { publicMode = it; settings.publicMode = it })
                Text(
                    if (publicMode) "Public contributor" else "One of the three named collectors",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        "In public mode the form stops asking you to pick a name from the campaign " +
                            "team, and files the measurement under \"public\". Alongside it goes the " +
                            "identifier below.",
                        style = MaterialTheme.typography.bodySmall,
                    )
                    Text(
                        settings.contributorId,
                        style = MaterialTheme.typography.bodySmall,
                        fontFamily = FontFamily.Monospace,
                    )
                    Text(
                        "Random, made up on first run. Not a device id, not a name, and never " +
                            "published.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline,
                    )
                    if (publicMode && !extended) {
                        Text(
                            "Public mode needs the v3 form deployed on Kobo — the \"public\" choice " +
                                "and the contributor field only exist there. Turn on the form-version " +
                                "switch below once it is.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error,
                        )
                    }
                }
            }

            Text("Microphone", style = MaterialTheme.typography.titleMedium)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Switch(checked = useMeter, onCheckedChange = { useMeter = it; settings.useInAppMeter = it })
                Text(
                    if (useMeter) "Measure with this phone's microphone" else "Type the level from a separate meter app",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Text(
                String.format(Locale.US, "Offset: %.1f dB", offset),
                style = MaterialTheme.typography.bodyMedium,
            )
            Slider(
                value = offset,
                onValueChange = { offset = it; settings.micOffsetDb = it },
                valueRange = Settings.OFFSET_RANGE,
                modifier = Modifier.fillMaxWidth(),
            )
            Button(onClick = onCalibrate, modifier = Modifier.fillMaxWidth()) {
                Text("Calibrate against a reference")
            }
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        "The entire absolute calibration of this handset, in one number. The default " +
                            "is a plausible constant for a consumer phone, not a measurement. Without a " +
                            "reference instrument to set it against, levels from this app are comparable " +
                            "to each other and to nothing else — which is also the status of the " +
                            "campaign's own 363 points.",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }

            Text("Form version", style = MaterialTheme.typography.titleMedium)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Switch(checked = extended, onCheckedChange = { extended = it; settings.extendedForm = it })
                Text("Submit app-measured level and device metadata", style = MaterialTheme.typography.bodyMedium)
            }
            Text(
                "Leave off until the v3 form is deployed. Kobo validates every instance against " +
                    "the deployed form: an unknown element is a rejected submission.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline,
            )
        }
    }
}
