package org.noisehanoi.mobile.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import org.noisehanoi.mobile.outbox.Outbox
import org.noisehanoi.mobile.outbox.SubmitWorker
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OutboxScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val outbox = remember { Outbox(java.io.File(context.filesDir, SubmitWorker.OUTBOX_DIR)) }
    var refresh by remember { mutableStateOf(0) }
    // Sweeping first: a measurement that was stopped by hand leaves its raw PCM
    // behind, and listing the outbox is the first moment anything can tell.
    val entries = remember(refresh) {
        outbox.sweep()
        outbox.entries()
    }
    val stamp = remember { SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Outbox") },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
            )
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = {
                    SubmitWorker.enqueue(context)
                    refresh++
                }) { Text("Send now") }
                OutlinedButton(onClick = {
                    outbox.purgeSent()
                    refresh++
                }) { Text("Clear sent") }
                OutlinedButton(onClick = { refresh++ }) { Text("Refresh") }
            }

            if (entries.isEmpty()) {
                Text("Nothing waiting.", style = MaterialTheme.typography.bodyMedium)
            }

            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(entries, key = { it.id }) { entry ->
                    Card(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(entry.formTitle.ifBlank { entry.formId }, style = MaterialTheme.typography.titleSmall)
                            Text(
                                "${stamp.format(Date(entry.createdAt))} · ${entry.state} · " +
                                    "${entry.attachments().size} attachment(s)" +
                                    if (entry.attempts > 0) " · ${entry.attempts} attempt(s)" else "",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.outline,
                            )
                            entry.lastError?.let {
                                Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                            }
                            if (entry.state == Outbox.State.FAILED) {
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    OutlinedButton(onClick = {
                                        outbox.requeue(entry)
                                        SubmitWorker.enqueue(context)
                                        refresh++
                                    }) { Text("Retry") }
                                    TextButton(onClick = {
                                        outbox.delete(entry)
                                        refresh++
                                    }) { Text("Delete") }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
