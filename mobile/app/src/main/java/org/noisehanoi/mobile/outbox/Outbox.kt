package org.noisehanoi.mobile.outbox

import org.json.JSONObject
import java.io.File

/**
 * Pending submissions, on disk.
 *
 * One directory per instance, holding the instance XML, its attachments and a
 * small state file — the same shape ODK Collect uses, for the same reason: a
 * field session loses signal, the app is killed, and nothing may be lost. There
 * is no database here on purpose; a directory that survives a crash is easier to
 * reason about, and easier to recover by hand, than a half-migrated schema.
 */
class Outbox(private val root: File) {

    enum class State { PENDING, SENT, FAILED }

    data class Entry(
        val id: String,
        val dir: File,
        val formId: String,
        val formTitle: String,
        val createdAt: Long,
        val state: State,
        val attempts: Int,
        val lastError: String?,
    ) {
        val instanceFile: File get() = File(dir, INSTANCE_FILE)

        /**
         * The files this instance actually references, not everything in the
         * directory.
         *
         * The directory is also the measurement's workspace — the raw PCM is
         * written here before it is encoded — and a session that is stopped by
         * hand, or killed mid-encode, leaves that file behind. Uploading whatever
         * happens to be lying next to the instance would send 2.4 MB of raw audio
         * per stranded file to a server that a public campaign is already going to
         * strain. So the instance is the authority: a file goes up only if the
         * submission names it.
         */
        fun attachments(): List<File> {
            val referenced = runCatching { instanceFile.readText() }.getOrElse { return emptyList() }
            return dir.listFiles()
                ?.filter { it.isFile && it.name != INSTANCE_FILE && it.name != STATE_FILE }
                ?.filter { referenced.contains(">${it.name}<") }
                ?.sortedBy { it.name }
                ?: emptyList()
        }

        /** Files in the directory that the instance does not reference. */
        fun strayFiles(): List<File> {
            val kept = (attachments().map { it.name } + INSTANCE_FILE + STATE_FILE).toSet()
            return dir.listFiles()?.filter { it.isFile && it.name !in kept } ?: emptyList()
        }
    }

    init {
        root.mkdirs()
    }

    /**
     * Creates the directory for a new instance and returns it, so the caller can
     * write attachments into it before [save] writes the instance and state.
     */
    fun newDir(id: String): File = File(root, sanitize(id)).apply { mkdirs() }

    fun save(id: String, formId: String, formTitle: String, instanceXml: String): Entry {
        val dir = newDir(id)
        File(dir, INSTANCE_FILE).writeText(instanceXml)
        val entry = Entry(id, dir, formId, formTitle, System.currentTimeMillis(), State.PENDING, 0, null)
        writeState(entry)
        return entry
    }

    /**
     * Removes the directories of forms that were opened and never saved.
     *
     * A directory is created when a form is opened, because the measurement has
     * to write its audio somewhere before there is anything to submit. Back out
     * of the form and it stays, holding a 200 kB clip that no instance will ever
     * reference. Only a directory with no state file can be a draft, and only at
     * startup is it certain that none of them is the form currently being
     * filled — so this is called from there and from nowhere else.
     */
    fun discardDrafts(): Int = (root.listFiles() ?: emptyArray())
        .filter { it.isDirectory && !File(it, STATE_FILE).isFile }
        .count { it.deleteRecursively() }

    /**
     * Removes working files that a saved instance does not reference — the raw
     * PCM of a measurement that was stopped by hand, most of all.
     */
    fun sweep(): Int = entries().sumOf { entry ->
        entry.strayFiles().count { it.delete() }
    }

    fun entries(): List<Entry> = (root.listFiles() ?: emptyArray())
        .filter { it.isDirectory }
        .mapNotNull { readState(it) }
        .sortedByDescending { it.createdAt }

    fun pending(): List<Entry> = entries().filter { it.state == State.PENDING }

    fun markSent(entry: Entry) = writeState(entry.copy(state = State.SENT, lastError = null))

    fun markFailed(entry: Entry, error: String) =
        writeState(entry.copy(state = State.FAILED, attempts = entry.attempts + 1, lastError = error))

    fun markRetry(entry: Entry, error: String) =
        writeState(entry.copy(state = State.PENDING, attempts = entry.attempts + 1, lastError = error))

    /** Retry a submission the server refused, after the configuration was fixed. */
    fun requeue(entry: Entry) = writeState(entry.copy(state = State.PENDING, lastError = null))

    fun delete(entry: Entry) {
        entry.dir.deleteRecursively()
    }

    /** Drops accepted submissions and their attachments. Audio clips are large. */
    fun purgeSent(): Int {
        val sent = entries().filter { it.state == State.SENT }
        sent.forEach { it.dir.deleteRecursively() }
        return sent.size
    }

    private fun writeState(entry: Entry) {
        val json = JSONObject()
            .put("id", entry.id)
            .put("formId", entry.formId)
            .put("formTitle", entry.formTitle)
            .put("createdAt", entry.createdAt)
            .put("state", entry.state.name)
            .put("attempts", entry.attempts)
            .put("lastError", entry.lastError ?: JSONObject.NULL)
        File(entry.dir, STATE_FILE).writeText(json.toString())
    }

    private fun readState(dir: File): Entry? {
        val file = File(dir, STATE_FILE)
        if (!file.isFile) return null
        return try {
            val json = JSONObject(file.readText())
            Entry(
                id = json.getString("id"),
                dir = dir,
                formId = json.optString("formId"),
                formTitle = json.optString("formTitle"),
                createdAt = json.optLong("createdAt"),
                state = State.valueOf(json.optString("state", State.PENDING.name)),
                attempts = json.optInt("attempts"),
                lastError = json.optString("lastError").takeIf { it.isNotBlank() && it != "null" },
            )
        } catch (_: Exception) {
            // A torn state file must not take the whole outbox down, and it must not
            // make its submission invisible either: an entry that cannot be listed
            // cannot be retried or deleted, and its attachments stay on the phone for
            // good. Surface it as failed, with the instance intact.
            Entry(
                id = dir.name,
                dir = dir,
                formId = "",
                formTitle = "Unreadable submission",
                createdAt = file.lastModified(),
                state = State.FAILED,
                attempts = 0,
                lastError = "Its state file could not be read. The submission itself may still be intact.",
            )
        }
    }

    private fun sanitize(id: String) = id.replace(Regex("[^A-Za-z0-9_.-]"), "_")

    companion object {
        const val INSTANCE_FILE = "submission.xml"
        const val STATE_FILE = "state.json"
    }
}
