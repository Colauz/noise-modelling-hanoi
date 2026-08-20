package org.noisehanoi.mobile.settings

import android.content.Context
import androidx.core.content.edit
import org.noisehanoi.mobile.BuildConfig
import org.json.JSONObject
import org.noisehanoi.mobile.odk.InstanceXml
import org.noisehanoi.mobile.odk.OpenRosaClient

/**
 * Server configuration and the two things that are properties of the handset:
 * the microphone offset, and whether this device's readings are comparable to
 * the campaign's.
 */
class Settings(context: Context) {

    private val prefs = context.getSharedPreferences("noise_hanoi", Context.MODE_PRIVATE)

    var serverUrl: String
        get() = prefs.getString(KEY_SERVER, DEFAULT_SERVER) ?: DEFAULT_SERVER
        set(value) = prefs.edit { putString(KEY_SERVER, value.trim()) }

    /**
     * Kobo account that owns the project, and in anonymous mode the only thing
     * that says where a submission goes: KoBoCAT routes on the path,
     * `/<username>/submission`. It is an address, not a credential — a submission
     * is not attributed to that account's owner, it is delivered to their project.
     * Empty falls back to `/submission`, which needs authentication to resolve.
     */
    var username: String
        get() = prefs.getString(KEY_USERNAME, DEFAULT_USERNAME) ?: DEFAULT_USERNAME
        set(value) = prefs.edit { putString(KEY_USERNAME, value.trim()) }

    var password: String
        get() = prefs.getString(KEY_PASSWORD, "") ?: ""
        set(value) = prefs.edit { putString(KEY_PASSWORD, value) }

    var token: String
        get() = prefs.getString(KEY_TOKEN, "") ?: ""
        set(value) = prefs.edit { putString(KEY_TOKEN, value.trim()) }

    /** Default answer to the form's `collector` question. */
    var collector: String
        get() = prefs.getString(KEY_COLLECTOR, "") ?: ""
        set(value) = prefs.edit { putString(KEY_COLLECTOR, value) }

    /**
     * The whole of this handset's absolute calibration, in dB, added to the
     * measured full-scale level.
     *
     * The default is a plausible constant for a consumer handset and nothing
     * more. Leaving it at the default does not make the reading absolute; it
     * makes it a number on an arbitrary scale that is still perfectly usable for
     * the contrasts this project actually claims. See `docs/metrology.md`.
     */
    var micOffsetDb: Float
        get() = prefs.getFloat(KEY_OFFSET, DEFAULT_OFFSET_DB).coerceIn(OFFSET_RANGE)
        set(value) = prefs.edit { putFloat(KEY_OFFSET, value.coerceIn(OFFSET_RANGE)) }

    /**
     * Submit the app-measured level and device metadata alongside the form's own
     * fields. Turn on only once a form carrying those fields is deployed: Kobo
     * validates the instance against the deployed form, and an unknown element
     * is a rejected submission.
     */
    var extendedForm: Boolean
        get() = prefs.getBoolean(KEY_EXTENDED, false)
        set(value) = prefs.edit { putBoolean(KEY_EXTENDED, value) }

    /** Whether the level typed into `noise_db` came from the app or from a meter app. */
    var useInAppMeter: Boolean
        get() = prefs.getBoolean(KEY_USE_METER, true)
        set(value) = prefs.edit { putBoolean(KEY_USE_METER, value) }

    /**
     * Public collection mode: the app is in the hands of someone who is not on
     * the team. The collector question stops offering three strangers' first
     * names, and submissions are filed under `public`.
     */
    var publicMode: Boolean
        get() = prefs.getBoolean(KEY_PUBLIC, false)
        set(value) = prefs.edit { putBoolean(KEY_PUBLIC, value) }

    /**
     * A random identifier minted on this phone at first use, and never anything
     * else.
     *
     * Not a hardware id, not an advertising id, not a name. It exists because the
     * pipeline needs to tell one contributor's stream of points from another's —
     * to hold a per-device calibration offset, and to spot a flood — and because
     * `collector` alone cannot do that once everyone is `public`. The published
     * dataset carries no collector name and no device identifier today
     * (`docs/data-sources.md`), and this must not change that: it belongs in the
     * raw Kobo export, which is never distributed.
     */
    val contributorId: String
        get() = prefs.getString(KEY_CONTRIBUTOR, null) ?: java.util.UUID.randomUUID().toString()
            .also { prefs.edit { putString(KEY_CONTRIBUTOR, it) } }

    /**
     * What the server said about the forms it has deployed, keyed by form name.
     *
     * Held rather than derived because a submission has to name the deployed
     * form's own identifier, which only the server knows, and the phone must be
     * able to fill a form in a street with no network. Refreshed from Settings.
     */
    fun rememberDeployedForms(forms: List<OpenRosaClient.DeployedForm>) {
        val json = JSONObject()
        forms.forEach { form ->
            json.put(
                form.name,
                JSONObject().put("formId", form.formId).put("version", form.version),
            )
        }
        prefs.edit { putString(KEY_DEPLOYED, json.toString()) }
    }

    fun deployedForm(name: String): InstanceXml.Deployment? {
        val raw = prefs.getString(KEY_DEPLOYED, null) ?: return null
        return runCatching {
            val entry = JSONObject(raw).optJSONObject(name) ?: return null
            InstanceXml.Deployment(
                formId = entry.getString("formId"),
                version = entry.optString("version"),
            )
        }.getOrNull()
    }

    fun deployedFormNames(): List<String> {
        val raw = prefs.getString(KEY_DEPLOYED, null) ?: return emptyList()
        return runCatching { JSONObject(raw).keys().asSequence().toList() }.getOrDefault(emptyList())
    }

    /**
     * Which version of the consent text this contributor accepted, 0 for none.
     *
     * A version rather than a flag, so that a material change to what is
     * collected can ask again instead of relying on an agreement given to a
     * different set of facts.
     */
    var acceptedConsentVersion: Int
        get() = prefs.getInt(KEY_CONSENT, 0)
        set(value) = prefs.edit { putInt(KEY_CONSENT, value) }

    val hasConsented: Boolean get() = acceptedConsentVersion >= CONSENT_VERSION

    /**
     * Where a `gama-server` is listening, and where its copy of the model lives.
     *
     * Both are properties of the server, not of the phone: the model path is read
     * on the machine running GAMA. `10.0.2.2` is the host as seen from an Android
     * emulator; a real phone needs the machine's address on the network it shares.
     */
    var gamaServerUrl: String
        get() = prefs.getString(KEY_GAMA_URL, defaultGamaUrl()) ?: defaultGamaUrl()
        set(value) = prefs.edit { putString(KEY_GAMA_URL, value.trim()) }

    var gamaModelPath: String
        get() = prefs.getString(KEY_GAMA_MODEL, DEFAULT_GAMA_MODEL) ?: DEFAULT_GAMA_MODEL
        set(value) = prefs.edit { putString(KEY_GAMA_MODEL, value.trim()) }

    fun openRosaConfig() = OpenRosaClient.Config(
        serverUrl = serverUrl,
        username = username.ifBlank { null },
        password = password.ifBlank { null },
        token = token.ifBlank { null },
    )

    companion object {
        const val DEFAULT_SERVER = "https://kc.kobotoolbox.org"

        /**
         * Set at build time with `-Pnoisehanoi.koboUser=`, empty otherwise. See
         * the comment on `defaultConfig` in `app/build.gradle.kts` for why it is
         * not a constant in the source.
         */
        val DEFAULT_USERNAME: String get() = BuildConfig.DEFAULT_KOBO_USER

        /**
         * Full-scale sine on a typical handset lands near 94 dB SPL. It is a
         * starting point for a slider, not a calibration.
         */
        const val DEFAULT_OFFSET_DB = 94.0f

        /**
         * The range the offset may take, enforced in one place.
         *
         * It has to hold anything the calibration screen can produce, or applying
         * a calibration would store a value the slider cannot show — and the first
         * touch of that slider would silently overwrite the calibration with its
         * own maximum. Wide, because a quiet handset calibrated against a loud
         * street legitimately lands well outside the plausible middle.
         */
        val OFFSET_RANGE = 40f..160f

        private const val KEY_SERVER = "server_url"
        private const val KEY_USERNAME = "username"
        private const val KEY_PASSWORD = "password"
        private const val KEY_TOKEN = "token"
        private const val KEY_COLLECTOR = "collector"
        private const val KEY_OFFSET = "mic_offset_db"
        private const val KEY_EXTENDED = "extended_form"
        private const val KEY_USE_METER = "use_in_app_meter"
        private const val KEY_PUBLIC = "public_mode"
        private const val KEY_CONTRIBUTOR = "contributor_id"
        private const val KEY_DEPLOYED = "deployed_forms"
        private const val KEY_CONSENT = "accepted_consent_version"
        private const val KEY_GAMA_URL = "gama_server_url"
        private const val KEY_GAMA_MODEL = "gama_model_path"

        /**
         * `10.0.2.2` is the host machine *as an emulator sees it*, and nothing at
         * all on a real handset — where it fails with a connection error that
         * says nothing about why. So it is offered only where it means something;
         * a phone starts blank and is told what to fill in, because only the user
         * knows the address of the machine running the server.
         */
        fun defaultGamaUrl(): String =
            if (isEmulator()) "ws://10.0.2.2:6868" else ""

        private fun isEmulator(): Boolean =
            android.os.Build.FINGERPRINT.startsWith("generic") ||
                android.os.Build.FINGERPRINT.contains("emulator", ignoreCase = true) ||
                android.os.Build.PRODUCT.startsWith("sdk_")
        const val DEFAULT_GAMA_MODEL = "simulation/gama/hanoi_noise.gaml"

        /** Raise this whenever the consent text's *facts* change, not its wording. */
        const val CONSENT_VERSION = 1
    }
}
