package org.noisehanoi.mobile.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.noisehanoi.mobile.study.Headline
import org.noisehanoi.mobile.study.StudyData
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResultsScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    var data by remember { mutableStateOf<StudyData?>(null) }
    LaunchedEffect(Unit) { data = withContext(Dispatchers.IO) { StudyData.load(context) } }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("What the study found") },
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
        val h = study.headline

        Column(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Card(
                Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
            ) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("The campaign", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "${h.nMeasurements} measurements, ${h.dateMin} to ${h.dateMax}, " +
                            String.format(Locale.US, "%.0f to %.0f dB.", h.dbMin, h.dbMax),
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    h.sites.forEach { (site, n) ->
                        Text("· $site — $n points", style = MaterialTheme.typography.bodySmall)
                    }
                    Text(
                        "Three consumer smartphones, cross-calibrated against each other and against " +
                            "no reference instrument. Every level here is a contrast, not an absolute.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline,
                    )
                }
            }

            Text("The three negative results are the contribution", style = MaterialTheme.typography.titleMedium)

            NegativeResult(
                "1. A three-parameter physical law beat every learned model",
                "The delivered model is a line-source attenuation kernel, E = A_hw/d_hw + A_res/d_res + B. " +
                    "It is ahead of six candidates under the reference protocol, including the " +
                    "physics-plus-ML hybrid the team had recommended to itself. The ranking inverts " +
                    "almost exactly between the permissive protocol and the two that test " +
                    "generalisation — which is why the map you see is produced by the physics alone.",
            )
            NegativeResult(
                "2. Morphology from OpenStreetMap added nothing measurable",
                "Built area, road density and intersection counts aggregated over 300 m brought no " +
                    "gain the strict protocols could see. Spatial contrast comes from distance to the " +
                    "two road classes and from nothing else.",
            )
            NegativeResult(
                "3. A model trained in one city did not transfer",
                "Nor did vehicle flow extracted from video explain measured levels. The withdrawn " +
                    "R2 of 0.45 came from a cross-validation grouped on 110 m cells, smaller than the " +
                    "300 m feature radius: it leaked, and it must no longer be cited.",
            )

            Text("Delivered model: ${h.deliveredLabel}", style = MaterialTheme.typography.titleMedium)
            Text(
                "Chosen by code, not by hand: 04_evaluate_models.py takes the best R2 under buffered " +
                    "leave-one-out among six candidates fixed in advance. Every figure below is read " +
                    "from models/metrics.json at build time and none of it is retyped.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline,
            )

            h.protocols.forEach { protocol -> ProtocolTable(protocol) }

            Text("Field analyses", style = MaterialTheme.typography.titleMedium)
            AssetFigure(context, "figures/analyse_1_horaire.png", "Level by hour of day")
            AssetFigure(context, "figures/analyse_3_type.png", "Level by dominant source")
            AssetFigure(context, "figures/validation_simulation.png", "Simulated against measured")

            Box(Modifier.padding(bottom = 24.dp))
        }
    }
}

@Composable
private fun NegativeResult(title: String, body: String) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Text(body, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun ProtocolTable(protocol: Headline.Protocol) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(protocol.label, style = MaterialTheme.typography.titleSmall)
            Row(Modifier.fillMaxWidth()) {
                Text("Model", Modifier.weight(1f), style = MaterialTheme.typography.labelSmall)
                Text("R²", Modifier.weight(0.25f), style = MaterialTheme.typography.labelSmall)
                Text("MAE", Modifier.weight(0.25f), style = MaterialTheme.typography.labelSmall)
            }
            HorizontalDivider()
            protocol.models.forEach { m ->
                Row(Modifier.fillMaxWidth().padding(vertical = 2.dp)) {
                    Text(
                        m.label,
                        Modifier.weight(1f),
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = if (m.key == "physical") FontWeight.Bold else FontWeight.Normal,
                    )
                    Text(
                        String.format(Locale.US, "%.3f", m.r2),
                        Modifier.weight(0.25f),
                        style = MaterialTheme.typography.bodySmall,
                        fontFamily = FontFamily.Monospace,
                    )
                    Text(
                        String.format(Locale.US, "%.2f", m.mae),
                        Modifier.weight(0.25f),
                        style = MaterialTheme.typography.bodySmall,
                        fontFamily = FontFamily.Monospace,
                    )
                }
            }
        }
    }
}

@Composable
private fun AssetFigure(context: android.content.Context, path: String, caption: String) {
    var bitmap by remember(path) { mutableStateOf<android.graphics.Bitmap?>(null) }
    LaunchedEffect(path) {
        bitmap = withContext(Dispatchers.IO) {
            runCatching {
                context.assets.open(path).use { android.graphics.BitmapFactory.decodeStream(it) }
            }.getOrNull()
        }
    }
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(caption, style = MaterialTheme.typography.titleSmall)
            bitmap?.let {
                Image(
                    bitmap = it.asImageBitmap(),
                    contentDescription = caption,
                    modifier = Modifier.fillMaxWidth(),
                    contentScale = ContentScale.FillWidth,
                )
            }
        }
    }
}
