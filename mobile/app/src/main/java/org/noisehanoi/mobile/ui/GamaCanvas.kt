package org.noisehanoi.mobile.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import org.noisehanoi.mobile.gama.GamaClient

/**
 * The model's own "Noise map" display, redrawn on the phone.
 *
 * Every colour, every size and the order of the layers are taken from
 * `hanoi_noise.gaml` rather than chosen here, so that the picture is the one the
 * team already recognises from the GAMA desktop. The species are drawn in the
 * order the display block declares them — grid, buildings, roads, construction,
 * vehicles, measured points — because in GAMA that order is the stacking, and
 * getting it wrong buries the measurements under the buildings.
 *
 * Coordinates are the model's projected metres with a local origin. Nothing is
 * converted to latitude and longitude: this is a picture of what the simulation
 * is doing, and the map screen is the one that answers where on Earth.
 */
object GamaPalette {

    /** `aspect default` of NoisePoint: 5 dB bands, green to dark red. */
    fun cell(levelDb: Double): Color = when {
        levelDb < 50 -> Color(26, 152, 80)
        levelDb < 55 -> Color(102, 189, 99)
        levelDb < 60 -> Color(166, 217, 106)
        levelDb < 65 -> Color(254, 224, 82)
        levelDb < 70 -> Color(253, 174, 60)
        levelDb < 75 -> Color(230, 90, 45)
        levelDb < 80 -> Color(190, 35, 35)
        else -> Color(126, 20, 40)
    }

    /** `aspect default` of Measure. */
    fun measure(levelDb: Double): Color = when {
        levelDb >= 75 -> Color(150, 20, 30)
        levelDb >= 70 -> Color(220, 70, 40)
        levelDb >= 65 -> Color(245, 160, 50)
        levelDb >= 60 -> Color(250, 215, 70)
        else -> Color(60, 170, 90)
    }

    /** `aspect default` of Vehicle: motorcycle, car, everything heavier. */
    fun vehicle(kind: Int): Color = when (kind) {
        0 -> Color(255, 140, 0)
        1 -> Color(20, 90, 190)
        else -> Color(95, 35, 130)
    }

    fun vehicleRadiusM(kind: Int): Float = when (kind) {
        0 -> 16f
        1 -> 20f
        else -> 27f
    }

    val background = Color(250, 250, 248)
    val building = Color(232, 232, 232)
    val buildingBorder = Color(205, 205, 205)
    val road = Color(155, 155, 155)
    val constructionLoud = Color(150, 30, 30)
    val constructionQuiet = Color(190, 120, 40)
    val constructionIdle = Color(215, 215, 215)
    val outline = Color(60, 60, 60)

    /** The overlay's legend, with the label text the model prints. */
    val legend = listOf(
        "< 50" to Color(26, 152, 80),
        "50–55  (< QCVN night)" to Color(102, 189, 99),
        "55–60" to Color(166, 217, 106),
        "60–65" to Color(254, 224, 82),
        "65–70" to Color(253, 174, 60),
        "70–75  (> QCVN day)" to Color(230, 90, 45),
        "75–80" to Color(190, 35, 35),
        "> 80" to Color(126, 20, 40),
    )
}

@Composable
fun GamaCanvas(scene: GamaClient.Scene, modifier: Modifier = Modifier) {
    val xs = scene.cells.map { it.x } + scene.roads.flatten().map { it.x }
    val ys = scene.cells.map { it.y } + scene.roads.flatten().map { it.y }
    if (xs.isEmpty() || ys.isEmpty()) return

    val minX = xs.min(); val maxX = xs.max()
    val minY = ys.min(); val maxY = ys.max()
    val spanX = (maxX - minX).coerceAtLeast(1.0)
    val spanY = (maxY - minY).coerceAtLeast(1.0)

    Canvas(
        modifier
            .fillMaxWidth()
            .aspectRatio((spanX / spanY).toFloat().coerceIn(0.5f, 2.0f))
            .clip(RoundedCornerShape(8.dp)),
    ) {
        drawRect(GamaPalette.background, size = Size(size.width, size.height))

        val scale = minOf(size.width / spanX, size.height / spanY)
        // The model's y grows northwards; the canvas's grows downwards.
        fun px(x: Double) = ((x - minX) * scale).toFloat()
        fun py(y: Double) = (size.height - (y - minY) * scale).toFloat()
        fun metres(m: Float) = (m * scale).toFloat()

        // 1. NoisePoint — square(40), the 40 m grid.
        val cell = metres(40f).coerceAtLeast(1.5f)
        for (c in scene.cells) {
            drawRect(
                color = GamaPalette.cell(c.levelDb),
                topLeft = Offset(px(c.x) - cell / 2, py(c.y) - cell / 2),
                size = Size(cell, cell),
            )
        }

        // 2. Building — filled, with a border.
        for (outline in scene.buildings) {
            val path = outline.toPath(::px, ::py) ?: continue
            drawPath(path, GamaPalette.building)
            drawPath(path, GamaPalette.buildingBorder, style = Stroke(width = 1f))
        }

        // 3. Road — a thin grey line.
        for (line in scene.roads) {
            val path = line.toPath(::px, ::py, close = false) ?: continue
            drawPath(path, GamaPalette.road, style = Stroke(width = 1.5f))
        }

        // 4. ConstructionSite — square(70) turned 45 degrees: a diamond.
        val diamond = metres(35f).coerceAtLeast(4f)
        for (site in scene.constructions) {
            val cx = px(site.x); val cy = py(site.y)
            val path = Path().apply {
                moveTo(cx, cy - diamond); lineTo(cx + diamond, cy)
                lineTo(cx, cy + diamond); lineTo(cx - diamond, cy); close()
            }
            val fill = when {
                !site.active -> GamaPalette.constructionIdle
                site.loud -> GamaPalette.constructionLoud
                else -> GamaPalette.constructionQuiet
            }
            drawPath(path, fill)
            drawPath(path, GamaPalette.outline, style = Stroke(width = 1.5f))
        }

        // 5. Vehicle — a circle whose size says what it is.
        for (v in scene.vehicles) {
            val r = metres(GamaPalette.vehicleRadiusM(v.kind)).coerceAtLeast(3f)
            drawCircle(GamaPalette.vehicle(v.kind), radius = r, center = Offset(px(v.x), py(v.y)))
            drawCircle(Color.Black, radius = r, center = Offset(px(v.x), py(v.y)), style = Stroke(1f))
        }

        // 6. Measure — the 363 field points, on top of everything.
        val measureRadius = metres(22f).coerceAtLeast(2.5f)
        for (m in scene.measures) {
            val centre = Offset(px(m.x), py(m.y))
            drawCircle(GamaPalette.measure(m.levelDb), radius = measureRadius, center = centre)
            drawCircle(Color(20, 20, 20), radius = measureRadius, center = centre, style = Stroke(1f))
        }
    }
}

private fun List<GamaClient.Point>.toPath(
    px: (Double) -> Float,
    py: (Double) -> Float,
    close: Boolean = true,
): Path? {
    if (size < 2) return null
    return Path().apply {
        moveTo(px(this@toPath[0].x), py(this@toPath[0].y))
        for (i in 1 until this@toPath.size) lineTo(px(this@toPath[i].x), py(this@toPath[i].y))
        if (close) close()
    }
}
