package org.noisehanoi.mobile.measure

import java.io.OutputStream

/**
 * Writes 16-bit PCM in the byte order the rest of the platform speaks.
 *
 * Its own file, and its own test, because getting this wrong is silent. The first
 * version used `DataOutputStream.writeShort`, which is big-endian by
 * specification, while `AudioRecord` hands out native-endian samples and
 * `MediaCodec` reads little-endian: every sample went out byte-swapped and the
 * clip that reached the server was noise. The measurement was unaffected — it is
 * computed from the shorts, never from the file — so nothing on screen looked
 * wrong. And an emulator records silence, which is a run of zeros, and zeros
 * survive a byte swap unharmed. Neither the app nor the test device could show
 * it; only a written-down expectation about the bytes can.
 */
object PcmWriter {

    /**
     * Appends `buffer[from until count]` to [out], little-endian.
     *
     * [from] exists so the warm-up the meter discards is discarded from the clip
     * as well: the audio submitted is then exactly the audio that was measured.
     */
    fun write(out: OutputStream, buffer: ShortArray, count: Int, from: Int = 0) {
        for (i in from until count) {
            val sample = buffer[i].toInt()
            out.write(sample and 0xFF)
            out.write((sample shr 8) and 0xFF)
        }
    }
}
