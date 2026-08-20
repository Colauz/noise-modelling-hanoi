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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
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
import androidx.core.content.FileProvider
import kotlinx.coroutines.launch
import androidx.lifecycle.viewmodel.compose.viewModel
import org.noisehanoi.mobile.form.CONSTRUCTION_FORM_V1
import org.noisehanoi.mobile.form.DecimalQ
import org.noisehanoi.mobile.form.FormSpec
import org.noisehanoi.mobile.form.GeoPointQ
import org.noisehanoi.mobile.form.IntegerQ
import org.noisehanoi.mobile.form.MediaKind
import org.noisehanoi.mobile.form.MediaQ
import org.noisehanoi.mobile.form.NOISE_FORM_V2
import org.noisehanoi.mobile.form.PUBLIC_COLLECTOR
import org.noisehanoi.mobile.form.SelectOneQ
import org.noisehanoi.mobile.form.TextQ
import org.noisehanoi.mobile.form.normaliseNumber
import org.noisehanoi.mobile.location.GpsFixes
import org.noisehanoi.mobile.location.Sites
import org.noisehanoi.mobile.measure.SplMeter
import java.io.File
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FormScreen(spec: FormSpec, onDone: () -> Unit, onBack: () -> Unit) {
    val model: FormViewModel = viewModel()
    LaunchedEffect(spec.id) { model.start(spec) }

    val answers by model.answers.collectAsState()
    val gps by model.gps.collectAsState()
    val meter by model.meter.collectAsState()
    val submitted by model.submitted.collectAsState()

    LaunchedEffect(submitted) { if (submitted != null) onDone() }

    var showProblems by remember { mutableStateOf(false) }
    val problems = if (showProblems) model.problems() else emptyMap()
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(spec.title) },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
            )
        },
    ) { padding ->
        val current = answers
        if (current == null) {
            Text("Saved", Modifier.padding(padding).padding(24.dp))
            return@Scaffold
        }

        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            item { MetrologyNotice(model) }

            for (question in spec.questions) {
                item(key = question.name) {
                    val value = current[question.name]
                    val problem = problems[question.name]
                    when (question) {
                        is GeoPointQ -> GpsCard(question.label, gps, model)
                        is MediaQ -> when (question.kind) {
                            MediaKind.AUDIO -> MeterCard(meter, value, problem, model)
                            MediaKind.IMAGE ->
                                PhotoCard(question.label, value, problem, model, question.name)
                        }
                        is SelectOneQ -> SelectOneField(
                            visibleChoices(question, model), value, problem,
                        ) { model.set(question.name, it) }
                        is DecimalQ -> {
                            val wording = levelWording(question, model)
                            NumberField(
                                question, value, problem, decimal = true,
                                labelOverride = wording?.first,
                                hintOverride = wording?.second,
                            ) { model.set(question.name, normaliseNumber(it)) }
                        }
                        is IntegerQ -> NumberField(question, value, problem, decimal = false) {
                            model.set(question.name, normaliseNumber(it))
                        }
                        is TextQ -> FreeTextField(question, value, problem) { model.set(question.name, it) }
                    }
                }
            }

            item {
                Column(Modifier.padding(vertical = 20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (showProblems && problems.isNotEmpty()) {
                        // Naming them, because "1 answer still missing" on a sixteen
                        // question form sends the user hunting, standing in traffic,
                        // for the one chip a thumb missed.
                        val named = spec.questions
                            .filter { it.name in problems }
                            .joinToString(", ") { it.label }
                        Text(
                            "Still to fix: $named",
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    }
                    Button(
                        onClick = {
                            showProblems = true
                            model.submit()
                            val first = spec.questions.indexOfFirst { it.name in model.problems() }
                            if (first >= 0) {
                                // +1 for the notice that heads the list.
                                scope.launch { listState.animateScrollToItem(first + 1) }
                            }
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Save to outbox and send") }
                    Text(
                        "Written to the phone first, uploaded when there is a network.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline,
                    )
                }
            }
        }
    }
}

/**
 * In public mode the collector question stops listing the team.
 *
 * Three first names is the right list for the people who ran the campaign and an
 * odd thing to show a stranger, who would have to file their measurement under
 * someone else's name. The field itself stays — the pipeline keys de-duplication
 * and the per-collector offset on it — but the only choice offered is the one
 * that is true.
 */
private fun visibleChoices(question: SelectOneQ, model: FormViewModel): SelectOneQ =
    if (question.name == "collector" && model.settings.publicMode) {
        question.copy(choices = question.choices.filter { it.name == PUBLIC_COLLECTOR })
    } else {
        question
    }

/**
 * The v2 wording — "from sound meter app", "Read LAeq / average value from the dB
 * app" — is what the field protocol asked of the three campaign handsets. With
 * the in-app meter on it is the app that fills the field, and text telling the
 * user to read another application describes something that is not happening.
 * Label and hint move together: overriding one and leaving the other is how a
 * screen ends up contradicting itself.
 */
private fun levelWording(question: DecimalQ, model: FormViewModel): Pair<String, String>? =
    if (question.name == "noise_db" && model.settings.useInAppMeter) {
        "Noise level (dB), measured by this app" to
            "Filled by the measurement above. Override it if you are reading a meter instead."
    } else {
        null
    }

@Composable
private fun MetrologyNotice(model: FormViewModel) {
    Card(
        Modifier.fillMaxWidth().padding(vertical = 12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("What this records", style = MaterialTheme.typography.titleSmall)
            Text(
                if (model.settings.useInAppMeter) {
                    "A 25 s A-weighted level from this phone's microphone, uncalibrated in absolute " +
                        "terms. Usable for contrasts between places and hours, not as a compliance figure."
                } else {
                    "A level read from a separate sound meter app, as the protocol specifies."
                },
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun GpsCard(label: String, gps: FormViewModel.GpsState, model: FormViewModel) {
    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { granted -> if (granted.values.any { it }) model.startGps() else model.locationRefused() }

    Card(Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(label, style = MaterialTheme.typography.titleSmall)

            val point = gps.point
            if (point == null) {
                Text(
                    gps.error ?: "No fix yet.",
                    style = MaterialTheme.typography.bodySmall,
                    color = if (gps.error != null) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.outline,
                )
            } else {
                Text(
                    String.format(Locale.US, "%.6f, %.6f", point.latitude, point.longitude),
                    fontFamily = FontFamily.Monospace,
                    style = MaterialTheme.typography.bodyMedium,
                )
                val ok = gps.accurateEnough
                Text(
                    String.format(
                        Locale.US, "accuracy %.1f m — %s", point.accuracyM,
                        if (ok) "within the protocol's 10 m" else "wait, the protocol asks for under 10 m",
                    ),
                    style = MaterialTheme.typography.bodySmall,
                    color = if (ok) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                )
                model.siteContext()?.let { (site, distance) ->
                    Text(
                        if (distance <= Sites.SITE_RADIUS_M) {
                            String.format(Locale.US, "%.0f m from the %s centre", distance, site.label)
                        } else {
                            String.format(
                                Locale.US,
                                "%.1f km from the nearest measured site (%s) — outside every campaign area",
                                distance / 1000.0, site.label,
                            )
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline,
                    )
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                OutlinedButton(onClick = {
                    permission.launch(
                        arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
                    )
                }) { Text(if (gps.searching) "Searching…" else "Get fix") }

                Button(onClick = model::acceptFix, enabled = gps.point != null) {
                    Text(if (gps.accurateEnough) "Use this fix" else "Use anyway")
                }
            }
            if (gps.point != null && !gps.accurateEnough) {
                Text(
                    "The campaign's worst fix was 9.0 m. Accepting a looser one weakens the " +
                        "argument for this point.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline,
                )
            }
        }
    }
}

@Composable
private fun MeterCard(
    meter: FormViewModel.MeterState,
    attached: String?,
    problem: String?,
    model: FormViewModel,
) {
    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted -> if (granted) model.startMeasurement() else model.microphoneRefused() }

    Card(Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            val keepsClip = !model.settings.publicMode
            Text(
                if (keepsClip) "Measurement and audio clip" else "Measurement",
                style = MaterialTheme.typography.titleSmall,
            )
            Text(
                if (keepsClip) {
                    "One microphone session: ${SplMeter.WINDOW_SECONDS.toInt()} s, A-weighted, " +
                        "SLOW. The clip is the stretch that was measured."
                } else {
                    "${SplMeter.WINDOW_SECONDS.toInt()} s, A-weighted, SLOW. The level is kept, " +
                        "the recording is not."
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline,
            )

            if (meter.running || meter.finishedLeqDb != null) {
                Text(
                    String.format(Locale.US, "%.1f dB", if (meter.running) meter.slowDb else meter.leqDb),
                    style = MaterialTheme.typography.displaySmall,
                    color = levelColour(if (meter.running) meter.slowDb else meter.leqDb),
                )
                Text(
                    String.format(
                        Locale.US, "L_eq %.1f dB over %.0f s", meter.leqDb, meter.elapsed,
                    ),
                    style = MaterialTheme.typography.bodySmall,
                )
                LinearProgressIndicator(
                    progress = { (meter.elapsed / SplMeter.WINDOW_SECONDS).coerceIn(0.0, 1.0).toFloat() },
                    modifier = Modifier.fillMaxWidth(),
                )
                if (meter.clippedFraction > 0) {
                    Text(
                        String.format(
                            Locale.US,
                            "%.2f %% of samples hit full scale — the level is a floor, not a reading",
                            meter.clippedFraction * 100,
                        ),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }

            meter.error?.let {
                Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
            }
            // The card is the only place the clip can be produced, so it is the
            // only place saying it is missing is any use. Naming the button rather
            // than the field, because "Audio recording — Required" tells someone
            // standing in traffic nothing about what to press.
            problem?.let {
                Text(
                    "Required: press Measure below to record the clip.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
            attached?.let {
                Text("Clip attached: $it", style = MaterialTheme.typography.bodySmall)
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = { permission.launch(Manifest.permission.RECORD_AUDIO) },
                    enabled = !meter.running,
                ) { Text(if (meter.finishedLeqDb != null) "Measure again" else "Measure ${SplMeter.WINDOW_SECONDS.toInt()} s") }
                if (meter.running) {
                    OutlinedButton(onClick = model::stopMeasurement) { Text("Stop") }
                }
            }
        }
    }
}

@Composable
private fun PhotoCard(
    label: String,
    attached: String?,
    problem: String?,
    model: FormViewModel,
    fieldName: String,
) {
    val context = LocalContext.current
    var target by remember { mutableStateOf<File?>(null) }
    val takePicture = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { ok ->
        val file = target
        if (ok && file != null) model.attachFile(fieldName, file)
    }
    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (!granted) return@rememberLauncherForActivityResult
        val file = model.photoTarget(fieldName)
        target = file
        takePicture.launch(
            FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
        )
    }

    Card(Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(label, style = MaterialTheme.typography.titleSmall)
            problem?.let {
                Text(
                    "Required: take the photo below.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
            attached?.let { Text("Attached: $it", style = MaterialTheme.typography.bodySmall) }
            OutlinedButton(onClick = { permission.launch(Manifest.permission.CAMERA) }) {
                Text(if (attached == null) "Take photo" else "Replace photo")
            }
        }
    }
}

/** The two forms, for the home screen. */
val AVAILABLE_FORMS = listOf(NOISE_FORM_V2, CONSTRUCTION_FORM_V1)
