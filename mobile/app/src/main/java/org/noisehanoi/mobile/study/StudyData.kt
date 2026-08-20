package org.noisehanoi.mobile.study

import android.content.Context
import org.json.JSONObject

/** One 40 m cell of the published map, with its level for each mapped hour. */
data class GridCell(
    val site: String,
    val latitude: Double,
    val longitude: Double,
    /** Indexed by hour − [NoiseMap.FIRST_HOUR]. */
    val levelsByHour: DoubleArray,
) {
    fun levelAt(hour: Int): Double = levelsByHour[hour - NoiseMap.FIRST_HOUR]

    // Generated because the class holds an array; identity would be wrong for a
    // value type the UI keys on.
    override fun equals(other: Any?): Boolean =
        other is GridCell && site == other.site &&
            latitude == other.latitude && longitude == other.longitude

    override fun hashCode(): Int = (site.hashCode() * 31 + latitude.hashCode()) * 31 + longitude.hashCode()
}

/** One field measurement, from the published `measurements.csv`. */
data class Measurement(
    val site: String,
    val latitude: Double,
    val longitude: Double,
    val levelDb: Double,
    val hour: Int,
    val noiseClass: String,
)

data class SiteExtent(
    val site: String,
    val minLatitude: Double,
    val maxLatitude: Double,
    val minLongitude: Double,
    val maxLongitude: Double,
) {
    operator fun contains(point: Pair<Double, Double>): Boolean =
        point.first in minLatitude..maxLatitude && point.second in minLongitude..maxLongitude
}

class NoiseMap(val cells: List<GridCell>) {

    val sites: List<String> = cells.map { it.site }.distinct().sorted()

    private val bySite: Map<String, List<GridCell>> = cells.groupBy { it.site }

    fun cellsOf(site: String): List<GridCell> = bySite[site].orEmpty()

    /**
     * Residual energy of a site at one hour, for the traffic scenario.
     *
     * Computed from the cells themselves, the way `hanoi_noise.gaml` does it, so
     * that the app's scenario and the model's agree instead of merely resembling
     * each other.
     */
    fun ambientEnergyOf(site: String, hour: Int): Double =
        Scenario.ambientEnergy(cellsOf(site).map { it.levelAt(hour) })

    fun extentOf(site: String): SiteExtent {
        val cs = cellsOf(site)
        return SiteExtent(
            site = site,
            minLatitude = cs.minOf { it.latitude },
            maxLatitude = cs.maxOf { it.latitude },
            minLongitude = cs.minOf { it.longitude },
            maxLongitude = cs.maxOf { it.longitude },
        )
    }

    /**
     * The nearest cell to a position, and its distance in metres — or null when
     * the position is outside every mapped area.
     *
     * The refusal is the point. `GRID_MARGIN_M` in `config.py` puts the map's edge
     * 400 m beyond the sampled envelope and the repository's rule is to predict no
     * further. An app installed across Hanoi will be opened where the campaign
     * never went, and a kernel fitted 12 km away has nothing to say there.
     */
    fun nearestCell(latitude: Double, longitude: Double): Pair<GridCell, Double>? {
        var best: GridCell? = null
        var bestDistance = Double.MAX_VALUE
        for (cell in cells) {
            val d = metresBetween(latitude, longitude, cell.latitude, cell.longitude)
            if (d < bestDistance) {
                best = cell
                bestDistance = d
            }
        }
        val cell = best ?: return null
        return if (bestDistance <= OUTSIDE_MAP_M) cell to bestDistance else null
    }

    companion object {
        /** The map covers 05:00–21:00, the hours the campaign worked. */
        const val FIRST_HOUR = 5
        const val LAST_HOUR = 21
        val HOURS = FIRST_HOUR..LAST_HOUR

        /** Grid resolution, `GRID_STEP_M` in `src/noise_hanoi/config.py`. */
        const val CELL_SIZE_M = 40.0

        /**
         * Beyond this from the nearest cell, the app says it does not know. Two
         * cells of slack, so standing at the very edge of a mapped area still
         * reads, and a street away does not.
         */
        const val OUTSIDE_MAP_M = 2 * CELL_SIZE_M
    }
}

fun metresBetween(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
    val r = 6_371_000.0
    val dLat = Math.toRadians(lat2 - lat1)
    val dLon = Math.toRadians(lon2 - lon1)
    val a = kotlin.math.sin(dLat / 2) * kotlin.math.sin(dLat / 2) +
        kotlin.math.cos(Math.toRadians(lat1)) * kotlin.math.cos(Math.toRadians(lat2)) *
        kotlin.math.sin(dLon / 2) * kotlin.math.sin(dLon / 2)
    return 2 * r * kotlin.math.atan2(kotlin.math.sqrt(a), kotlin.math.sqrt(1 - a))
}

/** The headline numbers, read from `metrics.json` and never retyped. */
data class Headline(
    val nMeasurements: Int,
    val dbMin: Double,
    val dbMax: Double,
    val dateMin: String,
    val dateMax: String,
    val deliveredLabel: String,
    val sites: Map<String, Int>,
    /** Model label to R², under each of the three cross-validation protocols. */
    val protocols: List<Protocol>,
) {
    data class Protocol(val key: String, val label: String, val models: List<ModelScore>)
    data class ModelScore(val key: String, val label: String, val r2: Double, val mae: Double)
}

/**
 * Everything the study screens read, loaded once from the assets the build copied
 * out of the repository.
 */
class StudyData private constructor(
    val map: NoiseMap,
    val measurements: List<Measurement>,
    val kernel: PhysicalKernel,
    val headline: Headline,
) {
    companion object {
        @Volatile
        private var instance: StudyData? = null

        fun load(context: Context): StudyData =
            instance ?: synchronized(this) {
                instance ?: build(context.applicationContext).also { instance = it }
            }

        private fun build(context: Context): StudyData {
            val assets = context.assets
            val map = assets.open("hanoi_noise_map.csv").use { readGrid(it.bufferedReader().readLines()) }
            val measurements =
                assets.open("measurements.csv").use { readMeasurements(it.bufferedReader().readLines()) }
            val kernel = assets.open("hybrid_physical.json").use { readKernel(it.bufferedReader().readText()) }
            val headline = assets.open("metrics.json").use { readHeadline(it.bufferedReader().readText()) }
            return StudyData(map, measurements, kernel, headline)
        }

        private fun readGrid(lines: List<String>): NoiseMap {
            val header = lines.first().split(',')
            val siteAt = header.indexOf("site")
            val lonAt = header.indexOf("longitude")
            val latAt = header.indexOf("latitude")
            val hourAt = NoiseMap.HOURS.map { header.indexOf("h$it") }
            val cells = ArrayList<GridCell>(lines.size)
            for (line in lines.drop(1)) {
                if (line.isBlank()) continue
                val f = line.split(',')
                cells += GridCell(
                    site = f[siteAt],
                    latitude = f[latAt].toDouble(),
                    longitude = f[lonAt].toDouble(),
                    levelsByHour = DoubleArray(hourAt.size) { f[hourAt[it]].toDouble() },
                )
            }
            return NoiseMap(cells)
        }

        private fun readMeasurements(lines: List<String>): List<Measurement> {
            val header = lines.first().split(',')
            val latAt = header.indexOf("latitude")
            val lonAt = header.indexOf("longitude")
            val dbAt = header.indexOf("noise_dB")
            val siteAt = header.indexOf("site")
            val hourAt = header.indexOf("hour")
            val classAt = header.indexOf("class")
            return lines.drop(1).mapNotNull { line ->
                if (line.isBlank()) return@mapNotNull null
                val f = line.split(',')
                val db = f.getOrNull(dbAt)?.toDoubleOrNull() ?: return@mapNotNull null
                Measurement(
                    site = f[siteAt],
                    latitude = f[latAt].toDouble(),
                    longitude = f[lonAt].toDouble(),
                    levelDb = db,
                    hour = f.getOrNull(hourAt)?.toIntOrNull() ?: -1,
                    noiseClass = f.getOrNull(classAt).orEmpty(),
                )
            }
        }

        private fun readKernel(json: String): PhysicalKernel {
            val o = JSONObject(json)
            return PhysicalKernel(
                aHighway = o.getDouble("A_highway"),
                aResidential = o.getDouble("A_residential"),
                bBackground = o.getDouble("B_background"),
                d0M = o.getDouble("D0_m"),
            )
        }

        private fun readHeadline(json: String): Headline {
            val root = JSONObject(json)
            val meta = root.getJSONObject("meta")
            val sites = LinkedHashMap<String, Int>()
            val sitesJson = meta.getJSONObject("sites")
            sitesJson.keys().forEach { sites[it] = sitesJson.getInt(it) }

            val protocols = listOf("bloo", "block_cv", "loso").mapNotNull { key ->
                val block = root.optJSONObject(key) ?: return@mapNotNull null
                val models = block.optJSONObject("models") ?: return@mapNotNull null
                val scores = models.keys().asSequence().map { modelKey ->
                    val m = models.getJSONObject(modelKey)
                    Headline.ModelScore(
                        key = modelKey,
                        label = m.optString("label", modelKey),
                        r2 = m.optDouble("r2", Double.NaN),
                        mae = m.optDouble("mae", Double.NaN),
                    )
                }.sortedByDescending { it.r2 }.toList()
                Headline.Protocol(key, block.optString("label", key), scores)
            }

            return Headline(
                nMeasurements = meta.optInt("n_measurements"),
                dbMin = meta.optDouble("db_min"),
                dbMax = meta.optDouble("db_max"),
                dateMin = meta.optString("date_min"),
                dateMax = meta.optString("date_max"),
                deliveredLabel = meta.optString("delivered_label"),
                sites = sites,
                protocols = protocols,
            )
        }
    }
}
