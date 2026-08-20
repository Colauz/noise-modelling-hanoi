package org.noisehanoi.mobile

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.noisehanoi.mobile.measure.Calibration
import org.noisehanoi.mobile.settings.Settings

class CalibrationTest {

    @Test
    fun `the offset moves by the difference from the reference`() {
        val result = Calibration.combine(
            currentOffsetDb = 94.0,
            attempts = listOf(Calibration.Attempt(measuredDb = 68.0, referenceDb = 72.0)),
        )!!
        assertEquals(98.0, result.offsetDb, 1e-9)
    }

    /** Applying the result must make the next measurement land on the reference. */
    @Test
    fun `a calibrated phone then reads what the reference read`() {
        val measured = 68.0
        val reference = 72.0
        val result = Calibration.combine(94.0, listOf(Calibration.Attempt(measured, reference)))!!
        // The same acoustic signal, re-expressed with the new offset.
        val recomputed = measured - 94.0 + result.offsetDb
        assertEquals(reference, recomputed, 1e-9)
    }

    @Test
    fun `repeated attempts are averaged and their spread reported`() {
        val result = Calibration.combine(
            currentOffsetDb = 90.0,
            attempts = listOf(
                Calibration.Attempt(60.0, 64.0),   // +4
                Calibration.Attempt(62.0, 65.0),   // +3
                Calibration.Attempt(61.0, 66.0),   // +5
            ),
        )!!
        assertEquals(94.0, result.offsetDb, 1e-9)
        assertEquals(1.0, result.spreadDb, 1e-9)
        assertEquals(3, result.attempts)
    }

    /**
     * One reading is not a calibration. Traffic noise moves several decibels
     * between one 25 s window and the next, so a single agreement can be luck.
     */
    @Test
    fun `a single attempt does not count as agreement`() {
        val single = Calibration.combine(94.0, listOf(Calibration.Attempt(68.0, 72.0)))!!
        assertFalse(single.agrees)
    }

    /**
     * One decibel is the tolerance the campaign's own three handsets were trimmed
     * to. Attempts that scatter more than that are not describing a constant.
     */
    @Test
    fun `attempts that scatter more than a decibel do not agree`() {
        val tight = Calibration.combine(
            94.0,
            listOf(Calibration.Attempt(60.0, 64.0), Calibration.Attempt(60.0, 64.5)),
        )!!
        assertTrue(tight.agrees)

        val loose = Calibration.combine(
            94.0,
            listOf(Calibration.Attempt(60.0, 64.0), Calibration.Attempt(60.0, 70.0)),
        )!!
        assertFalse(loose.agrees)
    }

    @Test
    fun `no attempts is no result`() {
        assertNull(Calibration.combine(94.0, emptyList()))
    }

    /**
     * A calibration can legitimately land outside the middle of the slider's
     * range, and the stored offset has to survive being shown next to it. Storing
     * a value the slider cannot represent is how the first touch of that slider
     * silently replaces a calibration with its own maximum.
     */
    @Test
    fun `the slider range covers a plausible calibration`() {
        val quietHandsetOnALoudStreet =
            Calibration.combine(94.0, listOf(Calibration.Attempt(48.0, 78.0)))!!
        assertTrue(
            "offset ${quietHandsetOnALoudStreet.offsetDb} outside ${Settings.OFFSET_RANGE}",
            quietHandsetOnALoudStreet.offsetDb.toFloat() in Settings.OFFSET_RANGE,
        )
    }
}
