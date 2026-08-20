package org.noisehanoi.mobile.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import org.noisehanoi.mobile.settings.Settings

/**
 * What a contributor is told before they contribute anything.
 *
 * Shown once, before the first form can be opened. Declining is a real option
 * and leaves a usable app: the map and the results collect nothing, so there is
 * no reason to withhold them from someone who would rather not submit.
 *
 * The text is specific because a general one would be worthless. It names the
 * fields that actually leave the phone, the server they land on, and the two
 * things a contributor would otherwise have no way of knowing: that a position
 * with a timestamp identifies a person even without a name, and that the levels
 * are not calibrated against anything.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConsentScreen(onAgree: () -> Unit, onDecline: () -> Unit, onBack: (() -> Unit)? = null) {
    val context = LocalContext.current
    val settings = remember { Settings(context) }
    val destination = remember {
        val user = settings.username
        if (user.isBlank()) settings.serverUrl else "${settings.serverUrl}/$user"
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Before you contribute") },
                navigationIcon = { onBack?.let { TextButton(onClick = it) { Text("Back") } } },
            )
        },
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(16.dp).verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                "This app collects urban noise measurements for a research project on Hanoi. " +
                    "Reading the map and the results sends nothing. Only submitting a form does.",
                style = MaterialTheme.typography.bodyMedium,
            )

            Section(
                "What a submission contains",
                "The sound level, the time, and your position with its accuracy. Your answers on " +
                    "the form. Your phone's model, its Android version, the app version, and a " +
                    "random number this phone invented on first run.",
            )
            Section(
                "The random number, and why it is there",
                "Not a device identifier, not an account, not a name. It exists so the project " +
                    "can tell one contributor's measurements from another's. You can see it in " +
                    "Settings.",
            )
            Section(
                "Your position is personal data, even without your name",
                "A position with a time says where somebody was at a moment. Measuring repeatedly " +
                    "from the same place — your home — says where you live. Measure where you " +
                    "would not mind being recorded as having stood.",
            )
            Section(
                "Sound recording",
                "In public contributor mode no recording is made at all. A short clip is " +
                    "submitted only when the app is set up for the campaign team.",
            )
            Section(
                "Where it goes, and who holds it",
                "Submissions are sent to a KoboToolbox project. Whoever owns that account holds " +
                    "the data and answers for it. This build sends to:",
            )
            Text(
                destination,
                style = MaterialTheme.typography.bodySmall,
                fontFamily = FontFamily.Monospace,
            )
            Section(
                "Changing your mind",
                "Stop at any time by not submitting. To have sent measurements removed, contact " +
                    "whoever runs the project with the random number from Settings — the only " +
                    "thing that points at your submissions.",
            )
            Section(
                "What the numbers are worth",
                "A phone microphone is not a sound level meter. Unless this phone has been " +
                    "calibrated against a reference, its decibels are comparable to each other and " +
                    "to nothing else, and are not a compliance measurement.",
            )

            Button(onClick = onAgree, modifier = Modifier.fillMaxWidth()) {
                Text("I understand — let me contribute")
            }
            TextButton(onClick = onDecline, modifier = Modifier.fillMaxWidth()) {
                Text("Not now — just show me the study")
            }
            Text(
                "Declining leaves the map and the results available. Nothing is sent either way " +
                    "until you submit a form.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline,
                modifier = Modifier.padding(bottom = 24.dp),
            )
        }
    }
}

@Composable
private fun Section(title: String, body: String) {
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Text(body, style = MaterialTheme.typography.bodySmall)
        }
    }
}
