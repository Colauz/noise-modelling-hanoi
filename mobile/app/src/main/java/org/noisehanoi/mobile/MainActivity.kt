package org.noisehanoi.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import org.noisehanoi.mobile.ui.NoiseHanoiApp
import org.noisehanoi.mobile.ui.NoiseHanoiTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            NoiseHanoiTheme {
                NoiseHanoiApp()
            }
        }
    }
}
