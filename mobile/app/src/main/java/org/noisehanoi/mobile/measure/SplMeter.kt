package org.noisehanoi.mobile.measure

import android.annotation.SuppressLint
import android.content.Context
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.MediaRecorder
import android.media.audiofx.AcousticEchoCanceler
import android.media.audiofx.AudioEffect
import android.media.audiofx.AutomaticGainControl
import android.media.audiofx.NoiseSuppressor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.isActive
import java.io.BufferedOutputStream
import java.io.File
import java.io.OutputStream
import kotlin.math.abs

/**
 * One microphone session that does two jobs at once: it measures the level and
 * it keeps the raw audio for the clip the form asks for.
 *
 * Doing both from a single capture is not an optimisation, it is a correctness
 * requirement. Android will not usually give `AudioRecord` and `MediaRecorder`
 * the microphone at the same time, so measuring and recording separately would
 * mean measuring one stretch of street and submitting a different one. Here the
 * PCM is written to a raw file as it is filtered, and [AacEncoder] turns it into
 * the `.m4a` afterwards.
 *
 * A missing or revoked microphone permission comes back as a flow error rather
 * than an exception: it can be withdrawn from Settings while the app is in the
 * background, so no check made beforehand is still true by the time the recorder
 * starts.
 *
 * Three things stand between this and a number that means something.
 *
 * **The signal must not be pre-processed.** Automatic gain control rescales the
 * signal to keep speech intelligible, which is precisely the information a level
 * measurement is made of; noise suppression removes the steady background, which
 * on a Hanoi street *is* the measurement. The capture asks for `UNPROCESSED`
 * where the device declares it and `VOICE_RECOGNITION` otherwise, and then
 * explicitly turns off AGC, noise suppression and echo cancellation on the
 * session — an audio source is a request, not a guarantee, and several handsets
 * apply effects anyway. [Reading.audioSource] records what was actually obtained,
 * so a submission can say how it was measured rather than how it was asked for.
 *
 * **The first second is discarded.** The weighting filter starts from rest and
 * the microphone hardware settles over the first buffers; both bias an average
 * that begins at sample zero. [WARMUP_SECONDS] of audio is run through the filter
 * to settle it, then thrown away — it is excluded from the energy, from the
 * clipping count and from the written clip, so the clip really is the stretch
 * that was measured.
 *
 * **The rate has to exist.** 48 kHz is asked for first, because the A-weighting
 * design is accurate there; a handset that will not give it falls back to
 * 44.1 kHz rather than failing to measure at all.
 */
class SplMeter(private val context: Context) {

    data class Reading(
        val elapsedSeconds: Double,
        /** Level with SLOW time weighting — the live number, as the protocol reads it. */
        val slowDb: Double,
        /** Equivalent continuous level over the measured window so far. */
        val leqDb: Double,
        /** Fraction of samples at full scale. Anything above zero invalidates the reading. */
        val clippedFraction: Double,
        /** The rate actually granted, needed to encode the clip that goes with it. */
        val sampleRate: Int,
        /** What the platform gave, and what was switched off. Goes into the submission. */
        val audioSource: String,
    )

    private class Capture(
        val record: AudioRecord,
        val sampleRate: Int,
        val description: String,
        val effects: List<AudioEffect>,
    ) {
        fun release() {
            effects.forEach { runCatching { it.release() } }
            runCatching { record.release() }
        }
    }

    @SuppressLint("MissingPermission")
    fun measure(rawPcm: File, offsetDb: Double, maxSeconds: Double): Flow<Reading> = callbackFlow {
        val capture = openCapture()
        if (capture == null) {
            close(IllegalStateException("Microphone unavailable"))
            return@callbackFlow
        }

        val sampleRate = capture.sampleRate
        val weighting = AWeighting(sampleRate)
        val slow = ExponentialAverage(AWeighting.TAU_SLOW_S, sampleRate)
        val buffer = ShortArray(sampleRate / 10)   // 100 ms
        val warmupSamples = (WARMUP_SECONDS * sampleRate).toLong()

        var seenSamples = 0L        // everything the microphone returned
        var measuredSamples = 0L    // what counts, warm-up excluded
        var totalSquares = 0.0
        var clipped = 0L

        val out: OutputStream = BufferedOutputStream(rawPcm.outputStream())

        try {
            try {
                capture.record.startRecording()
            } catch (_: SecurityException) {
                close(SecurityException("Microphone permission not granted"))
                return@callbackFlow
            }
            var lastEmit = 0L
            while (isActive) {
                val read = capture.record.read(buffer, 0, buffer.size)
                if (read <= 0) continue

                // Where this buffer begins relative to the end of the warm-up.
                val fromWarmup = (warmupSamples - seenSamples).coerceIn(0L, read.toLong()).toInt()
                seenSamples += read

                var slowMeanSquare = 0.0
                for (i in 0 until read) {
                    val raw = buffer[i]
                    val a = weighting.filter(raw.toDouble() / FULL_SCALE)
                    // The filter runs through the warm-up so that it settles; nothing
                    // else does.
                    if (i < fromWarmup) continue
                    slowMeanSquare = slow.accept(a)
                    totalSquares += a * a
                    if (abs(raw.toInt()) >= Short.MAX_VALUE - 1) clipped++
                }
                if (fromWarmup < read) {
                    PcmWriter.write(out, buffer, read, from = fromWarmup)
                    measuredSamples += read - fromWarmup
                }
                if (measuredSamples == 0L) continue

                val elapsed = measuredSamples.toDouble() / sampleRate
                val now = System.currentTimeMillis()
                if (now - lastEmit >= 100) {
                    lastEmit = now
                    trySend(
                        Reading(
                            elapsedSeconds = elapsed,
                            slowDb = meanSquareToDb(slowMeanSquare, offsetDb),
                            leqDb = meanSquareToDb(totalSquares / measuredSamples, offsetDb),
                            clippedFraction = clipped.toDouble() / measuredSamples,
                            sampleRate = sampleRate,
                            audioSource = capture.description,
                        )
                    )
                }
                if (elapsed >= maxSeconds) break
            }
        } finally {
            runCatching { capture.record.stop() }
            capture.release()
            runCatching { out.flush(); out.close() }
        }
        close()
    }.flowOn(Dispatchers.Default)

    @SuppressLint("MissingPermission")
    private fun openCapture(): Capture? {
        for (rate in SAMPLE_RATES) {
            val minBuffer = AudioRecord.getMinBufferSize(
                rate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT,
            )
            if (minBuffer <= 0) continue
            val bufferSize = maxOf(minBuffer * 2, rate)   // about half a second

            for ((source, name) in preferredSources()) {
                val record = runCatching {
                    AudioRecord(source, rate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, bufferSize)
                }.getOrNull() ?: continue
                if (record.state != AudioRecord.STATE_INITIALIZED) {
                    record.release()
                    continue
                }
                val (effects, disabled) = disableProcessing(record.audioSessionId)
                val description = buildString {
                    append(name)
                    append('@').append(rate)
                    if (disabled.isNotEmpty()) append(" (").append(disabled.joinToString("+")).append(" off)")
                }
                return Capture(record, rate, description, effects)
            }
        }
        return null
    }

    /**
     * Turns off everything the platform might be doing to the signal, and reports
     * what it found. An effect that is not available was never going to interfere;
     * one that is available and left on would.
     */
    private fun disableProcessing(sessionId: Int): Pair<List<AudioEffect>, List<String>> {
        val held = mutableListOf<AudioEffect>()
        val disabled = mutableListOf<String>()

        fun attach(name: String, available: Boolean, create: () -> AudioEffect?) {
            if (!available) return
            val effect = runCatching { create() }.getOrNull() ?: return
            held += effect
            if (runCatching { effect.enabled = false; !effect.enabled }.getOrDefault(false)) {
                disabled += name
            }
        }

        attach("agc", AutomaticGainControl.isAvailable()) { AutomaticGainControl.create(sessionId) }
        attach("ns", NoiseSuppressor.isAvailable()) { NoiseSuppressor.create(sessionId) }
        attach("aec", AcousticEchoCanceler.isAvailable()) { AcousticEchoCanceler.create(sessionId) }
        return held to disabled
    }

    private fun preferredSources(): List<Pair<Int, String>> {
        val sources = mutableListOf<Pair<Int, String>>()
        val audio = context.getSystemService(Context.AUDIO_SERVICE) as? AudioManager
        if (audio?.getProperty(AudioManager.PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED) == "true") {
            sources += MediaRecorder.AudioSource.UNPROCESSED to "unprocessed"
        }
        sources += MediaRecorder.AudioSource.VOICE_RECOGNITION to "voice_recognition"
        sources += MediaRecorder.AudioSource.MIC to "mic"
        return sources
    }

    companion object {
        /**
         * 48 kHz first: the A-weighting design is within 0.7 dB there and degrades
         * as the rate falls. 44.1 kHz is the fallback every handset supports.
         */
        val SAMPLE_RATES = intArrayOf(48_000, 44_100)

        const val FULL_SCALE = 32_768.0

        /** Discarded at the start: filter transient and microphone settling. */
        const val WARMUP_SECONDS = 1.0

        /** The protocol's observation length: a 20-30 s stationary reading. */
        const val WINDOW_SECONDS = 25.0

        /** The form requires at least this much audio in the clip. */
        const val MIN_CLIP_SECONDS = 10.0
    }
}
