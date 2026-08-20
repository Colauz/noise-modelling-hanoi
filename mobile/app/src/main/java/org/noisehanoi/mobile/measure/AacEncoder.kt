package org.noisehanoi.mobile.measure

import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import java.io.File
import java.nio.ByteBuffer

/**
 * Turns the raw PCM written by [SplMeter] into the `.m4a` that goes up with the
 * submission.
 *
 * Size is the reason this exists. Twenty-five seconds of 48 kHz mono PCM is
 * 2.4 MB; the same clip as 64 kbit/s AAC is about 200 kB. Multiply by the
 * campaign the app is meant to open up and the difference decides whether the
 * receiving account's storage quota survives the first week.
 */
object AacEncoder {

    private const val MIME = MediaFormat.MIMETYPE_AUDIO_AAC
    private const val BIT_RATE = 64_000
    private const val TIMEOUT_US = 10_000L

    /**
     * @throws IllegalStateException if the encoder never produced a track, which
     *   leaves a file that exists, is empty, and would be uploaded as if it were a
     *   recording. Failing loudly here is what lets the caller keep the level and
     *   say the clip is missing.
     */
    fun encode(rawPcm: File, output: File, sampleRate: Int) {
        val format = MediaFormat.createAudioFormat(MIME, sampleRate, 1).apply {
            setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC)
            setInteger(MediaFormat.KEY_BIT_RATE, BIT_RATE)
            setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, 16 * 1024)
        }
        val codec = MediaCodec.createEncoderByType(MIME)
        codec.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        codec.start()

        val muxer = MediaMuxer(output.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        var trackIndex = -1
        var muxing = false
        val info = MediaCodec.BufferInfo()

        try {
            rawPcm.inputStream().buffered().use { input ->
                val chunk = ByteArray(4096)
                var presentationUs = 0L
                var inputDone = false

                while (true) {
                    if (!inputDone) {
                        val index = codec.dequeueInputBuffer(TIMEOUT_US)
                        if (index >= 0) {
                            val buffer: ByteBuffer = codec.getInputBuffer(index)!!
                            buffer.clear()
                            val read = input.read(chunk, 0, minOf(chunk.size, buffer.remaining()))
                            if (read <= 0) {
                                codec.queueInputBuffer(index, 0, 0, presentationUs, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                                inputDone = true
                            } else {
                                buffer.put(chunk, 0, read)
                                codec.queueInputBuffer(index, 0, read, presentationUs, 0)
                                // 2 bytes per mono sample.
                                presentationUs += 1_000_000L * (read / 2) / sampleRate
                            }
                        }
                    }

                    when (val index = codec.dequeueOutputBuffer(info, TIMEOUT_US)) {
                        MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                            trackIndex = muxer.addTrack(codec.outputFormat)
                            muxer.start()
                            muxing = true
                        }
                        // Nothing ready yet. `info` still holds the previous callback's
                        // flags, so it says nothing about now; the end-of-stream break
                        // below is the only one that may fire.
                        MediaCodec.INFO_TRY_AGAIN_LATER -> Unit
                        else -> if (index >= 0) {
                            val encoded = codec.getOutputBuffer(index)!!
                            if (info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG == 0 && info.size > 0 && muxing) {
                                encoded.position(info.offset)
                                encoded.limit(info.offset + info.size)
                                muxer.writeSampleData(trackIndex, encoded, info)
                            }
                            codec.releaseOutputBuffer(index, false)
                            if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) break
                        }
                    }
                }
            }

        } finally {
            // Both hold native resources. An exception thrown out of the loop must
            // not leak an encoder for the rest of the process's life.
            runCatching { codec.stop() }
            codec.release()
            if (muxing) runCatching { muxer.stop() }
            muxer.release()
        }

        if (!muxing || output.length() == 0L) {
            output.delete()
            error("the encoder produced no audio track")
        }
    }
}
