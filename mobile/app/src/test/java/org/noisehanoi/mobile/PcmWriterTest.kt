package org.noisehanoi.mobile

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.noisehanoi.mobile.measure.PcmWriter
import org.noisehanoi.mobile.measure.meanSquareToDb
import java.io.ByteArrayOutputStream

class PcmWriterTest {

    /**
     * The byte order is the whole reason this class exists. A swapped stream still
     * plays, still has the right length, and still passes every check the app makes
     * of it — it is simply noise. So the expectation is written down here as
     * literal bytes.
     */
    @Test
    fun `samples are written little-endian`() {
        val out = ByteArrayOutputStream()
        PcmWriter.write(out, shortArrayOf(0x0102, 0x7FFF, -1, 0), 4)
        val bytes = out.toByteArray().map { it.toInt() and 0xFF }
        assertEquals(
            listOf(
                0x02, 0x01,   // 0x0102 low byte first
                0xFF, 0x7F,   // full positive scale
                0xFF, 0xFF,   // -1
                0x00, 0x00,   // silence, the one value a swap cannot corrupt
            ),
            bytes,
        )
    }

    @Test
    fun `only the requested number of samples is written`() {
        val out = ByteArrayOutputStream()
        PcmWriter.write(out, ShortArray(64) { 1 }, 10)
        assertEquals(20, out.size())
    }

    /**
     * `AudioRecord` on a muted or absent microphone returns exact zeros, and
     * log10(0) is not something to put on a screen.
     */
    @Test
    fun `digital silence reads as the quantisation floor, not minus infinity`() {
        val db = meanSquareToDb(0.0, 94.0)
        assertTrue(db.isFinite())
        assertEquals(94.0 - 90.3, db, 0.2)
    }

    @Test
    fun `full scale reads as the offset itself`() {
        assertEquals(94.0, meanSquareToDb(1.0, 94.0), 1e-9)
    }
}
