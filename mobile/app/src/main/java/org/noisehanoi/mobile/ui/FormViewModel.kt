package org.noisehanoi.mobile.ui

import android.Manifest
import android.app.Application
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.noisehanoi.mobile.BuildConfig
import org.noisehanoi.mobile.form.Answers
import org.noisehanoi.mobile.form.Attachment
import org.noisehanoi.mobile.form.FormSpec
import org.noisehanoi.mobile.form.GeoPoint
import org.noisehanoi.mobile.form.GeoPointQ
import org.noisehanoi.mobile.form.NOISE_FORM_V3_VERSION
import org.noisehanoi.mobile.form.PUBLIC_COLLECTOR
import org.noisehanoi.mobile.location.GpsFixes
import org.noisehanoi.mobile.location.Sites
import org.noisehanoi.mobile.measure.AacEncoder
import org.noisehanoi.mobile.measure.SplMeter
import org.noisehanoi.mobile.odk.InstanceXml
import org.noisehanoi.mobile.outbox.Outbox
import org.noisehanoi.mobile.outbox.SubmitWorker
import org.noisehanoi.mobile.settings.Settings
import java.io.File
import java.util.Locale
import java.util.TimeZone

class FormViewModel(application: Application) : AndroidViewModel(application) {

    data class MeterState(
        val running: Boolean = false,
        val elapsed: Double = 0.0,
        val slowDb: Double = Double.NaN,
        val leqDb: Double = Double.NaN,
        val clippedFraction: Double = 0.0,
        val finishedLeqDb: Double? = null,
        val clipSeconds: Double = 0.0,
        val error: String? = null,
    )

    data class GpsState(
        val point: GeoPoint? = null,
        val searching: Boolean = false,
        val error: String? = null,
    ) {
        val accurateEnough: Boolean
            get() = point != null && point.accuracyM > 0 && point.accuracyM <= GpsFixes.REQUIRED_ACCURACY_M
    }

    val settings = Settings(application)

    private lateinit var spec: FormSpec
    private var instanceId: String = ""
    private var instanceDir: File = application.cacheDir
    private var startedAt: Long = 0L

    private val _answers = MutableStateFlow<Answers?>(null)
    val answers: StateFlow<Answers?> = _answers.asStateFlow()

    private val _gps = MutableStateFlow(GpsState())
    val gps: StateFlow<GpsState> = _gps.asStateFlow()

    private val _meter = MutableStateFlow(MeterState())
    val meter: StateFlow<MeterState> = _meter.asStateFlow()

    private val _submitted = MutableStateFlow<String?>(null)
    val submitted: StateFlow<String?> = _submitted.asStateFlow()

    private var gpsJob: Job? = null
    private var meterJob: Job? = null

    private val outbox by lazy { Outbox(File(getApplication<Application>().filesDir, SubmitWorker.OUTBOX_DIR)) }

    /**
     * The answers so far, on disk beside the instance they will become.
     *
     * Android kills backgrounded apps as a matter of routine — a phone call, a
     * notification, memory pressure — and everything typed into a form lived only
     * in this ViewModel. A field worker who answered a call halfway through lost
     * the lot, while the recorded clip stayed on disk as an orphan.
     *
     * A flat JSON map rewritten on every change. Not a database, not a state
     * machine: the file is small, the write is a few hundred bytes, and a draft
     * that survives is worth more than a clever way of storing it.
     */
    private fun draftFile() = File(instanceDir, Outbox.DRAFT_FILE)

    private fun saveDraft() {
        val answers = _answers.value ?: return
        runCatching {
            val json = org.json.JSONObject()
            answers.values.forEach { (k, v) -> json.put(k, v) }
            val attachments = org.json.JSONObject()
            answers.attachments.forEach { (field, a) ->
                attachments.put(field, org.json.JSONObject()
                    .put("fileName", a.fileName)
                    .put("absolutePath", a.absolutePath))
            }
            draftFile().writeText(
                org.json.JSONObject().put("values", json).put("attachments", attachments).toString()
            )
        }
    }

    private fun restoreDraft(spec: FormSpec, dir: File): Answers? {
        val file = File(dir, Outbox.DRAFT_FILE)
        if (!file.isFile) return null
        return runCatching {
            val root = org.json.JSONObject(file.readText())
            var answers = Answers(spec)
            val values = root.optJSONObject("values")
            values?.keys()?.forEach { key -> answers = answers.with(key, values.optString(key)) }
            val attachments = root.optJSONObject("attachments")
            attachments?.keys()?.forEach { field ->
                val a = attachments.getJSONObject(field)
                val path = a.getString("absolutePath")
                // Only if the file is still there; a clip deleted under us must not
                // become an attachment the outbox cannot find.
                if (File(path).isFile) {
                    answers = answers.withAttachment(
                        Attachment(field, a.getString("fileName"), path)
                    )
                }
            }
            answers
        }.getOrNull()
    }

    /** The most recent unsaved draft, if the app died with one open. */
    private fun latestDraftDir(): File? =
        File(getApplication<Application>().filesDir, SubmitWorker.OUTBOX_DIR)
            .listFiles()
            ?.filter { it.isDirectory && File(it, Outbox.DRAFT_FILE).isFile && !File(it, Outbox.STATE_FILE).isFile }
            ?.maxByOrNull { File(it, Outbox.DRAFT_FILE).lastModified() }

    /**
     * Whether the permission is granted right now.
     *
     * The screens only start these from a permission callback, but that is an
     * invariant held by the caller, and a caller is one refactor away from
     * changing. The platform's answer to an ungranted microphone or location is a
     * SecurityException thrown inside a background flow, which is a process death,
     * not an error message. Asking first turns it into one.
     */
    private fun granted(permission: String): Boolean =
        ContextCompat.checkSelfPermission(getApplication(), permission) == PackageManager.PERMISSION_GRANTED

    fun start(requested: FormSpec) {
        // Never blocking, in either mode. See `withOptionalAudio`.
        val formSpec = requested.withOptionalAudio()
        if (_answers.value != null && ::spec.isInitialized && spec.id == formSpec.id) return
        spec = formSpec

        // Pick up where a killed app left off, if it left anything.
        val resumed = latestDraftDir()?.let { dir -> restoreDraft(formSpec, dir)?.let { dir to it } }
        if (resumed != null) {
            instanceDir = resumed.first
            instanceId = "uuid:" + resumed.first.name.removePrefix("uuid_")
            startedAt = File(resumed.first, Outbox.DRAFT_FILE).lastModified()
            _answers.value = resumed.second
            _meter.value = MeterState()
            _submitted.value = null
            return
        }

        instanceId = InstanceXml.newInstanceId()
        instanceDir = outbox.newDir(instanceId)
        startedAt = System.currentTimeMillis()
        _answers.value = Answers(formSpec).with(
            "collector",
            if (settings.publicMode) PUBLIC_COLLECTOR else settings.collector.takeIf { it.isNotBlank() },
        )
        _meter.value = MeterState()
        _submitted.value = null
    }

    fun set(name: String, value: String?) {
        _answers.value = _answers.value?.with(name, value)
        saveDraft()
    }

    // --- GPS ----------------------------------------------------------------

    fun startGps() {
        if (gpsJob?.isActive == true) return
        if (!granted(Manifest.permission.ACCESS_FINE_LOCATION) &&
            !granted(Manifest.permission.ACCESS_COARSE_LOCATION)
        ) {
            _gps.value = GpsState(error = "Location permission not granted")
            return
        }
        _gps.value = _gps.value.copy(searching = true, error = null)
        gpsJob = viewModelScope.launch {
            GpsFixes.stream(getApplication())
                .catch { e -> _gps.value = GpsState(error = e.message ?: "Location unavailable") }
                .collect { point ->
                    val current = _gps.value.point
                    // Keep the best fix of the session, not the latest one.
                    val keep = if (current == null || point.accuracyM in 0.1..current.accuracyM) point else current
                    _gps.value = GpsState(point = keep, searching = true)
                    suggestSiteFrom(keep)
                }
        }
    }

    fun stopGps() {
        gpsJob?.cancel()
        gpsJob = null
        _gps.value = _gps.value.copy(searching = false)
    }

    fun acceptFix() {
        val point = _gps.value.point ?: return
        val field = spec.questions.filterIsInstance<GeoPointQ>().firstOrNull()?.name ?: return
        _answers.value = _answers.value?.withGeoPoint(field, point)
        saveDraft()
        stopGps()
    }

    private fun suggestSiteFrom(point: GeoPoint) {
        val answers = _answers.value ?: return
        if (answers["site"] != null) return
        if (spec.questions.none { it.name == "site" }) return
        val (site, distance) = Sites.nearest(point)
        _answers.value = answers.with(
            "site",
            if (distance <= Sites.SITE_RADIUS_M) site.choiceName else "other_site",
        )
        saveDraft()
    }

    /** Nearest campaign site to the current fix, and its distance, for the UI. */
    fun siteContext(): Pair<Sites.Site, Double>? = _gps.value.point?.let { Sites.nearest(it) }

    // --- measurement --------------------------------------------------------

    fun startMeasurement() {
        if (meterJob?.isActive == true) return
        if (!granted(Manifest.permission.RECORD_AUDIO)) {
            _meter.value = MeterState(error = "Microphone permission not granted")
            return
        }
        val rawPcm = File(instanceDir, "capture.pcm")
        _meter.value = MeterState(running = true)
        meterJob = viewModelScope.launch {
            // The raw PCM is a working file and it is 2.4 MB. Stopping a measurement
            // by hand cancels this coroutine wherever it stands, so its removal
            // belongs in a finally rather than on the success path.
            try {
                val splMeter = SplMeter(getApplication())
                var last: SplMeter.Reading? = null
                splMeter.measure(rawPcm, settings.micOffsetDb.toDouble(), SplMeter.WINDOW_SECONDS)
                    .catch { e -> _meter.value = MeterState(error = e.message ?: "Microphone unavailable") }
                    .collect { reading ->
                        last = reading
                        _meter.value = MeterState(
                            running = true,
                            elapsed = reading.elapsedSeconds,
                            slowDb = reading.slowDb,
                            leqDb = reading.leqDb,
                            clippedFraction = reading.clippedFraction,
                        )
                    }

                val reading = last
                if (reading == null) {
                    if (_meter.value.error == null) _meter.value = MeterState(error = "No audio captured")
                    return@launch
                }

                // Public mode keeps the level and drops the recording: nothing is
                // encoded, nothing is attached, nothing of the street's voices
                // leaves the phone. It is also the difference between 28 MB and
                // 10 GB at the scale this app is meant for.
                val keepClip = !settings.publicMode
                val clip = File(instanceDir, "audio_${System.currentTimeMillis()}.m4a")
                val encoded = keepClip && withContext(Dispatchers.IO) {
                    runCatching { AacEncoder.encode(rawPcm, clip, reading.sampleRate) }.isSuccess
                }

                val answers = _answers.value
                if (answers != null) {
                    var updated = answers
                    if (encoded) {
                        // "Measure again" replaces the clip; the one it replaces is
                        // 200 kB that no instance will ever reference.
                        answers.previousAttachment("audio_sample")
                            ?.takeIf { it.fileName != clip.name }
                            ?.let { withContext(Dispatchers.IO) { File(it.absolutePath).delete() } }
                        updated = updated.withAttachment(
                            Attachment("audio_sample", clip.name, clip.absolutePath)
                        )
                    }
                    // Independent of the clip. Tying the two together meant that in
                    // public mode, where no clip is made, the level stopped being
                    // filled in — in exactly the mode where the user has no other
                    // way to obtain it.
                    if (settings.useInAppMeter) {
                        updated = updated.with("noise_db", String.format(Locale.US, "%.1f", reading.leqDb))
                    }
                    _answers.value = updated
                    saveDraft()
                }
                audioSource = reading.audioSource
                _meter.value = MeterState(
                    running = false,
                    elapsed = reading.elapsedSeconds,
                    slowDb = reading.slowDb,
                    leqDb = reading.leqDb,
                    clippedFraction = reading.clippedFraction,
                    finishedLeqDb = reading.leqDb,
                    clipSeconds = reading.elapsedSeconds,
                    error = when {
                        encoded || !keepClip -> null
                        else -> "Level measured, but the clip could not be encoded"
                    },
                )
            } finally {
                rawPcm.delete()
            }
        }
    }

    /**
     * Records a refusal, so a second tap on a permanently denied permission says
     * something. Android stops showing its dialog after the second refusal and
     * answers the request immediately; without this the button would simply do
     * nothing, which reads as a broken app rather than a decision the user made.
     */
    fun microphoneRefused() {
        _meter.value = MeterState(
            error = "Microphone permission refused. Turn it on in Android Settings > Apps > Noise Hanoi > Permissions.",
        )
    }

    fun locationRefused() {
        _gps.value = GpsState(
            error = "Location permission refused. Turn it on in Android Settings > Apps > Noise Hanoi > Permissions.",
        )
    }

    fun stopMeasurement() {
        meterJob?.cancel()
        meterJob = null
        _meter.value = _meter.value.copy(running = false)
    }

    private var audioSource: String = "unknown"

    // --- attachments from elsewhere (the construction form's photo) ----------

    fun attachFile(fieldName: String, file: File) {
        val answers = _answers.value ?: return
        answers.previousAttachment(fieldName)
            ?.takeIf { it.fileName != file.name }
            ?.let { File(it.absolutePath).delete() }
        _answers.value = answers.withAttachment(Attachment(fieldName, file.name, file.absolutePath))
        saveDraft()
    }

    fun photoTarget(fieldName: String): File = File(instanceDir, "${fieldName}_${System.currentTimeMillis()}.jpg")

    // --- submission ---------------------------------------------------------

    fun problems(): Map<String, String> = _answers.value?.problems() ?: emptyMap()

    fun submit() {
        val answers = _answers.value ?: return
        if (!answers.isComplete) return
        val offsetMinutes = TimeZone.getDefault().getOffset(System.currentTimeMillis()) / 60_000

        val extras = if (settings.extendedForm) buildMap {
            _meter.value.finishedLeqDb?.let { put("app_noise_db", String.format(Locale.US, "%.1f", it)) }
            put("measure_method", if (settings.useInAppMeter) "in_app_$audioSource" else "external_meter_app")
            put("device_model", "${Build.MANUFACTURER} ${Build.MODEL}")
            put("os_version", "Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
            put("app_version", BuildConfig.VERSION_NAME)
            put("contributor_id", settings.contributorId)
        } else emptyMap()

        val xml = InstanceXml.build(
            answers = answers,
            instanceId = instanceId,
            start = InstanceXml.timestamp(startedAt, offsetMinutes),
            end = InstanceXml.timestamp(System.currentTimeMillis(), offsetMinutes),
            extraFields = extras,
            // What the server calls this form. Absent until Settings has fetched
            // the form list at least once, in which case the instance falls back
            // to the XLSForm's own id — which a Kobo server will answer 404.
            deployment = settings.deployedForm(spec.title),
        )
        draftFile().delete()   // it is an instance now, not a draft
        outbox.save(instanceId, spec.id, spec.title, xml)
        SubmitWorker.enqueue(getApplication())
        _submitted.value = instanceId
        _answers.value = null
    }

    override fun onCleared() {
        gpsJob?.cancel()
        meterJob?.cancel()
        super.onCleared()
    }
}
