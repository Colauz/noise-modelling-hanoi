package org.noisehanoi.mobile

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.noisehanoi.mobile.study.PhysicalKernel
import org.noisehanoi.mobile.study.Scenario
import kotlin.math.log10
import kotlin.math.pow

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
        val ambient = 10.0.pow(56.0 / 10.0)
        for (level in listOf(53.4, 60.0, 66.7, 72.3)) {
            assertEquals(level, Scenario.scaledLevelDb(level, 1.0, ambient), 1e-9)
        }
    }

    /**
     * The damping is the whole point, and its absence is the bug this replaced.
     *
     * An earlier version subtracted the kernel's additive constant, 1.1e-10,
     * from a cell energy near 1e6 — a subtraction of nothing — and so scaled the
     * total. It therefore returned exactly 10·log10(k), and a test asserting
     * precisely that certified it. Against the real model, at a fifth of the
     * traffic, it was 3.3 dB out.
     */
    @Test
    fun `a cell above the ambience moves by less than ten log ten of k`() {
        val ambient = 10.0.pow(56.0 / 10.0)
        for (k in listOf(0.2, 0.5, 2.0, 3.0)) {
            val moved = Scenario.scaledLevelDb(65.0, k, ambient) - 65.0
            val naive = 10 * log10(k)
            assertTrue(
                "k=$k moved $moved, naive $naive",
                kotlin.math.abs(moved) < kotlin.math.abs(naive),
            )
            assertEquals("k=$k has the right sign", kotlin.math.sign(naive), kotlin.math.sign(moved), 0.0)
        }
    }

    /** A cell at or below the ambience is all ambience, and cannot move at all. */
    @Test
    fun `the residual ambience does not move`() {
        val ambient = 10.0.pow(56.0 / 10.0)
        assertEquals(56.0, Scenario.scaledLevelDb(56.0, 0.2, ambient), 1e-9)
        assertEquals(50.0, Scenario.scaledLevelDb(50.0, 3.0, ambient), 1e-9)
    }

    /**
     * The percentile and its index arithmetic are `hanoi_noise.gaml`'s, not an
     * approximation of them: for Ocean Park at 17:00 the model reports an ambience
     * of 56.08 dB and this must give the same cell.
     */
    @Test
    fun `the ambience is the fifth percentile of the levels`() {
        val levels = (0 until 100).map { 50.0 + it * 0.1 }   // 50.0 .. 59.9
        val energy = Scenario.ambientEnergy(levels)
        assertEquals(50.5, 10 * log10(energy), 1e-9)         // index int(100 * 0.05) = 5
        assertEquals(0.0, Scenario.ambientEnergy(emptyList()), 0.0)
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
