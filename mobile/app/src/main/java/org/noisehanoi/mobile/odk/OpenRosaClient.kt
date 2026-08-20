package org.noisehanoi.mobile.odk

import okhttp3.Credentials
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * The OpenRosa half of ODK Collect, which is all a submitting client needs.
 *
 * - `GET  <server>/formList`   — used only to test a configuration.
 * - `POST <server>/submission` — `multipart/form-data` carrying the instance in a
 *   part named `xml_submission_file`, plus one part per attachment named after
 *   the file. `X-OpenRosa-Version: 1.0` is required; a compliant server answers
 *   201 Created.
 *
 * KoBoCAT accepts unauthenticated submissions only when the receiving account has
 * `require_auth` turned off — which is what a public APK needs, and also what
 * makes the endpoint spammable. See `mobile/PLAN.md`.
 */
class OpenRosaClient(
    private val http: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(120, TimeUnit.SECONDS)   // audio clips over a field connection
        .readTimeout(60, TimeUnit.SECONDS)
        .build(),
) {

    data class Config(
        val serverUrl: String,
        /** Kobo username. Present: submit to `/<user>/submission`. Absent: `/submission`. */
        val username: String? = null,
        val password: String? = null,
        /** Kobo API token, used instead of basic auth when set. */
        val token: String? = null,
    )

    sealed interface Outcome {
        /** Accepted (201), or already known to the server (202) — nothing more to do. */
        data class Accepted(val code: Int, val message: String) : Outcome

        /** The server said no and will say no again. Do not retry. */
        data class Rejected(val code: Int, val message: String) : Outcome

        /** Network, timeout or 5xx. Retry later. */
        data class Retryable(val message: String) : Outcome
    }

    fun submit(config: Config, instanceXml: File, attachments: List<File>): Outcome {
        val body = MultipartBody.Builder().setType(MultipartBody.FORM)
            .addFormDataPart(
                "xml_submission_file", "submission.xml",
                instanceXml.asRequestBody(XML),
            )
            .apply {
                for (f in attachments) {
                    addFormDataPart(f.name, f.name, f.asRequestBody(guessMediaType(f)))
                }
            }
            .build()

        val request = Request.Builder()
            .url(submissionUrl(config))
            .post(body)
            .header("X-OpenRosa-Version", "1.0")
            .header("Accept-Encoding", "gzip")
            .apply { authorization(config)?.let { header("Authorization", it) } }
            .build()

        return try {
            http.newCall(request).execute().use { response ->
                val text = response.body.string().take(500)
                when {
                    response.code == 201 || response.code == 202 -> Outcome.Accepted(response.code, text)
                    response.code in 500..599 -> Outcome.Retryable("HTTP ${response.code}: $text")
                    else -> Outcome.Rejected(response.code, text)
                }
            }
        } catch (e: IOException) {
            Outcome.Retryable(e.message ?: e.javaClass.simpleName)
        }
    }

    /**
     * One form as the server has it deployed.
     *
     * [formId] is the thing that matters and the thing you cannot guess. Kobo does
     * not keep the `id_string` from the XLSForm: on deployment it assigns the
     * asset's own identifier, something like `aA8FaTuUVSkRjbUW7rCBz7`, and that is
     * what the instance's root element and `id` attribute have to be. Submitting
     * under the XLSForm's own name gets a 404 — a form the server has never heard
     * of — which is indistinguishable, from the phone, from a wrong URL.
     *
     * [version] changes on every redeployment, which is the second reason this is
     * read rather than compiled in.
     */
    data class DeployedForm(
        val formId: String,
        val name: String,
        val version: String,
        val downloadUrl: String,
    )

    /** Reads `/formList`. Empty when the server answered but listed nothing. */
    fun formList(config: Config): Result<List<DeployedForm>> = runCatching {
        val request = Request.Builder()
            .url(joinUrl(config.serverUrl, formListPath(config)))
            .get()
            .header("X-OpenRosa-Version", "1.0")
            .apply { authorization(config)?.let { header("Authorization", it) } }
            .build()
        http.newCall(request).execute().use { response ->
            val body = response.body.string()
            if (!response.isSuccessful) error("HTTP ${response.code}: ${body.take(200)}")
            parseFormList(body)
        }
    }

    /** Fetches `/formList`, so Settings can tell "wrong URL" from "wrong password". */
    fun checkConnection(config: Config): Outcome {
        val request = Request.Builder()
            .url(joinUrl(config.serverUrl, formListPath(config)))
            .get()
            .header("X-OpenRosa-Version", "1.0")
            .apply { authorization(config)?.let { header("Authorization", it) } }
            .build()
        return try {
            http.newCall(request).execute().use { response ->
                when {
                    response.isSuccessful -> Outcome.Accepted(response.code, "OK")
                    response.code in 500..599 -> Outcome.Retryable("HTTP ${response.code}")
                    else -> Outcome.Rejected(response.code, response.message)
                }
            }
        } catch (e: IOException) {
            Outcome.Retryable(e.message ?: e.javaClass.simpleName)
        }
    }

    private fun authorization(config: Config): String? = when {
        !config.token.isNullOrBlank() -> "Token ${config.token}"
        !config.username.isNullOrBlank() && !config.password.isNullOrBlank() ->
            Credentials.basic(config.username, config.password)
        else -> null   // anonymous, which the receiving account has to allow
    }

    private fun submissionUrl(config: Config): String =
        joinUrl(config.serverUrl, submissionPath(config))

    private fun submissionPath(config: Config): String =
        if (config.username.isNullOrBlank()) "submission" else "${config.username}/submission"

    private fun formListPath(config: Config): String =
        if (config.username.isNullOrBlank()) "formList" else "${config.username}/formList"

    companion object {
        val XML = "text/xml".toMediaType()

        /**
         * Pulled out and kept string-based on purpose: the payload is a short,
         * flat OpenRosa document, and a regex over it is testable on the JVM
         * without an XML parser or an emulator.
         */
        fun parseFormList(xml: String): List<DeployedForm> =
            Regex("<xform>(.*?)</xform>", RegexOption.DOT_MATCHES_ALL)
                .findAll(xml)
                .mapNotNull { match ->
                    val block = match.groupValues[1]
                    fun tag(name: String) =
                        Regex("<$name>(.*?)</$name>", RegexOption.DOT_MATCHES_ALL)
                            .find(block)?.groupValues?.get(1)?.trim()
                    val id = tag("formID") ?: return@mapNotNull null
                    DeployedForm(
                        formId = id,
                        name = tag("name").orEmpty(),
                        version = tag("version").orEmpty(),
                        downloadUrl = tag("downloadUrl").orEmpty(),
                    )
                }
                .toList()

        fun joinUrl(base: String, path: String): String =
            base.trimEnd('/') + "/" + path.trimStart('/')

        fun guessMediaType(file: File) = when (file.extension.lowercase()) {
            "m4a", "mp4a" -> "audio/mp4".toMediaType()
            "3gp" -> "audio/3gpp".toMediaType()
            "amr" -> "audio/amr".toMediaType()
            "jpg", "jpeg" -> "image/jpeg".toMediaType()
            "png" -> "image/png".toMediaType()
            "xml" -> XML
            else -> "application/octet-stream".toMediaType()
        }
    }
}
