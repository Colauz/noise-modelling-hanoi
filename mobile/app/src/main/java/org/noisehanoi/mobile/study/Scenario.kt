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
 * The correction that matters is which energy gets multiplied. Multiplying the
 * total, background included, is what made an earlier version of the model claim
 * 7.0 dB of benefit from pedestrianisation; decomposing first gives 3.5 dB. The
 * benefit had been overstated by a factor of two, and the difference is exactly
 * this function.
 */
object Scenario {

    /**
     * @param baseLevelDb the mapped level at a cell, from the published grid.
     * @param trafficMultiplier k, the scenario's traffic volume against measured.
     * @param backgroundEnergy B of the kernel — the share that is not traffic and
     *   must not be scaled.
     */
    fun scaledLevelDb(baseLevelDb: Double, trafficMultiplier: Double, backgroundEnergy: Double): Double {
        val energy = 10.0.pow(baseLevelDb / 10.0)
        // Numerically the background is minute against the traffic term; coerce
        // rather than trust a subtraction that could go negative on a rounded level.
        val traffic = (energy - backgroundEnergy).coerceAtLeast(0.0)
        return 10.0 * log10(traffic * trafficMultiplier + backgroundEnergy)
    }

    /** The range the GAMA experiment exposes: a fifth of measured traffic to triple. */
    val MULTIPLIER_RANGE = 0.2f..3.0f
}
