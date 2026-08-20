package org.noisehanoi.mobile.measure

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.log10
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * IEC 61672-1 A-weighting as a digital filter, plus the exponential time
 * weightings the field protocol uses.
 *
 * The analog weighting has four zeros at the origin and six poles: a double pole
 * at each of 20.599 Hz and 12194.217 Hz, and a single pole at each of 107.653 Hz
 * and 737.862 Hz. Under the bilinear substitution s = 2·fs·(1 - z⁻¹)/(1 + z⁻¹)
 * every analog zero at s = 0 becomes a factor (1 - z⁻¹), every real pole at
 * s = -a becomes a one-pole section, and — because there are six poles against
 * four zeros — two zeros land at z = -1, one for each surplus pole. Those two
 * factors are not optional: without them the curve rises about 1.9 dB too high
 * at 8 kHz and keeps climbing towards Nyquist, because the numerator no longer
 * carries the right order.
 *
 * Pole frequencies are prewarped, a' = 2·fs·tan(π·f/fs), so that each one lands
 * where the standard puts it rather than where the tangent map would drag it —
 * the 12.2 kHz pair moves to about 10.3 kHz without this, and that is the pair
 * that shapes the top of the curve.
 *
 * Measured against the IEC table at 48 kHz, the design is within 0.7 dB from
 * 31.5 Hz to 12.5 kHz and -3.1 dB at 16 kHz, comfortably inside class 1
 * tolerances across the band. The margin narrows as the sample rate falls, since
 * every one of these deviations is a warping effect: check [responseDb] again
 * before running below 32 kHz.
 *
 * Gain is normalised so the response is exactly 0 dB at 1 kHz, as the standard
 * defines it.
 */
class AWeighting(sampleRate: Int) {

    private val poles = DoubleArray(POLE_FREQUENCIES.size) { i ->
        val k = 2.0 * sampleRate
        val a = k * kotlin.math.tan(PI * POLE_FREQUENCIES[i] / sampleRate)   // prewarped
        (k - a) / (k + a)
    }
    private val gain: Double = 1.0 / magnitudeAt(1000.0, sampleRate)

    // Zeros at z = 1 (differences), zeros at z = -1 (sums), and the one-pole memory.
    private val zeroState = DoubleArray(N_ZEROS_AT_DC)
    private val nyquistState = DoubleArray(N_ZEROS_AT_NYQUIST)
    private val poleState = DoubleArray(POLE_FREQUENCIES.size)

    fun reset() {
        zeroState.fill(0.0)
        nyquistState.fill(0.0)
        poleState.fill(0.0)
    }

    /** Filters one sample. Input and output are full-scale units, not pascals. */
    fun filter(sample: Double): Double {
        var x = sample
        for (i in 0 until N_ZEROS_AT_DC) {
            val previous = zeroState[i]
            zeroState[i] = x
            x -= previous
        }
        for (i in 0 until N_ZEROS_AT_NYQUIST) {
            val previous = nyquistState[i]
            nyquistState[i] = x
            x += previous
        }
        for (i in poles.indices) {
            x += poles[i] * poleState[i]
            poleState[i] = x
        }
        return x * gain
    }

    /** Weighting curve value in dB at [frequency], for tests and for display. */
    fun responseDb(frequency: Double, sampleRate: Int): Double =
        20.0 * log10(magnitudeAt(frequency, sampleRate) * gain)

    private fun magnitudeAt(frequency: Double, sampleRate: Int): Double {
        val w = 2.0 * PI * frequency / sampleRate
        // Numerator (1 - z^-1)^4 (1 + z^-1)^2 evaluated on the unit circle.
        var reN = 1.0
        var imN = 0.0
        repeat(N_ZEROS_AT_DC) {
            val re = 1.0 - cos(w)
            val im = sin(w)
            val nr = reN * re - imN * im
            val ni = reN * im + imN * re
            reN = nr; imN = ni
        }
        repeat(N_ZEROS_AT_NYQUIST) {
            val re = 1.0 + cos(w)
            val im = -sin(w)
            val nr = reN * re - imN * im
            val ni = reN * im + imN * re
            reN = nr; imN = ni
        }
        // Denominator prod(1 - p·z^-1).
        var reD = 1.0
        var imD = 0.0
        for (p in poles) {
            val re = 1.0 - p * cos(w)
            val im = p * sin(w)
            val dr = reD * re - imD * im
            val di = reD * im + imD * re
            reD = dr; imD = di
        }
        val magN = sqrt(reN * reN + imN * imN)
        val magD = sqrt(reD * reD + imD * imD)
        return magN / magD
    }

    companion object {
        private const val N_ZEROS_AT_DC = 4

        /** One per surplus pole: six poles against four zeros. */
        private const val N_ZEROS_AT_NYQUIST = 2

        /** f1, f1, f2, f3, f4, f4 — the double poles written out. */
        private val POLE_FREQUENCIES = doubleArrayOf(
            20.598997, 20.598997, 107.65265, 737.86223, 12194.217, 12194.217,
        )

        /** Time constant of SLOW weighting, in seconds. The protocol uses SLOW. */
        const val TAU_SLOW_S = 1.0

        /** Time constant of FAST weighting, in seconds. Offered for the live display. */
        const val TAU_FAST_S = 0.125
    }
}

/**
 * Exponential mean-square averaging: what a sound level meter's SLOW or FAST
 * setting actually is.
 */
class ExponentialAverage(private val tauSeconds: Double, private val sampleRate: Int) {
    private var meanSquare = 0.0
    private var primed = false

    fun accept(weightedSample: Double): Double {
        val square = weightedSample * weightedSample
        if (!primed) {
            meanSquare = square
            primed = true
        } else {
            val alpha = 1.0 - kotlin.math.exp(-1.0 / (tauSeconds * sampleRate))
            meanSquare += alpha * (square - meanSquare)
        }
        return meanSquare
    }

    fun reset() {
        meanSquare = 0.0
        primed = false
    }
}

/**
 * Converts a mean square in full-scale units to a displayed level.
 *
 * [offsetDb] is the whole of the absolute calibration, and it is a property of
 * the handset, not of this code. Without a reference instrument to fix it, the
 * number this returns is meaningful in *relative* terms only — differences
 * between places and between hours — which is exactly the status of the 363
 * measurements in `data/processed/measurements.csv`. See `docs/metrology.md`.
 */
fun meanSquareToDb(meanSquare: Double, offsetDb: Double): Double {
    // Digital silence is exactly zero and its logarithm is not a number anyone can
    // read off a screen. The floor used instead is the quantisation step of the
    // 16-bit samples we are given: one least-significant bit, about -90 dB full
    // scale. Nothing quieter is representable, so nothing quieter can be measured.
    val floored = maxOf(meanSquare, QUANTISATION_FLOOR)
    return 10.0 * log10(floored) + offsetDb
}

/** Mean square of a signal of one least-significant bit, in full-scale units. */
private val QUANTISATION_FLOOR = (1.0 / 32_768.0) * (1.0 / 32_768.0)
