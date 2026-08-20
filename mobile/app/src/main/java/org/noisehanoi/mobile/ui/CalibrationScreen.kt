package org.noisehanoi.mobile.ui

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.launch
import org.noisehanoi.mobile.form.normaliseNumber
import org.noisehanoi.mobile.measure.Calibration
import org.noisehanoi.mobile.measure.SplMeter
import org.noisehanoi.mobile.settings.Settings
import java.io.File
import java.util.Locale

/**
 * The screen that turns the arbitrary offset into a number tied to something.
 *
 * Measure alongside a reference, type what the reference read, repeat. The
 * arithmetic is in [Calibration]; this is the part that stands in the street.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CalibrationScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val settings = remember { Settings(context) }
    val scope = rememberCoroutineScope()

    val attempts = remember { mutableStateListOf<Calibration.Attempt>() }
    var running by remember { mutableStateOf(false) }
    var elapsed by remember { mutableStateOf(0.0) }
    var measured by remember { mutableStateOf<Double?>(null) }
    var reference by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var applied by remember { mutableStateOf<String?>(null) }

    // The offset the pairs below were measured with. Re-read after applying, so
    // the screen never computes from a baseline that has since moved.
    var startOffset by remember { mutableStateOf(settings.micOffsetDb.toDouble()) }
    val result = Calibration.combine(startOffset, attempts.toList())

    fun measureOnce() {
        if (running) return
        running = true
        error = null
        measured = null
        scope.launch {
            val raw = File(context.cacheDir, "calibration.pcm")
            try {
                var last: SplMeter.Reading? = null
                SplMeter(context).measure(raw, startOffset, SplMeter.WINDOW_SECONDS)
                    .catch { error = it.message ?: "Microphone unavailable" }
                    .collect { reading ->
                        last = reading
                        elapsed = reading.elapsedSeconds
                    }
                measured = last?.leqDb
                if (last == null && error == null) error = "No audio captured"
            } finally {
                raw.delete()
                running = false
            }
        }
    }

    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted -> if (granted) measureOnce() else error = "Microphone permission refused." }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Calibrate against a reference") },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
            )
        },
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(16.dp).verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Card(
                Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
            ) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("How to do this", style = MaterialTheme.typography.titleSmall)
                    Text(
                        "Put this phone and the reference side by side, facing the same way, in a " +
                            "spot that is not changing much — a steady street, not a junction with " +
                            "horn bursts. Start a measurement here, read the reference over the same " +
                            "25 s, and type what it said. Do it three times in different places.",
                        style = MaterialTheme.typography.bodySmall,
                    )
                    Text(
                        "Against a class 1 or 2 sound level meter this makes the app absolute. " +
                            "Against Decibel X on the campaign's phones it does not — those were " +
                            "trimmed to each other and to no standard — but it puts new points on " +
                            "the same scale as the existing 363, which is what lets them be used " +
                            "together at all.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline,
                    )
                }
            }

            if (running) {
                Text(
                    String.format(Locale.US, "Measuring… %.0f of %.0f s", elapsed, SplMeter.WINDOW_SECONDS),
                    style = MaterialTheme.typography.bodyMedium,
                )
                LinearProgressIndicator(
                    progress = { (elapsed / SplMeter.WINDOW_SECONDS).coerceIn(0.0, 1.0).toFloat() },
                    modifier = Modifier.fillMaxWidth(),
                )
            }

            error?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }

            measured?.let { m ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(
                            String.format(Locale.US, "This phone read %.1f dB", m),
                            style = MaterialTheme.typography.titleSmall,
                        )
                        OutlinedTextField(
                            value = reference,
                            onValueChange = { reference = normaliseNumber(it) },
                            label = { Text("What the reference read (dB)") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                            modifier = Modifier.fillMaxWidth(),
                        )
                        Button(
                            onClick = {
                                reference.toDoubleOrNull()?.let {
                                    attempts += Calibration.Attempt(m, it)
                                    reference = ""
                                    measured = null
                                }
                            },
                            enabled = reference.toDoubleOrNull() != null,
                        ) { Text("Record this pair") }
                    }
                }
            }

            Button(
                onClick = { permission.launch(Manifest.permission.RECORD_AUDIO) },
                enabled = !running,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(if (attempts.isEmpty()) "Measure" else "Measure again") }

            if (attempts.isNotEmpty()) {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Pairs recorded", style = MaterialTheme.typography.titleSmall)
                        attempts.forEachIndexed { i, a ->
                            Row(
                                Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Text(
                                    String.format(
                                        Locale.US, "%d. app %.1f, reference %.1f — %+.1f dB",
                                        i + 1, a.measuredDb, a.referenceDb, a.difference,
                                    ),
                                    style = MaterialTheme.typography.bodySmall,
                                    modifier = Modifier.weight(1f),
                                )
                                // One mistyped reference used to mean starting over.
                                TextButton(onClick = { attempts.removeAt(i) }) { Text("Remove") }
                            }
                        }
                    }
                }
            }

            result?.let { r ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        val plausible = r.offsetDb.toFloat() in Settings.OFFSET_RANGE
                        Text(
                            String.format(Locale.US, "New offset: %.1f dB", r.offsetDb),
                            style = MaterialTheme.typography.titleMedium,
                            color = if (plausible) {
                                MaterialTheme.colorScheme.onSurface
                            } else {
                                MaterialTheme.colorScheme.error
                            },
                        )
                        if (!plausible) {
                            Text(
                                String.format(
                                    Locale.US,
                                    "Outside %.0f–%.0f dB, which no handset needs. The two devices " +
                                        "were almost certainly not measuring the same sound — a " +
                                        "phone indoors and a reference outdoors, or one of them not " +
                                        "running yet.",
                                    Settings.OFFSET_RANGE.start, Settings.OFFSET_RANGE.endInclusive,
                                ),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.error,
                            )
                        }
                        Text(
                            if (r.attempts < 2) {
                                "One pair. Traffic noise moves several decibels between one 25 s " +
                                    "window and the next, so a single agreement can be luck. Do it " +
                                    "at least twice more."
                            } else {
                                String.format(
                                    Locale.US,
                                    "%d pairs, spread %.1f dB. %s",
                                    r.attempts, r.spreadDb,
                                    if (r.agrees) {
                                        "That is as close as the campaign's own three phones were " +
                                            "trimmed to each other."
                                    } else {
                                        "More than a decibel apart: these pairs are not describing " +
                                            "one constant. Try again somewhere steadier."
                                    },
                                )
                            },
                            style = MaterialTheme.typography.bodySmall,
                            color = if (r.attempts >= 2 && !r.agrees) {
                                MaterialTheme.colorScheme.error
                            } else {
                                MaterialTheme.colorScheme.outline
                            },
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(enabled = plausible, onClick = {
                                settings.micOffsetDb = r.offsetDb.toFloat()
                                // The pairs described the old baseline; keeping them
                                // would compound one correction onto another.
                                attempts.clear()
                                startOffset = settings.micOffsetDb.toDouble()
                                applied = if (r.offsetDb.toFloat() in Settings.OFFSET_RANGE) {
                                    String.format(Locale.US, "Applied: %.1f dB", r.offsetDb)
                                } else {
                                    String.format(
                                        Locale.US,
                                        "Applied, clamped to %.1f dB. A result this far out usually " +
                                            "means the two devices were not measuring the same sound.",
                                        settings.micOffsetDb,
                                    )
                                }
                            }) { Text("Apply this offset") }
                            OutlinedButton(onClick = { attempts.clear(); applied = null }) { Text("Start over") }
                        }
                        applied?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                    }
                }
            }
        }
    }
}
