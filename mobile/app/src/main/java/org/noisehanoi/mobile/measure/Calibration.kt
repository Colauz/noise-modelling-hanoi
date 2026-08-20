package org.noisehanoi.mobile.measure

/**
 * Turning the arbitrary offset into a number that means something.
 *
 * The app measures a level in full-scale units and adds a constant. That
 * constant is the whole of the handset's absolute calibration, and its default
 * is a plausible guess, nothing more. Everything the app reports is therefore on
 * an arbitrary scale until somebody ties it to something.
 *
 * The tie is arithmetic, not magic: measure the same sound at the same moment
 * with a reference, and shift the constant by the difference.
 *
 *     offset' = offset + (reference − measured)
 *
 * What it is tied *to* decides what the numbers mean afterwards.
 *
 * - Against a class 1 or class 2 sound level meter, the result is absolute, and
 *   this app stops being uncalibrated.
 * - Against the campaign's own Decibel X setup on the campaign's handsets, the
 *   result is not absolute — those three phones were cross-calibrated against
 *   each other and against no standard (`docs/metrology.md`) — but it puts new
 *   measurements on the same scale as the existing 363 points, which is what
 *   makes them comparable at all. Without it there are two datasets and nothing
 *   joining them.
 *
 * A single reading is a poor tie. Traffic noise moves several decibels between
 * one 25 s window and the next, so [combine] averages repeated attempts and
 * reports the spread, which is the honest measure of how well the tie holds.
 */
object Calibration {

    data class Attempt(val measuredDb: Double, val referenceDb: Double) {
        val difference: Double get() = referenceDb - measuredDb
    }

    data class Result(
        val offsetDb: Double,
        val attempts: Int,
        /** Standard deviation of the individual differences, in dB. */
        val spreadDb: Double,
    ) {
        /**
         * Below this the attempts agree about as well as the campaign's own three
         * phones did with each other, which is the standard being matched.
         */
        val agrees: Boolean get() = attempts >= 2 && spreadDb <= 1.0
    }

    /** @param currentOffsetDb the offset the measurements in [attempts] were taken with. */
    fun combine(currentOffsetDb: Double, attempts: List<Attempt>): Result? {
        if (attempts.isEmpty()) return null
        val differences = attempts.map { it.difference }
        val mean = differences.average()
        val spread = if (differences.size < 2) 0.0 else {
            val variance = differences.sumOf { (it - mean) * (it - mean) } / (differences.size - 1)
            kotlin.math.sqrt(variance)
        }
        return Result(
            offsetDb = currentOffsetDb + mean,
            attempts = attempts.size,
            spreadDb = spread,
        )
    }
}
