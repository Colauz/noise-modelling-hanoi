package org.noisehanoi.mobile.study

import kotlin.math.log10
import kotlin.math.pow

/**
 * The delivered model, and the one scenario the simulation actually supports.
 *
 * The map the app ships was produced by a three-parameter line-source kernel,
 *
 *     E(x) = A_hw / max(d_hw, D0) + A_res / max(d_res, D0) + B
 *     L(x) = 10 * log10( E(x) )
 *
 * fitted on the 363 measurements and chosen by `04_evaluate_models.py` over six
 * candidates under buffered leave-one-out — ahead of every learned model,
 * including the physics-plus-ML hybrid the team had recommended to itself. The
 * residual booster is trained and saved but not applied.
 *
 * Two things follow for this class. The kernel is three constants, so the app
 * needs no ML runtime. And the levels in the grid are already the model's
 * output, so predicting at a point is reading the cell, not re-deriving it.
 */
data class PhysicalKernel(
    val aHighway: Double,
    val aResidential: Double,
    val bBackground: Double,
    val d0M: Double,
) {
    /** Level at a point, from its distances to the two road classes, in metres. */
    fun levelDb(distanceHighwayM: Double, distanceResidentialM: Double): Double {
        val energy = aHighway / maxOf(distanceHighwayM, d0M) +
            aResidential / maxOf(distanceResidentialM, d0M) +
            bBackground
        return 10.0 * log10(energy)
    }
}

/**
 * Tier 1 of the GAMA model, recomputed on the phone.
 *
 * GAMA is an Eclipse desktop platform and does not run on Android, but tier 1 is
 * not a simulation of agents: it is a traffic multiplier applied to a grid the
 * app already carries. Doing that arithmetic here gives the same interaction,
 * offline, and — unlike a screen recording — it answers at whatever value of the
 * multiplier the user chooses.
 *
 * The correction that matters is which energy gets multiplied, and what counts
 * as residual. Multiplying the total is what made an earlier version of the model
 * claim 7.0 dB of benefit from pedestrianisation where the honest figure is 3.5;
 * the benefit had been overstated by a factor of two.
 *
 * The first version of this class reproduced that error while claiming not to. It
 * subtracted the kernel's additive constant `B_background`, 1.1e-10, from a cell
 * energy on the order of 1e6 — a subtraction of nothing — and so scaled the total
 * after all. Driving the real model exposed it: at a fifth of the traffic GAMA
 * gives -3.7 dB and this gave -7.0, the very figure the model had been corrected
 * away from.
 *
 * The residual is the zone's ambience, a low percentile of its own levels, not a
 * constant of the kernel. With that, the two agree to within 0.2 dB from x0.2 to
 * x3 — checked against `hanoi_noise.gaml` running under gama-server.
 */
object Scenario {

    /**
     * Low percentile of a zone's levels, taken as its non-road residual ambience.
     *
     * `AMBIENT_PCT` in `hanoi_noise.gaml`, and the index arithmetic below is that
     * model's, reproduced rather than approximated: the quietest cells of a zone
     * are those where traffic contributes least, so their level stands in for the
     * ventilation, activity and distant noise that a traffic scenario must not
     * move. Checked against the running model — for Ocean Park at 17:00 both give
     * 56.08 dB.
     */
    const val AMBIENT_PERCENTILE = 0.05

    /** Residual energy of a zone, from the levels of its cells at one hour. */
    fun ambientEnergy(levelsDb: List<Double>): Double {
        if (levelsDb.isEmpty()) return 0.0
        val sorted = levelsDb.sorted()
        val index = (sorted.size * AMBIENT_PERCENTILE).toInt().coerceIn(0, sorted.size - 1)
        return 10.0.pow(sorted[index] / 10.0)
    }

    /**
     * @param baseLevelDb the mapped level at a cell, from the published grid.
     * @param trafficMultiplier k, the scenario's traffic volume against measured.
     * @param ambientEnergy the zone's residual energy, from [ambientEnergy]. What
     *   is *not* traffic, and is therefore not scaled.
     */
    fun scaledLevelDb(baseLevelDb: Double, trafficMultiplier: Double, ambientEnergy: Double): Double {
        val energy = 10.0.pow(baseLevelDb / 10.0)
        // Never more residual than the cell itself holds; a cell quieter than the
        // zone's ambience is all ambience.
        val residual = minOf(ambientEnergy, energy)
        val traffic = energy - residual
        return 10.0 * log10(residual + trafficMultiplier * traffic)
    }

    /** The range the GAMA experiment exposes: a fifth of measured traffic to triple. */
    val MULTIPLIER_RANGE = 0.2f..3.0f
}
