package org.noisehanoi.mobile.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.noisehanoi.mobile.gama.GamaClient
import org.noisehanoi.mobile.settings.Settings
import java.util.Locale

/**
 * The GAMA model itself, driven from the phone.
 *
 * This is a remote control, not a simulation running here: GAMA is a desktop
 * platform and the model executes on whatever machine answers at the server
 * address. The map screen carries a grid and computes its scenario locally, which
 * works with no network at all; this needs both a network and a server that is
 * switched on. What it buys in exchange is everything the grid cannot hold — the
 * mitigation scenarios, the construction sites, the hour-by-hour fleet — because
 * those come from the model, not from a table of levels.
 */
@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun GamaScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val settings = remember { Settings(context) }
    val client = remember { GamaClient() }
    val scope = rememberCoroutineScope()

    var serverUrl by remember { mutableStateOf(settings.gamaServerUrl) }
    var modelPath by remember { mutableStateOf(settings.gamaModelPath) }
    var status by remember { mutableStateOf("Not connected.") }
    var busy by remember { mutableStateOf(false) }
    var experimentId by remember { mutableStateOf<String?>(null) }

    var hour by remember { mutableStateOf(17f) }
    var traffic by remember { mutableStateOf(1f) }
    var mitigation by remember { mutableStateOf("none") }
    val readings = remember { mutableStateListOf<Pair<String, String>>() }
    var scene by remember { mutableStateOf(GamaClient.Scene()) }
    var playing by remember { mutableStateOf(false) }

    DisposableEffect(Unit) { onDispose { client.close() } }


    /** Re-pulls what moves: the field's levels and the vehicles. */
    fun refreshScene(exp: String) {
        scope.launch {
            val cells = withContext(Dispatchers.IO) { client.pullField(exp) }
            val vehicles = withContext(Dispatchers.IO) { client.pullVehicles(exp) }
            scene = scene.copy(cells = cells, vehicles = vehicles)
        }
    }

    fun refreshIndicators(exp: String) {
        scope.launch {
            val fresh = mutableListOf<Pair<String, String>>()
            for (indicator in GamaClient.INDICATORS) {
                when (val r = withContext(Dispatchers.IO) { client.evaluate(exp, indicator.expression) }) {
                    is GamaClient.Outcome.Ok -> fresh += indicator.name to r.content
                    is GamaClient.Outcome.Failed -> fresh += indicator.name to "— (${r.type})"
                }
            }
            readings.clear()
            readings.addAll(fresh)
        }
    }

    fun loadScenario() {
        busy = true
        // Stop the one being replaced. A slider drag is a reload, and each
        // abandoned experiment holds 2544 cells, 1075 buildings and 766 roads on
        // the server — about 15 MB apiece, measured. Sixty slider moves would be
        // a gigabyte of simulations nobody is watching.
        val previous = experimentId
        experimentId = null
        readings.clear()
        status = "Loading ${GamaClient.HEADLESS_EXPERIMENT}…"
        scope.launch {
            previous?.let { withContext(Dispatchers.IO) { client.stop(it) } }
            val outcome = withContext(Dispatchers.IO) {
                client.load(
                    modelPath = modelPath,
                    experiment = GamaClient.HEADLESS_EXPERIMENT,
                    parameters = listOf(
                        GamaClient.Parameter.Number("hour_of_day", hour.toDouble()),
                        GamaClient.Parameter.Number("traffic_multiplier", traffic.toDouble()),
                        GamaClient.Parameter.Text("mitigation", mitigation),
                    ),
                )
            }
            when (outcome) {
                is GamaClient.Outcome.Ok -> {
                    val exp = outcome.content
                    experimentId = exp
                    status = "Loaded. Drawing the zone…"
                    withContext(Dispatchers.IO) { client.step(exp) }
                    // The unmoving layers once; the rest after every step.
                    if (scene.roads.isEmpty()) {
                        // Geometry, not state: it survives a reload, and pulling
                        // 330 kB again on every slider release would be the whole
                        // cost of the interaction.
                        scene = withContext(Dispatchers.IO) { client.pullStatic(exp) }
                    }
                    refreshScene(exp)
                    refreshIndicators(exp)
                    // A slider change is a reload, and a reload is a new
                    // experiment: without this, moving a slider silently stops a
                    // running simulation and the button still says Pause.
                    if (playing) withContext(Dispatchers.IO) { client.play(exp) }
                    status = "Running. Experiment $exp."
                }
                is GamaClient.Outcome.Failed ->
                    status = "Load refused (${outcome.type}): ${outcome.detail.take(200)}"
            }
            busy = false
        }
    }

    // While the model runs, only the vehicles and the counters move: the noise
    // field is a function of hour, traffic and mitigation, and none of those
    // change on their own. Re-pulling 98 kB of grid four times a second to redraw
    // an identical picture would be waste, so play animates the vehicles alone.
    LaunchedEffect(playing, experimentId) {
        val exp = experimentId ?: return@LaunchedEffect
        while (playing) {
            val vehicles = withContext(Dispatchers.IO) { client.pullVehicles(exp) }
            scene = scene.copy(vehicles = vehicles)
            refreshIndicators(exp)
            delay(400)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("GAMA simulation") },
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
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("What this is", style = MaterialTheme.typography.titleSmall)
                    Text(
                        "The model runs on another machine, started with " +
                            "gama-headless.sh -socket 6868. Needs a network and a running server.",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }

            OutlinedTextField(
                value = serverUrl,
                onValueChange = { serverUrl = it; settings.gamaServerUrl = it },
                label = { Text("Server (ws://host:port)") },
                supportingText = {
                    Text(
                        "Its address on the wifi, not localhost.",
                        style = MaterialTheme.typography.bodySmall,
                    )
                },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = modelPath,
                onValueChange = { modelPath = it; settings.gamaModelPath = it },
                label = { Text("Model path, on the server") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Button(
                    enabled = !busy && serverUrl.isNotBlank(),
                    onClick = {
                        busy = true
                        status = "Connecting…"
                        scope.launch {
                            val result = withContext(Dispatchers.IO) { client.connect(serverUrl) }
                            status = result.fold(
                                onSuccess = { "Connected to $serverUrl." },
                                onFailure = { "Could not connect: ${it.message}" },
                            )
                            busy = false
                        }
                    },
                ) { Text(if (client.isConnected) "Reconnect" else "Connect") }

                OutlinedButton(enabled = !busy && client.isConnected, onClick = ::loadScenario) {
                    Text("Run scenario")
                }
                if (busy) CircularProgressIndicator(Modifier.padding(4.dp))
            }

            Text(
                if (serverUrl.isBlank()) {
                    "Enter the address of the machine running gama-server, then connect."
                } else {
                    status
                },
                style = MaterialTheme.typography.bodySmall,
                fontFamily = FontFamily.Monospace,
            )

            HorizontalDivider()

            Text(String.format(Locale.US, "Hour of day: %02d:00", hour.toInt()),
                style = MaterialTheme.typography.titleSmall)
            Text(
                "Changes the traffic and the construction, not the predicted field.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline,
            )
            Slider(
                value = hour,
                onValueChange = { hour = it },
                // On release, not on every pixel: each change is a reload, and a
                // drag would otherwise queue a hundred of them.
                onValueChangeFinished = { if (client.isConnected) loadScenario() },
                valueRange = 5f..21f,
                steps = 15,
            )

            Text(String.format(Locale.US, "Traffic: x%.2f of observed", traffic),
                style = MaterialTheme.typography.titleSmall)
            Slider(
                value = traffic,
                onValueChange = { traffic = it },
                onValueChangeFinished = { if (client.isConnected) loadScenario() },
                valueRange = 0.2f..3f,
            )

            Text("Mitigation", style = MaterialTheme.typography.titleSmall)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("none" to "None", "zone 30" to "Zone 30", "pietonnisation" to "Pedestrianised")
                    .forEach { (value, label) ->
                        FilterChip(
                            selected = mitigation == value,
                            // Mitigation is a parameter, so changing it re-runs the
                            // scenario rather than nudging a running one.
                            onClick = {
                                mitigation = value
                                if (client.isConnected) loadScenario()
                            },
                            label = { Text(label) },
                        )
                    }
            }

            experimentId?.let { exp ->
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = {
                        scope.launch {
                            playing = !playing
                            withContext(Dispatchers.IO) {
                                if (playing) client.play(exp) else client.pause(exp)
                            }
                        }
                    }) { Text(if (playing) "Pause" else "Play") }
                    OutlinedButton(onClick = {
                        scope.launch {
                            withContext(Dispatchers.IO) { client.step(exp) }
                            refreshScene(exp)
                            refreshIndicators(exp)
                        }
                    }) { Text("Step") }
                    OutlinedButton(onClick = { refreshScene(exp); refreshIndicators(exp) }) {
                        Text("Read again")
                    }
                    OutlinedButton(onClick = {
                        scope.launch {
                            withContext(Dispatchers.IO) { client.stop(exp) }
                            playing = false
                            experimentId = null
                            readings.clear()
                            scene = GamaClient.Scene()
                            status = "Experiment stopped."
                        }
                    }) { Text("Stop") }
                }
            }

            if (!scene.isEmpty) {
                Text("The model's noise map", style = MaterialTheme.typography.titleSmall)
                GamaCanvas(scene, Modifier.fillMaxWidth())
                FlowRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    GamaPalette.legend.forEach { (label, colour) ->
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(4.dp),
                        ) {
                            Canvas(Modifier.size(12.dp)) { drawRect(colour) }
                            Text("$label dB", style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }
                Text(
                    "Drawn from the running model, layer for layer as hanoi_noise.gaml declares " +
                        "them: the 40 m grid, buildings, roads, construction sites as diamonds, " +
                        "vehicles by type, and the measured points on top.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline,
                )
            }

            if (readings.isNotEmpty()) {
                Card(Modifier.fillMaxWidth().padding(bottom = 24.dp)) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("What the model reports", style = MaterialTheme.typography.titleSmall)
                        readings.forEach { (name, value) ->
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(name, style = MaterialTheme.typography.bodySmall)
                                Text(
                                    value,
                                    style = MaterialTheme.typography.bodySmall,
                                    fontFamily = FontFamily.Monospace,
                                )
                            }
                        }
                        Text(
                            "Read from the running model, not from the grid this app carries. " +
                                "The two agree on the traffic scenario to within 0.2 dB.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.outline,
                        )
                    }
                }
            }
        }
    }
}
