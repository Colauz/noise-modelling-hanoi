package org.noisehanoi.mobile

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.noisehanoi.mobile.study.PhysicalKernel
import org.noisehanoi.mobile.study.Scenario
import kotlin.math.log10

class ScenarioTest {

    /** The delivered parameters, from `models/hybrid_physical.json`. */
    private val kernel = PhysicalKernel(
        aHighway = 47_740_121.85653321,
        aResidential = 37_999_904.24630178,
        bBackground = 1.1063539038895509e-10,
        d0M = 5.0,
    )

    /**
     * The invariant `simulation/gama/hanoi_noise.gaml` states in its own header:
     * at k = 1 with no mitigation, the simulated map equals the predicted map. It
     * is the check that the scenario arithmetic has not quietly become a second,
     * divergent model of the same thing.
     */
    @Test
    fun `at a multiplier of one the map is unchanged`() {
        for (level in listOf(53.4, 60.0, 66.7, 72.3)) {
            assertEquals(level, Scenario.scaledLevelDb(level, 1.0, kernel.bBackground), 1e-9)
        }
    }

    /**
     * Aggregate flow noise follows 10·log10 of the flow, so doubling traffic adds
     * about 3 dB. "About", because the background does not scale — which is the
     * whole reason this function decomposes before it multiplies.
     */
    @Test
    fun `doubling the traffic adds three decibels`() {
        val doubled = Scenario.scaledLevelDb(65.0, 2.0, kernel.bBackground)
        assertEquals(65.0 + 10 * log10(2.0), doubled, 0.01)
    }

    @Test
    fun `halving the traffic takes three decibels off`() {
        val halved = Scenario.scaledLevelDb(65.0, 0.5, kernel.bBackground)
        assertEquals(65.0 - 10 * log10(2.0), halved, 0.01)
    }

    /**
     * The background is a floor. Turning the traffic down to a fifth cannot take a
     * cell below the level the kernel attributes to everything that is not
     * traffic, and a scenario that claimed otherwise would be promising silence
     * that removing cars cannot deliver.
     */
    @Test
    fun `the background is not scaled away`() {
        val floor = 10 * log10(kernel.bBackground)
        val quietest = Scenario.scaledLevelDb(60.0, Scenario.MULTIPLIER_RANGE.start.toDouble(), kernel.bBackground)
        assertTrue("floor $floor, got $quietest", quietest > floor)
    }

    /**
     * The kernel itself, at the two distances that drive it. D0 clamps the near
     * field: a line source has no singularity at zero distance, and without the
     * clamp a point on the kerb would read infinity.
     */
    @Test
    fun `the kernel falls off with distance and clamps at D0`() {
        val atKerb = kernel.levelDb(1.0, 1.0)
        val atD0 = kernel.levelDb(kernel.d0M, kernel.d0M)
        assertEquals(atD0, atKerb, 1e-9)

        val near = kernel.levelDb(10.0, 10.0)
        val far = kernel.levelDb(200.0, 200.0)
        assertTrue("near $near should exceed far $far", near > far)
        // A line source falls as 1/d, so a tenfold distance costs 10 dB.
        assertEquals(10.0, near - kernel.levelDb(100.0, 100.0), 0.2)
    }
}
