package org.noisehanoi.mobile.outbox

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.noisehanoi.mobile.odk.OpenRosaClient
import org.noisehanoi.mobile.settings.Settings
import java.io.File

/**
 * Drains the outbox when there is a network.
 *
 * Field sessions happen where the signal is worst, so submission is never on the
 * path of finishing a form: the instance is written to disk, and this runs
 * later. A refusal the server will repeat — a wrong password, an instance the
 * deployed form does not recognise — is recorded as failed and left alone rather
 * than retried forever.
 */
class SubmitWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val outbox = Outbox(File(applicationContext.filesDir, OUTBOX_DIR))
        val config = Settings(applicationContext).openRosaConfig()
        val client = OpenRosaClient()

        var retryNeeded = false
        for (entry in outbox.pending()) {
            val attachments = entry.attachments()
            val missing = attachments.filterNot { it.isFile }
            if (missing.isNotEmpty()) {
                // A referenced file that is not there will fail the upload the same
                // way every time. Retrying it forever burns the field phone's battery
                // and buries the submissions behind it.
                outbox.markFailed(entry, "Missing attachment: ${missing.joinToString { it.name }}")
                continue
            }
            when (val outcome = client.submit(config, entry.instanceFile, attachments)) {
                is OpenRosaClient.Outcome.Accepted -> outbox.markSent(entry)
                is OpenRosaClient.Outcome.Rejected ->
                    outbox.markFailed(entry, "HTTP ${outcome.code}: ${outcome.message}")
                is OpenRosaClient.Outcome.Retryable -> {
                    outbox.markRetry(entry, outcome.message)
                    retryNeeded = true
                }
            }
        }
        if (retryNeeded) Result.retry() else Result.success()
    }

    companion object {
        const val OUTBOX_DIR = "outbox"
        private const val WORK_NAME = "submit-outbox"

        fun enqueue(context: Context) {
            val request = OneTimeWorkRequestBuilder<SubmitWorker>()
                .setConstraints(
                    Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
                )
                .build()
            WorkManager.getInstance(context)
                // APPEND_OR_REPLACE, not REPLACE: submitting a second form while the
                // first is still uploading would otherwise cancel that upload
                // mid-request and re-send the attachment from the start.
                .enqueueUniqueWork(WORK_NAME, ExistingWorkPolicy.APPEND_OR_REPLACE, request)
        }
    }
}
