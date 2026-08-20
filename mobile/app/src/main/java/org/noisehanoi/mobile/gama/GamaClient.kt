package org.noisehanoi.mobile.gama

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withTimeoutOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Drives a running `gama-server` over its websocket protocol.
 *
 * GAMA is an Eclipse desktop platform and does not run on Android. What this
 * talks to is a GAMA process started elsewhere with
 * `gama-headless.sh -socket <port>`, on a machine the phone can reach. The
 * consequence is worth stating plainly: everything here needs a network and a
 * server that is switched on, unlike the map the app carries, which does not.
 *
 * The protocol is small — JSON objects with a `type`, answered by a message whose
 * own `type` comes from a fixed vocabulary — so it is implemented directly rather
 * than through a client library, of which there are Python and TypeScript ones
 * and no Kotlin.
 *
 * Two things learned by driving it against GAMA 2025.6.4 rather than reading
 * about it, and both are load-bearing:
 *
 * - **The experiment must have no display.** `hanoi_noise_sim` is `type: gui`
 *   with three of them, one OpenGL; loading it makes the server create a render
 *   surface, take the main thread on macOS, and stop answering the socket
 *   entirely. `check` — the model's own display-free control experiment — loads
 *   in about two seconds.
 * - **`step` needs `sync`.** Without it the command returns immediately, the
 *   cycle does not advance, and every indicator reads zero, which looks exactly
 *   like a model that does not work.
 */
class GamaClient(
    private val http: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        // The server does not answer pings while it compiles a model, and a read
        // timeout here is indistinguishable from a broken server.
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(0, TimeUnit.MILLISECONDS)
        .build(),
) {

    data class Indicator(val name: String, val expression: String)

    sealed interface Outcome {
        data class Ok(val content: String) : Outcome
        data class Failed(val type: String, val detail: String) : Outcome
    }

    private var socket: WebSocket? = null
    private val incoming = Channel<JSONObject>(Channel.UNLIMITED)
    private val turn = Mutex()
    private var connected: CompletableDeferred<Result<Unit>>? = null

    val isConnected: Boolean get() = socket != null

    /** Opens the socket and waits for the server's greeting. */
    suspend fun connect(url: String, timeoutMs: Long = 20_000): Result<Unit> {
        close()
        val ready = CompletableDeferred<Result<Unit>>()
        connected = ready
        // Say what is wrong, not merely that something is. An empty field and a
        // typo are different mistakes and the user can only fix the one they are
        // told about.
        val trimmed = url.trim()
        if (trimmed.isBlank()) {
            return Result.failure(
                IllegalArgumentException(
                    "No server address. Enter the address of the machine running gama-server, " +
                        "as ws://host:port."
                )
            )
        }
        if (!trimmed.startsWith("ws://") && !trimmed.startsWith("wss://")) {
            return Result.failure(
                IllegalArgumentException("The address must start with ws:// or wss:// — got \"$trimmed\".")
            )
        }
        val request = runCatching { Request.Builder().url(trimmed).build() }
            .getOrElse {
                return Result.failure(
                    IllegalArgumentException("\"$trimmed\" is not a usable address: ${it.message}")
                )
            }

        socket = http.newWebSocket(request, object : WebSocketListener() {
            override fun onMessage(webSocket: WebSocket, text: String) {
                val message = runCatching { JSONObject(text) }.getOrNull() ?: return
                if (message.optString("type") == GREETING) {
                    ready.complete(Result.success(Unit))
                } else {
                    incoming.trySend(message)
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                ready.complete(Result.failure(t))
                socket = null
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                socket = null
            }
        })

        val result = withTimeoutOrNull(timeoutMs) { ready.await() }
        if (result == null) {
            close()
            return Result.failure(IllegalStateException("No greeting from $url within ${timeoutMs / 1000}s"))
        }
        if (result.isFailure) socket = null
        return result
    }

    fun close() {
        socket?.close(1000, null)
        socket = null
        while (incoming.tryReceive().isSuccess) Unit
    }

    /**
     * Loads [experiment] from [modelPath] — a path **on the server's filesystem**,
     * not the phone's — and returns the experiment id every later command needs.
     */
    /**
     * A parameter of the experiment, with the type GAMA expects to be told.
     *
     * Parameters are applied by `load` and by nothing else. Setting one through
     * an `expression` — `mitigation <- 'pietonnisation'` — is accepted, changes
     * nothing, and leaves every indicator at its previous value: the scenario
     * looks applied and is not.
     */
    sealed interface Parameter {
        val name: String

        data class Number(override val name: String, val value: Double) : Parameter
        data class Text(override val name: String, val value: String) : Parameter
    }

    suspend fun load(
        modelPath: String,
        experiment: String,
        parameters: List<Parameter> = emptyList(),
        timeoutMs: Long = 300_000,
    ): Outcome {
        val params = JSONArray()
        parameters.forEach { parameter ->
            val entry = JSONObject().put("name", parameter.name)
            when (parameter) {
                is Parameter.Number -> entry.put("type", "float").put("value", parameter.value)
                is Parameter.Text -> entry.put("type", "string").put("value", parameter.value)
            }
            params.put(entry)
        }
        return command(
            JSONObject()
                .put("type", "load")
                .put("model", modelPath)
                .put("experiment", experiment)
                .put("console", false).put("status", false)
                .put("dialog", false).put("runtime", false)
                .apply { if (parameters.isNotEmpty()) put("parameters", params) },
            timeoutMs,
        )
    }

    /** Runs the simulation continuously until [pause]. */
    suspend fun play(experimentId: String, timeoutMs: Long = 60_000): Outcome =
        command(JSONObject().put("type", "play").put("exp_id", experimentId), timeoutMs)

    suspend fun pause(experimentId: String, timeoutMs: Long = 60_000): Outcome =
        command(JSONObject().put("type", "pause").put("exp_id", experimentId), timeoutMs)

    /** Advances one cycle and waits for it. Without `sync` nothing moves. */
    suspend fun step(experimentId: String, timeoutMs: Long = 300_000): Outcome =
        command(JSONObject().put("type", "step").put("exp_id", experimentId).put("sync", true), timeoutMs)

    /** Evaluates a GAML expression inside the running experiment. */
    suspend fun evaluate(experimentId: String, expression: String, timeoutMs: Long = 120_000): Outcome =
        command(
            JSONObject().put("type", "expression").put("exp_id", experimentId).put("expr", expression),
            timeoutMs,
        )

    /**
     * Everything the model's "Noise map" display draws, pulled in one round.
     *
     * The layers, their order and their colours are `hanoi_noise.gaml`'s, not an
     * interpretation of them: the aspects are read from the model and reproduced,
     * so that what appears on the phone is the display the team already knows from
     * the GAMA desktop rather than a second, similar-looking picture.
     *
     * Static layers — buildings, roads, construction sites, the measured points —
     * are pulled once when the scenario loads. Only the grid and the vehicles move.
     */
    data class Scene(
        val cells: List<Cell> = emptyList(),
        val roads: List<List<Point>> = emptyList(),
        val buildings: List<List<Point>> = emptyList(),
        val constructions: List<Construction> = emptyList(),
        val measures: List<Cell> = emptyList(),
        val vehicles: List<Vehicle> = emptyList(),
    ) {
        val isEmpty: Boolean get() = cells.isEmpty() && roads.isEmpty() && buildings.isEmpty()
    }

    data class Point(val x: Double, val y: Double)

    /** `kind`: 0 motorcycle, 1 car, 2 bus or truck — the model's own three. */
    data class Vehicle(val x: Double, val y: Double, val kind: Int)

    data class Construction(val x: Double, val y: Double, val loud: Boolean, val active: Boolean)

    /** The layers that never move. Pulled once per scenario. */
    suspend fun pullStatic(experimentId: String): Scene = Scene(
        roads = pullPolygons(experimentId, "Road collect (each.shape.points collect [each.x, each.y])"),
        buildings = pullPolygons(experimentId, "Building collect (each.shape.points collect [each.x, each.y])"),
        measures = pullCells(experimentId, "Measure collect [each.location.x, each.location.y, each.dB]"),
        constructions = pullCells(
            experimentId,
            "ConstructionSite collect [each.location.x, each.location.y, (each.loud = 1 ? 1.0 : 0.0)]",
        ).map { Construction(it.x, it.y, loud = it.levelDb > 0.5, active = true) },
    )

    /**
     * The simulated field itself: every cell's position and current level, as the
     * running model holds them.
     *
     * Pulled as one GAML expression rather than agent by agent — the whole Ocean
     * Park grid comes back as 2544 triples in about 95 kB, fast enough to redraw
     * after every step. Coordinates are the model's own projected metres with a
     * local origin, which is all a picture needs; nothing here converts to
     * latitude and longitude, and nothing should, because the point is to show
     * what the simulation is doing rather than where it is on Earth.
     */
    suspend fun pullField(experimentId: String): List<Cell> = pullCells(
        experimentId,
        // `effective_dB`, which is what the aspect colours by: it carries the
        // construction contribution, where `background_dB` does not.
        "NoisePoint collect [each.location.x, each.location.y, each.effective_dB]",
    )

    suspend fun pullVehicles(experimentId: String): List<Vehicle> = pullCells(
        experimentId,
        "Vehicle collect [each.location.x, each.location.y, " +
            "(each.v_type = 'moto' ? 0.0 : (each.v_type = 'car' ? 1.0 : 2.0))]",
    ).map { Vehicle(it.x, it.y, it.levelDb.toInt()) }

    private suspend fun pullCells(experimentId: String, expression: String): List<Cell> {
        val outcome = evaluate(experimentId, expression)
        return if (outcome is Outcome.Ok) parseTriples(outcome.content) else emptyList()
    }

    private suspend fun pullPolygons(experimentId: String, expression: String): List<List<Point>> {
        val outcome = evaluate(experimentId, expression)
        if (outcome !is Outcome.Ok) return emptyList()
        return runCatching {
            val outer = JSONArray(outcome.content)
            buildList(outer.length()) {
                for (i in 0 until outer.length()) {
                    val ring = outer.optJSONArray(i) ?: continue
                    val points = ArrayList<Point>(ring.length())
                    for (j in 0 until ring.length()) {
                        val p = ring.optJSONArray(j) ?: continue
                        points += Point(p.optDouble(0), p.optDouble(1))
                    }
                    if (points.size >= 2) add(points)
                }
            }
        }.getOrDefault(emptyList())
    }

    data class Cell(val x: Double, val y: Double, val levelDb: Double)

    suspend fun stop(experimentId: String, timeoutMs: Long = 60_000): Outcome =
        command(JSONObject().put("type", "stop").put("exp_id", experimentId), timeoutMs)

    /**
     * Sends one command and waits for the answer that concludes it.
     *
     * Serialised, because the server correlates nothing: replies carry no request
     * id, so the only way to know which command an answer belongs to is to have
     * only one outstanding.
     */
    private suspend fun command(payload: JSONObject, timeoutMs: Long): Outcome = turn.withLock {
        val ws = socket ?: return Outcome.Failed("NotConnected", "No server connection")
        while (incoming.tryReceive().isSuccess) Unit   // drop anything left from before
        if (!ws.send(payload.toString())) {
            return Outcome.Failed("SendFailed", "The connection is closed")
        }
        val answer = withTimeoutOrNull(timeoutMs) {
            while (true) {
                val message = incoming.receive()
                val type = message.optString("type")
                if (type in TERMINAL) return@withTimeoutOrNull message
            }
            @Suppress("UNREACHABLE_CODE") null
        } ?: return Outcome.Failed("Timeout", "No answer within ${timeoutMs / 1000}s")

        val type = answer.optString("type")
        val content = answer.opt("content")?.toString().orEmpty()
        return if (type == SUCCESS) Outcome.Ok(content) else Outcome.Failed(type, content)
    }

    companion object {

        /** `[[x, y, v], ...]`, which is what a `collect` of lists serialises to. */
        fun parseTriples(content: String): List<Cell> = runCatching {
            val array = JSONArray(content)
            buildList(array.length()) {
                for (i in 0 until array.length()) {
                    val row = array.optJSONArray(i) ?: continue
                    if (row.length() < 2) continue
                    add(
                        Cell(
                            x = row.optDouble(0),
                            y = row.optDouble(1),
                            levelDb = if (row.length() > 2) row.optDouble(2) else 0.0,
                        )
                    )
                }
            }
        }.getOrDefault(emptyList())

        private const val GREETING = "ConnectionSuccessful"
        private const val SUCCESS = "CommandExecutedSuccessfully"
        private val TERMINAL = setOf(
            SUCCESS, "GamaServerError", "MalformedRequest",
            "UnableToExecuteRequest", "SimulationError", "RuntimeError",
        )

        /**
         * The display-free experiment of `hanoi_noise.gaml`. Loading the GUI one
         * wedges the server; see the class documentation.
         */
        const val HEADLESS_EXPERIMENT = "check"

        /** What the screen reads back after each step, in the model's own terms. */
        val INDICATORS = listOf(
            Indicator("Mean level", "mean_dB"),
            Indicator("Peak level", "peak_dB"),
            Indicator("Residual ambience", "ambient_dB"),
            Indicator("Above QCVN day", "exceed_qcvn"),
            Indicator("Above QCVN night", "exceed_night"),
            Indicator("Vehicles", "n_vehicles"),
            Indicator("Flow (veh/min)", "flow_now"),
            Indicator("Active construction", "constr_active"),
            Indicator("Cycle", "cycle"),
        )
    }
}
