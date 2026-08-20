package org.noisehanoi.mobile.location

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Looper
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import org.noisehanoi.mobile.form.GeoPoint

/**
 * GPS fixes, straight from `LocationManager`.
 *
 * Deliberately not the fused provider: that pulls in Google Play services, which
 * an APK meant to be installed widely — including on devices without them —
 * should not require for a position it can get from the platform.
 *
 * Reports a missing or revoked permission as a flow error rather than throwing.
 * The permission can be taken away from Settings while the app sits in the
 * background, so a check before the call is a check that can go stale between the
 * asking and the using; handling it here is the only place that cannot race.
 *
 * The 10 m accuracy gate is the field protocol's, not a UI nicety. The campaign
 * reported a median declared accuracy of 4.9 m and a maximum of 9.0 m, and that
 * bound is what let the 26 points falling inside OSM building footprints be
 * explained rather than discarded (`docs/data-sources.md`). A submission that
 * silently relaxes it costs the next analysis that argument.
 */
object GpsFixes {

    const val REQUIRED_ACCURACY_M = 10.0

    @SuppressLint("MissingPermission")
    fun stream(context: Context): Flow<GeoPoint> = callbackFlow {
        val manager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager

        // Written out rather than as a SAM lambda. `LocationListener` only gained
        // default implementations for its other three methods in API 30, so on
        // API 26-29 a lambda leaves them abstract and the process dies with an
        // AbstractMethodError the first time the system reports a provider change —
        // which is to say, in the field, on the older phones, and never on a
        // current emulator.
        val listener = object : LocationListener {
            override fun onLocationChanged(location: Location) {
                trySend(location.toGeoPoint())
            }

            @Deprecated("Required by LocationListener below API 30")
            override fun onStatusChanged(provider: String?, status: Int, extras: android.os.Bundle?) = Unit

            override fun onProviderEnabled(provider: String) = Unit

            override fun onProviderDisabled(provider: String) = Unit
        }

        val providers = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
            .filter { runCatching { manager.isProviderEnabled(it) }.getOrDefault(false) }

        if (providers.isEmpty()) {
            close(IllegalStateException("Location is turned off"))
            return@callbackFlow
        }

        var registered = false
        providers.forEach { provider ->
            try {
                manager.requestLocationUpdates(provider, 1000L, 0f, listener, Looper.getMainLooper())
                // Only if it is recent. A cached fix is a starting point, not a
                // position, and one from this morning would otherwise win on
                // accuracy and be accepted as today's measurement location.
                manager.getLastKnownLocation(provider)
                    ?.takeIf { System.currentTimeMillis() - it.time <= STALE_AFTER_MS }
                    ?.let { trySend(it.toGeoPoint()) }
                registered = true
            } catch (_: SecurityException) {
                // Permission missing or revoked since the caller checked.
            } catch (_: IllegalArgumentException) {
                // The provider disappeared between the check and the request.
            }
        }
        if (!registered) {
            close(SecurityException("Location permission not granted"))
            return@callbackFlow
        }

        awaitClose { runCatching { manager.removeUpdates(listener) } }
    }

    /**
     * How old a cached fix may be and still count as "where you are". Two minutes
     * of walking in Hanoi is a couple of hundred metres, which is more than the
     * 40 m grid the predictions are read from.
     */
    const val STALE_AFTER_MS = 2 * 60 * 1000L

    private fun Location.toGeoPoint() = GeoPoint(
        latitude = latitude,
        longitude = longitude,
        altitude = if (hasAltitude()) altitude else 0.0,
        accuracyM = if (hasAccuracy()) accuracy.toDouble() else 0.0,
        timeMillis = time,
    )
}

/**
 * The three campaign sites, from `src/noise_hanoi/config.py` and
 * `scripts/01_prepare_field_data.py`.
 *
 * `01_prepare_field_data.py` already reassigns each point to the nearest of these
 * centres because the form's site label was sometimes left unchanged when the
 * team moved between areas. Suggesting the site from the fix removes that class
 * of error at the source instead of repairing it downstream.
 */
object Sites {
    data class Site(val choiceName: String, val label: String, val latitude: Double, val longitude: Double)

    val ALL = listOf(
        Site("hoan_kiem", "Hoan Kiem lake", 21.0317, 105.8514),
        Site("vinh_tuy", "Vinh Tuy area", 20.9928, 105.8690),
        Site("ocean_park", "Ocean Park", 20.9922, 105.9441),
    )

    /** Nearest campaign site, and how far the fix is from its centre, in metres. */
    fun nearest(point: GeoPoint): Pair<Site, Double> {
        var best = ALL.first()
        var bestDistance = Double.MAX_VALUE
        for (site in ALL) {
            val d = haversineMetres(point.latitude, point.longitude, site.latitude, site.longitude)
            if (d < bestDistance) {
                best = site
                bestDistance = d
            }
        }
        return best to bestDistance
    }

    /**
     * Beyond this the fix is outside every measured area. The app says so rather
     * than guessing: nothing in this project licenses a claim about a place the
     * campaign never visited.
     */
    const val SITE_RADIUS_M = 2_000.0

    fun haversineMetres(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val r = 6_371_000.0
        val dLat = Math.toRadians(lat2 - lat1)
        val dLon = Math.toRadians(lon2 - lon1)
        val a = kotlin.math.sin(dLat / 2) * kotlin.math.sin(dLat / 2) +
            kotlin.math.cos(Math.toRadians(lat1)) * kotlin.math.cos(Math.toRadians(lat2)) *
            kotlin.math.sin(dLon / 2) * kotlin.math.sin(dLon / 2)
        return 2 * r * kotlin.math.atan2(kotlin.math.sqrt(a), kotlin.math.sqrt(1 - a))
    }
}
