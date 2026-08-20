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
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import org.noisehanoi.mobile.form.FormSpec
import kotlinx.coroutines.delay
import org.noisehanoi.mobile.odk.InstanceXml
import org.noisehanoi.mobile.outbox.Outbox

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    outbox: Outbox,
    /** Set once when arriving from a submission, so the first message is immediate. */
    justSubmitted: Boolean = false,
    onSubmissionAcknowledged: () -> Unit = {},
    onOpenForm: (FormSpec) -> Unit,
    onOpenOutbox: () -> Unit,
    onOpenSettings: () -> Unit,
    onOpenMap: () -> Unit,
    onOpenResults: () -> Unit,
    /** What the server calls each form, once Settings has read the list. */
    deployedOf: (FormSpec) -> InstanceXml.Deployment? = { null },
    onOpenGama: () -> Unit = {},
    mayCollect: Boolean = true,
    onReviewConsent: () -> Unit = {},
) {
    val snackbar = remember { SnackbarHostState() }
    var counts by remember { mutableStateOf(outbox.counts()) }

    // Submission is deliberately not on the path of finishing a form -- the
    // instance is written to disk and uploaded later -- so "it worked" cannot be
    // answered at the moment of pressing send. It is answered here instead, by
    // watching the outbox until nothing is in flight.
    LaunchedEffect(justSubmitted) {
        if (justSubmitted) {
            snackbar.showSnackbar("Saved to the outbox. Sending\u2026")
            onSubmissionAcknowledged()
        }
    }
    LaunchedEffect(Unit) {
        var previous = counts
        while (true) {
            val now = outbox.counts()
            if (now != previous) {
                counts = now
                if (now.sent > previous.sent) {
                    snackbar.showSnackbar("Sent to KoboToolbox \u2014 accepted by the server.")
                } else if (now.failed > previous.failed) {
                    snackbar.showSnackbar("The server refused a submission. See the outbox.")
                }
                previous = now
            }
            // Briskly while something is in flight, idly otherwise: the only thing
            // that can change the outbox with nothing pending is the user, and
            // they are looking at this screen anyway.
            delay(if (now.pending > 0) 1_000 else 5_000)
        }
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("Noise Hanoi") }) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(16.dp).verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                "Field collection for the Hanoi urban noise campaign. Forms are the ones deployed on " +
                    "KoboToolbox; submissions go to the same server ODK Collect used.",
                style = MaterialTheme.typography.bodyMedium,
            )

            Text("Collect", style = MaterialTheme.typography.titleMedium)

            if (!mayCollect) {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Collection is off", style = MaterialTheme.typography.titleSmall)
                        Text(
                            "You have not agreed to contribute measurements. The map and the " +
                                "results below send nothing and stay available.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.outline,
                        )
                        Button(onClick = onReviewConsent) { Text("Read what would be collected") }
                    }
                }
            }

            AVAILABLE_FORMS.forEach { form ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(form.title, style = MaterialTheme.typography.titleMedium)
                        // The deployed identity when it is known, because that is
                        // what a submission actually names. Showing the
                        // spreadsheet's own id while submitting under another is
                        // the confusion that produced a 404 nobody could read.
                        val deployed = deployedOf(form)
                        Text(
                            if (deployed == null) {
                                "${form.questions.size} questions · not yet matched to a deployed form"
                            } else {
                                "${form.questions.size} questions · ${deployed.formId} · v${deployed.version}"
                            },
                            style = MaterialTheme.typography.bodySmall,
                            color = if (deployed == null) {
                                MaterialTheme.colorScheme.error
                            } else {
                                MaterialTheme.colorScheme.outline
                            },
                        )
                        Button(onClick = { onOpenForm(form) }, enabled = mayCollect) {
                            Text("Fill this form")
                        }
                    }
                }
            }

            Text("The study", style = MaterialTheme.typography.titleMedium)
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Predicted noise map", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "The 40 m grid over the three measured areas, by hour, with the 363 points " +
                            "and the simulation's traffic slider.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline,
                    )
                    Button(onClick = onOpenMap) { Text("Open the map") }
                }
            }
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("What the study found", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "The delivered model, the three negative results, and every metric read " +
                            "from metrics.json rather than retyped.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline,
                    )
                    Button(onClick = onOpenResults) { Text("Open the results") }
                }
            }

            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("GAMA simulation", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "The model itself, driven from here — mitigation scenarios, construction, " +
                            "the fleet by hour. Needs a gama-server on the network; the map above " +
                            "needs nothing.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline,
                    )
                    Button(onClick = onOpenGama) { Text("Open the simulation") }
                }
            }

            OutlinedButton(onClick = onOpenOutbox, modifier = Modifier.fillMaxWidth()) {
                Text(
                    when {
                        counts.total == 0 -> "Outbox"
                        counts.pending > 0 -> "Outbox — ${counts.pending} sending…"
                        counts.failed > 0 -> "Outbox — ${counts.failed} refused, ${counts.sent} sent"
                        else -> "Outbox — ${counts.sent} sent"
                    }
                )
            }
            OutlinedButton(onClick = onOpenSettings, modifier = Modifier.fillMaxWidth()) {
                Text("Server and microphone settings")
            }
        }
    }
}
