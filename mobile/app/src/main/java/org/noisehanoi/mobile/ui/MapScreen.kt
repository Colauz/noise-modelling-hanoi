package org.noisehanoi.mobile.ui

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
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
import androidx.compose.material3.LinearProgressIndicator
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
import androidx.compose.runtime.mutableStateListOf
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
import androidx.compose.ui.graphics.drawscope.scale
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.shape.RoundedCornerShape
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.filter
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.coroutines.withContext
import org.noisehanoi.mobile.form.GeoPoint
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
        // Pan and zoom, because 2 km across at 40 m a cell is unreadable held
        // still on a phone. Kept in the projected plane rather than a tile
        // framework: the area is 5 587 rectangles, so panning is a translation of
        // the draw and needs neither tiles nor a network.
        var zoom by remember(site) { mutableStateOf(1f) }
        var pan by remember(site) { mutableStateOf(Offset.Zero) }

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

            HereCard(study)

            NoiseCanvas(
                cells = cells,
                points = if (showMeasured) points else emptyList(),
                extent = extent,
                hour = hour,
                multiplier = multiplier.toDouble(),
                background = ambient,
                zoom = zoom,
                pan = pan,
                onTransform = { z, p ->
                    zoom = z
                    // Never let the map be pushed off its own frame and lost.
                    val limit = 2_000f * (z - 1f)
                    pan = Offset(p.x.coerceIn(-limit, limit), p.y.coerceIn(-limit, limit))
                },
                onPick = { picked = it },
            )

            // Gestures work, and a thumb on a scrolling page does not always get
            // them: the parent scroll takes the drag first. These always work.
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { zoom = (zoom * 1.6f).coerceAtMost(12f) }) { Text("Zoom in") }
                OutlinedButton(onClick = {
                    zoom = (zoom / 1.6f).coerceAtLeast(1f)
                    val limit = 2_000f * (zoom - 1f)
                    pan = Offset(pan.x.coerceIn(-limit, limit), pan.y.coerceIn(-limit, limit))
                }) { Text("Zoom out") }
                if (zoom > 1f || pan != Offset.Zero) {
                    OutlinedButton(onClick = { zoom = 1f; pan = Offset.Zero }) { Text("Reset") }
                }
            }
            if (zoom > 1f) {
                Text(
                    String.format(Locale.US, "x%.1f", zoom),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline,
                )
            }

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
                    Text(
                        "No hour control: the delivered model has no hour term.",
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
    zoom: Float,
    pan: Offset,
    onTransform: (Float, Offset) -> Unit,
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
            .pointerInput(extent) {
                detectTransformGestures { _, drag, gestureZoom, _ ->
                    val next = (zoom * gestureZoom).coerceIn(1f, 12f)
                    val scaled = if (zoom == 0f) Offset.Zero else pan * (next / zoom)
                    onTransform(next, scaled + drag * next)
                }
            }
            .pointerInput(cells, zoom, pan) {
                detectTapGestures { tap ->
                    // Undo the view transform before asking which cell was touched.
                    val cx = size.width / 2f
                    val cy = size.height / 2f
                    val x = (tap.x - cx - pan.x) / zoom + cx
                    val y = (tap.y - cy - pan.y) / zoom + cy
                    val lon = extent.minLongitude + (x / size.width) * lonSpan
                    val lat = extent.maxLatitude - (y / size.height) * latSpan
                    cells.minByOrNull { metresBetween(lat, lon, it.latitude, it.longitude) }
                        ?.let(onPick)
                }
            }
    ) {
      withTransform({
          translate(pan.x, pan.y)
          scale(zoom, zoom, pivot = Offset(size.width / 2f, size.height / 2f))
      }) {
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
            drawCircle(Color.White, radius = 4.5f / zoom, center = Offset(x, y))
            drawCircle(levelColour(point.levelDb), radius = 3f / zoom, center = Offset(x, y))
        }
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

/**
 * The predicted level where the phone is standing.
 *
 * Two things it does not do, and both are the point. It does not take the first
 * fix the platform offers: that can be a network fix tens of metres wide, and on a
 * 40 m grid a 50 m fix chooses the cell at random. It listens for a while, keeps
 * the best, and says how good it was. And it does not answer outside the three
 * measured areas.
 *
 * No hour is reported either, because the delivered model has no hour term and
 * saying "at 17:00" would imply one.
 */
@Composable
private fun HereCard(study: StudyData) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var reading by remember { mutableStateOf<String?>(null) }
    var level by remember { mutableStateOf<Double?>(null) }
    var siteName by remember { mutableStateOf<String?>(null) }
    var searching by remember { mutableStateOf(false) }
    var best by remember { mutableStateOf<GeoPoint?>(null) }
    val collected = remember { mutableStateListOf<GeoPoint>() }
    var job by remember { mutableStateOf<Job?>(null) }

    fun readHere() {
        job?.cancel()
        searching = true
        best = null
        collected.clear()
        reading = null
        level = null
        siteName = null
        job = scope.launch {
            // Keep listening past the first good fix: several of them averaged
            // land closer to the truth than any one of them. `first` ends the flow
            // once there are enough; the timeout ends it otherwise. Throwing to
            // break out would cancel this coroutine whole, and the answer below
            // would never be written.
            withTimeoutOrNull(SEARCH_MS) {
                GpsFixes.stream(context)
                    .catch { reading = it.message ?: "Location unavailable" }
                    .filter { it.accuracyM > 0 && it.ageMillis() <= GpsFixes.STALE_AFTER_MS }
                    .onEach { fix ->
                        collected += fix
                        val current = best
                        if (current == null || fix.accuracyM < current.accuracyM) best = fix
                    }
                    .first { fix ->
                        fix.accuracyM <= GOOD_ENOUGH_M &&
                            collected.count { it.accuracyM <= GOOD_ENOUGH_M } >= ENOUGH_FIXES
                    }
            }
            searching = false
            val fix = GpsFixes.combine(collected.toList())
            val nearest = fix?.let { study.map.nearestCell(it.latitude, it.longitude) }
            when {
                fix == null -> reading = "No fix in ${SEARCH_MS / 1000} s. Try outdoors."
                nearest == null -> reading = "Outside the three measured areas."
                else -> {
                    level = nearest.first.levelAt(NoiseMap.FIRST_HOUR)
                    siteName = nearest.first.site
                    // Said only when it matters: a fix wider than a cell makes the
                    // choice of cell partly chance, and the reader should know.
                    reading = if (fix.accuracyM > NoiseMap.CELL_SIZE_M) {
                        String.format(
                            Locale.US,
                            "The fix is only accurate to %.0f m, wider than a 40 m cell — this " +
                                "could be the neighbouring one.",
                            fix.accuracyM,
                        )
                    } else {
                        null
                    }
                }
            }
        }
    }

    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { granted ->
        if (granted.values.any { it }) readHere() else reading = "Location permission refused."
    }

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Predicted level where I am", style = MaterialTheme.typography.titleSmall)
            if (searching) {
                Text("Searching…", style = MaterialTheme.typography.bodyMedium)
                LinearProgressIndicator(Modifier.fillMaxWidth())
            }
            level?.let { db ->
                Text(
                    String.format(Locale.US, "%.0f dB", db),
                    style = MaterialTheme.typography.displaySmall,
                    color = levelColour(db),
                )
                siteName?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
            }
            reading?.let {
                Text(
                    it,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline,
                )
            }
            OutlinedButton(
                enabled = !searching,
                onClick = {
                    permission.launch(
                        arrayOf(
                            Manifest.permission.ACCESS_FINE_LOCATION,
                            Manifest.permission.ACCESS_COARSE_LOCATION,
                        )
                    )
                },
            ) { Text(if (level == null && reading == null) "Read my position" else "Read again") }
        }
    }
}

/** How long to listen for a better fix before answering with the best seen. */
private const val SEARCH_MS = 25_000L

/** Accurate enough to choose a 40 m cell without ambiguity. */
private const val GOOD_ENOUGH_M = 15.0

/** How many good fixes to average before answering. */
private const val ENOUGH_FIXES = 5

@Composable
private fun ScopeNotice(multiplier: Float) {
    Card(
        Modifier.fillMaxWidth().padding(bottom = 24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(
                "Cells predicted over a 40 m grid, dots the 363 measurements. Bands are " +
                    "QCVN 26:2010, descriptive only — levels are relative, not absolute.",
                style = MaterialTheme.typography.bodySmall,
            )
            if (multiplier != 1f) {
                Text(
                    "Scales the traffic share of the energy, not the zone's residual ambience.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        }
    }
}
