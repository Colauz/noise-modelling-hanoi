package org.noisehanoi.mobile

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.noisehanoi.mobile.measure.AWeighting
import kotlin.math.PI
import kotlin.math.log10
import kotlin.math.sin

class AWeightingTest {

    private val sampleRate = 48_000

    /** IEC 61672-1 table 3, the A-weighting curve at the nominal frequencies. */
    private val reference = mapOf(
        31.5 to -39.4, 63.0 to -26.2, 125.0 to -16.1, 250.0 to -8.6,
        500.0 to -3.2, 1000.0 to 0.0, 2000.0 to 1.2, 4000.0 to 1.0,
        8000.0 to -1.1, 12500.0 to -4.3,
    )

    /**
     * 0.7 dB is what this design achieves at 48 kHz over the whole range, and it
     * is well inside the class 1 tolerance, which is ±1.0 dB through 4 kHz and
     * widens above it. Tightening this bound is not a matter of tuning: the
     * residual is bilinear frequency warping, and closing it needs a different
     * design.
     */
    @Test
    fun `frequency response matches the standard curve`() {
        val weighting = AWeighting(sampleRate)
        for ((frequency, expected) in reference) {
            val actual = weighting.responseDb(frequency, sampleRate)
            assertEquals("at $frequency Hz", expected, actual, 0.7)
        }
    }

    /**
     * Where the design gives ground, and how much, so that a later change to the
     * filter cannot quietly make it worse. -6.6 dB is the standard's value at
     * 16 kHz; class 1 allows +3.0/-16 there.
     */
    @Test
    fun `deviation near Nyquist is bounded and documented`() {
        val weighting = AWeighting(sampleRate)
        val at16k = weighting.responseDb(16000.0, sampleRate)
        assertEquals(-6.6 - 3.1, at16k, 0.5)
    }

    @Test
    fun `gain is exactly unity at 1 kHz`() {
        val weighting = AWeighting(sampleRate)
        assertEquals(0.0, weighting.responseDb(1000.0, sampleRate), 1e-9)
    }

    /**
     * The filter run over a real signal has to agree with its own frequency
     * response, otherwise the two are describing different filters.
     */
    @Test
    fun `filtering a tone attenuates it by the curve value`() {
        for (frequency in listOf(125.0, 1000.0, 4000.0)) {
            val weighting = AWeighting(sampleRate)
            val n = sampleRate * 2
            var sumSquares = 0.0
            var counted = 0
            for (i in 0 until n) {
                val x = sin(2 * PI * frequency * i / sampleRate)
                val y = weighting.filter(x)
                if (i > sampleRate / 2) {   // let the transient settle
                    sumSquares += y * y
                    counted++
                }
            }
            // A unit sine has mean square 0.5; the gain is the ratio of the two.
            val measuredDb = 10 * log10(sumSquares / counted / 0.5)
            assertEquals("at $frequency Hz", weighting.responseDb(frequency, sampleRate), measuredDb, 0.2)
        }
    }

    @Test
    fun `infrasound is rejected, which is the point of the weighting`() {
        val weighting = AWeighting(sampleRate)
        assertTrue(weighting.responseDb(10.0, sampleRate) < -60.0)
    }
}
