package org.noisehanoi.mobile.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val Ink = Color(0xFF0B3D5C)
private val Sky = Color(0xFF3E8FB8)
private val Sand = Color(0xFFB8873E)

private val LightColors = lightColorScheme(
    primary = Ink,
    secondary = Sky,
    tertiary = Sand,
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF8FC4E0),
    secondary = Color(0xFF7FB6D4),
    tertiary = Color(0xFFE0BC85),
)

@Composable
fun NoiseHanoiTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors,
        content = content,
    )
}

/**
 * Colour bands of QCVN 26:2010, used descriptively and never as a verdict.
 *
 * `docs/metrology.md` is explicit that our quantity is not the quantity the
 * standard regulates: a 25 s A-weighted sample is not the `L_Aeq` determined
 * under TCVN 7878-2 with a class 1 or 2 meter. These are a reading aid on a
 * scale, the same use the published noise map makes of them, and no screen in
 * this app may turn them into a compliance statement.
 */
fun levelColour(db: Double): Color = when {
    db.isNaN() -> Color(0xFF9E9E9E)
    db < 55 -> Color(0xFF14654A)
    db < 65 -> Color(0xFFF5D06B)
    db < 70 -> Color(0xFFEE9422)
    db < 80 -> Color(0xFFD6541E)
    else -> Color(0xFF5E0F14)
}
