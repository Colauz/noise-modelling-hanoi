package org.noisehanoi.mobile.ui

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.shape.RoundedCornerShape
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.coroutines.withContext
import org.noisehanoi.mobile.location.GpsFixes
import org.noisehanoi.mobile.study.GridCell
import org.noisehanoi.mobile.study.NoiseMap
import org.noisehanoi.mobile.study.Scenario
import org.noisehanoi.mobile.study.StudyData
import org.noisehanoi.mobile.study.metresBetween
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun MapScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    var data by remember { mutableStateOf<StudyData?>(null) }
    LaunchedEffect(Unit) {
        data = withContext(Dispatchers.IO) { StudyData.load(context) }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Predicted noise map") },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
            )
        },
    ) { padding ->
        val study = data
        if (study == null) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
            return@Scaffold
        }

        var site by remember { mutableStateOf(study.map.sites.first()) }
        var hour by remember { mutableStateOf(17) }
        var multiplier by remember { mutableStateOf(1f) }
        var showMeasured by remember { mutableStateOf(true) }
        var picked by remember { mutableStateOf<GridCell?>(null) }

        val cells = remember(site, study) { study.map.cellsOf(site) }
        // The zone's own ambience at this hour, not a constant: it is what the
        // traffic multiplier must leave alone.
        val ambient = remember(site, hour, study) { study.map.ambientEnergyOf(site, hour) }
        val extent = remember(site, study) { study.map.extentOf(site) }
        val points = remember(site, study) { study.measurements.filter { it.site == site } }

        Column(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                study.map.sites.forEach { s ->
                    FilterChip(
                        selected = s == site,
                        onClick = { site = s; picked = null },
                        label = { Text(s) },
                    )
                }
            }

            NoiseCanvas(
                cells = cells,
                points = if (showMeasured) points else emptyList(),
                extent = extent,
                hour = hour,
                multiplier = multiplier.toDouble(),
                background = ambient,
                onPick = { picked = it },
            )

            Legend()

            // No hour control, because there is nothing for it to do. The
            // delivered model is a distance kernel with no hour term, so all
            // seventeen hourly columns of the published grid are identical for
            // every one of the 5 587 cells — checked. A slider here would promise
            // a variation the study does not claim.
            Card(
                Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
            ) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("This map does not vary by hour", style = MaterialTheme.typography.titleSmall)
                    Text(
                        "The delivered model is a three-parameter distance kernel with no hour " +
                            "term, so every hour of the published grid holds the same levels. " +
                            "Traffic does vary by hour — from about 24 vehicles a minute at 21:00 " +
                            "to 76 at 17:00, measured on 147 videos — but that variation was not " +
                            "found to move the predicted level, which is one of the study's " +
                            "negative results rather than a gap in this app.",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }

            Text(
                String.format(Locale.US, "Traffic volume: x%.2f of measured", multiplier),
                style = MaterialTheme.typography.titleSmall,
            )
            Slider(
                value = multiplier,
                onValueChange = { multiplier = it },
                valueRange = Scenario.MULTIPLIER_RANGE,
            )

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { multiplier = 1f }) { Text("Reset to measured") }
                OutlinedButton(onClick = { showMeasured = !showMeasured }) {
                    Text(if (showMeasured) "Hide the 363 points" else "Show the 363 points")
                }
            }

            picked?.let { cell ->
                val base = cell.levelAt(hour)
                val scaled = Scenario.scaledLevelDb(base, multiplier.toDouble(), ambient)
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Selected cell", style = MaterialTheme.typography.titleSmall)
                        Text(
                            String.format(Locale.US, "%.5f, %.5f", cell.latitude, cell.longitude),
                            fontFamily = FontFamily.Monospace,
                            style = MaterialTheme.typography.bodySmall,
                        )
                        Text(
                            String.format(Locale.US, "%.1f dB predicted at %02d:00", base, hour),
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        if (multiplier != 1f) {
                            Text(
                                String.format(
                                    Locale.US, "%.1f dB at x%.2f traffic (%+.1f dB)",
                                    scaled, multiplier, scaled - base,
                                ),
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.primary,
                            )
                        }
                    }
                }
            }

            HereCard(study)

            ScopeNotice(multiplier)
        }
    }
}

@Composable
private fun NoiseCanvas(
    cells: List<GridCell>,
    points: List<org.noisehanoi.mobile.study.Measurement>,
    extent: org.noisehanoi.mobile.study.SiteExtent,
    hour: Int,
    multiplier: Double,
    background: Double,
    onPick: (GridCell) -> Unit,
) {
    // Equirectangular, which over an area 2 km across is indistinguishable from
    // anything better and costs no projection library.
    val latSpan = (extent.maxLatitude - extent.minLatitude).coerceAtLeast(1e-9)
    val lonSpan = (extent.maxLongitude - extent.minLongitude).coerceAtLeast(1e-9)
    val aspect = (lonSpan * kotlin.math.cos(Math.toRadians(extent.minLatitude)) / latSpan)
        .toFloat().coerceIn(0.5f, 2.0f)

    Canvas(
        Modifier
            .fillMaxWidth()
            .aspectRatio(aspect)
            .clip(RoundedCornerShape(8.dp))
            .pointerInput(cells, hour) {
                detectTapGestures { tap ->
                    val lon = extent.minLongitude + (tap.x / size.width) * lonSpan
                    val lat = extent.maxLatitude - (tap.y / size.height) * latSpan
                    cells.minByOrNull { metresBetween(lat, lon, it.latitude, it.longitude) }
                        ?.let(onPick)
                }
            }
    ) {
        drawRect(Color(0xFF12161A), size = Size(size.width, size.height))

        val cellW = (size.width * (NoiseMap.CELL_SIZE_M / (lonSpan * 111_320.0 *
            kotlin.math.cos(Math.toRadians(extent.minLatitude))))).toFloat()
        val cellH = (size.height * (NoiseMap.CELL_SIZE_M / (latSpan * 110_574.0))).toFloat()

        for (cell in cells) {
            val level = if (multiplier == 1.0) {
                cell.levelAt(hour)
            } else {
                Scenario.scaledLevelDb(cell.levelAt(hour), multiplier, background)
            }
            val x = ((cell.longitude - extent.minLongitude) / lonSpan * size.width).toFloat()
            val y = ((extent.maxLatitude - cell.latitude) / latSpan * size.height).toFloat()
            drawRect(
                color = levelColour(level),
                topLeft = Offset(x - cellW / 2, y - cellH / 2),
                size = Size(cellW.coerceAtLeast(1.5f), cellH.coerceAtLeast(1.5f)),
            )
        }

        for (point in points) {
            val x = ((point.longitude - extent.minLongitude) / lonSpan * size.width).toFloat()
            val y = ((extent.maxLatitude - point.latitude) / latSpan * size.height).toFloat()
            drawCircle(Color.White, radius = 4.5f, center = Offset(x, y))
            drawCircle(levelColour(point.levelDb), radius = 3f, center = Offset(x, y))
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Legend() {
    val bands = listOf("< 55" to 50.0, "55–65" to 60.0, "65–70" to 67.0, "70–80" to 75.0, "≥ 80" to 85.0)
    FlowRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        bands.forEach { (label, level) ->
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                Canvas(Modifier.size(12.dp)) { drawRect(levelColour(level)) }
                Text("$label dB", style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

/** "What is predicted where I am standing", with the refusal that goes with it. */
@Composable
private fun HereCard(study: StudyData) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var text by remember { mutableStateOf<String?>(null) }
    var job by remember { mutableStateOf<Job?>(null) }

    fun readHere() {
        job?.cancel()
        text = "Waiting for a fix…"
        job = scope.launch {
            val fix = withTimeoutOrNull(30_000) {
                GpsFixes.stream(context)
                    .catch { text = it.message ?: "Location unavailable" }
                    // A fix of now, not the last one the platform happens to hold.
                    .first { it.accuracyM > 0 && it.ageMillis() <= GpsFixes.STALE_AFTER_MS }
            }
            if (fix == null) {
                if (text == "Waiting for a fix…") text = "No fix within 30 s."
                return@launch
            }
            val hour = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY)
            val mapped = hour.coerceIn(NoiseMap.FIRST_HOUR, NoiseMap.LAST_HOUR)
            val nearest = study.map.nearestCell(fix.latitude, fix.longitude)
            text = if (nearest == null) {
                String.format(
                    Locale.US,
                    "You are outside the three measured areas. Nothing in this study licenses a " +
                        "prediction here, so the app does not make one. (fix %.5f, %.5f)",
                    fix.latitude, fix.longitude,
                )
            } else {
                val (cell, distance) = nearest
                String.format(
                    Locale.US,
                    "%s: %.1f dB predicted at %02d:00, %.0f m from the nearest grid cell.",
                    cell.site, cell.levelAt(mapped), mapped, distance,
                )
            }
        }
    }

    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { granted ->
        if (granted.values.any { it }) readHere() else text = "Location permission refused."
    }

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Where I am standing", style = MaterialTheme.typography.titleSmall)
            text?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
            OutlinedButton(onClick = {
                permission.launch(
                    arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
                )
            }) { Text("Read the map at my position") }
            Text(
                "Outside the three measured areas the app has no answer, and says so. " +
                    "The kernel was fitted here; it is not a model of Hanoi.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline,
            )
        }
    }
}

@Composable
private fun ScopeNotice(multiplier: Float) {
    Card(
        Modifier.fillMaxWidth().padding(bottom = 24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("How to read this", style = MaterialTheme.typography.titleSmall)
            Text(
                "Coloured cells are predicted by a three-parameter physical kernel over a 40 m grid. " +
                    "The bands are the QCVN 26:2010 references, shown descriptively — this is not a " +
                    "compliance assessment, and the levels are calibrated in relative terms only.",
                style = MaterialTheme.typography.bodySmall,
            )
            Text(
                "The dots are the 363 measurements themselves. Spatial contrast comes from distance " +
                    "to the two road classes and from nothing else: morphology aggregated over 300 m " +
                    "brought no measurable gain.",
                style = MaterialTheme.typography.bodySmall,
            )
            if (multiplier != 1f) {
                Text(
                    "The traffic multiplier scales only the traffic share of the energy, never the " +
                        "zone's residual ambience. Scaling the total is what once made the model " +
                        "claim twice the benefit for pedestrianisation that it should have. Checked " +
                        "against the GAMA model itself: the two agree within 0.2 dB.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        }
    }
}
