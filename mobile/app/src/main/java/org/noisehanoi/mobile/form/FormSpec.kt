package org.noisehanoi.mobile.form

/**
 * The two survey instruments, transcribed from the XLSForms in `data/forms/`.
 *
 * This is deliberately not a general XForm engine. Rendering an arbitrary XForm
 * is what JavaRosa does for ODK Collect, and it is a large dependency and a
 * large surface. Both of our forms are frozen — the campaign is closed and v2 is
 * final — so the questions live here as data, the screens render them natively,
 * and `InstanceXml` emits an instance the deployed form accepts. A form change
 * costs one app release, which is the trade we chose.
 *
 * Question names, choice names, ordering and constraints must stay identical to
 * the XLSForm. Kobo validates the instance against the deployed form: a renamed
 * field is a rejected submission, not a warning.
 */

data class Choice(val name: String, val label: String)

sealed interface Question {
    val name: String
    val label: String
    val required: Boolean
    val hint: String?
}

data class SelectOneQ(
    override val name: String,
    override val label: String,
    val choices: List<Choice>,
    override val required: Boolean = false,
    override val hint: String? = null,
) : Question

data class DecimalQ(
    override val name: String,
    override val label: String,
    val min: Double,
    val max: Double,
    override val required: Boolean = false,
    override val hint: String? = null,
) : Question

data class IntegerQ(
    override val name: String,
    override val label: String,
    val min: Int,
    val max: Int,
    override val required: Boolean = false,
    override val hint: String? = null,
) : Question

data class TextQ(
    override val name: String,
    override val label: String,
    override val required: Boolean = false,
    override val hint: String? = null,
) : Question

data class GeoPointQ(
    override val name: String,
    override val label: String,
    override val required: Boolean = true,
    override val hint: String? = null,
) : Question

/** An attachment question: audio clip, photo. The instance carries the filename. */
data class MediaQ(
    override val name: String,
    override val label: String,
    val kind: MediaKind,
    override val required: Boolean = false,
    override val hint: String? = null,
) : Question

enum class MediaKind { AUDIO, IMAGE }

data class FormSpec(
    /** `id_string` from the XLSForm settings sheet. Also the instance root node name. */
    val id: String,
    /** `version` from the XLSForm settings sheet. */
    val version: String,
    val title: String,
    val questions: List<Question>,
) {
    /**
     * The same form, with the audio clip optional.
     *
     * The clip is never allowed to block a submission, in either mode. It was
     * required of the team at first, on the reasoning that it lets a doubtful
     * measurement be revisited — which is true, and still not worth what it
     * costs when it fails. The app measures the level itself; the clip is
     * corroboration. Making it mandatory meant that any hiccup in the encoder,
     * on any handset, stranded someone in a street with a form they could not
     * send and no way to understand why. That happened on the first real phone
     * this ran on.
     *
     * What the two modes still decide is whether a clip is *made*: across a
     * public campaign it would be 209 kB a submission — some 10 GB for fifty
     * thousand — of recordings nobody will play back, each of which may have
     * caught a passing conversation.
     */
    fun withOptionalAudio(): FormSpec = copy(
        questions = questions.map {
            if (it is MediaQ && it.kind == MediaKind.AUDIO) it.copy(required = false) else it
        }
    )
}

// --- choice lists (XLSForm `choices` sheet) ---------------------------------

val SITES = listOf(
    Choice("hoan_kiem", "Hoan Kiem lake"),
    Choice("vinh_tuy", "Vinh Tuy area"),
    Choice("ocean_park", "Ocean Park"),
    Choice("other_site", "Other"),
)

/**
 * The deployed v2 list is three first names — the right list for a team of three,
 * and the wrong one for a public campaign, where it asks a stranger to file
 * themselves under someone else's name. [PUBLIC_COLLECTOR] is the honest bucket.
 *
 * The field is not decoration: `01_prepare_field_data.py` keys its per-collector
 * calibration offset and its de-duplication on it, so it has to stay a real
 * value, not be emptied.
 */
val COLLECTORS = listOf(
    Choice("lucas", "Lucas"),
    Choice("laurian", "Laurian"),
    Choice("quang", "Quang"),
    Choice(PUBLIC_COLLECTOR, "Public contributor (mobile app)"),
)

/** Choice name for anyone who is not one of the three named collectors. */
const val PUBLIC_COLLECTOR = "public"

val CATEGORIES = listOf(
    Choice("xe_may_motorbike", "Motorbike (xe may)"),
    Choice("car_or_truck", "Car or truck"),
    Choice("motor_vehicle_horn", "Vehicle horn / honking"),
    Choice("construction_site", "Construction site (drilling, hammering...)"),
    Choice("street_vendor", "Street vendor / hawker"),
    Choice("karaoke_restaurant", "Karaoke / restaurant / bar"),
    Choice("crowd_noise", "Crowd noise"),
    Choice("school", "School"),
    Choice("animal", "Animal"),
    Choice("silence", "Silence / quiet ambient"),
    Choice("transportation", "Transportation noise"),
    Choice("other", "Other"),
)

val PHONE_ORIENTATIONS = listOf(
    Choice("vertical", "Vertical"),
    Choice("horizontal", "Horizontal"),
)

val MIC_DIRECTIONS = listOf(
    Choice("towards", "Pointing towards the source"),
    Choice("perpendicular", "Perpendicular to the source"),
    Choice("away", "Back to the source"),
    Choice("above_below", "Source above or below"),
)

val YES_NO = listOf(Choice("yes", "Yes"), Choice("no", "No"))

val DISTANCE_BANDS = listOf(
    Choice("d_0_2", "0-2 m (roadside)"),
    Choice("d_2_10", "2-10 m"),
    Choice("d_10_30", "10-30 m"),
    Choice("d_30_60", "30-60 m"),
    Choice("d_60plus", "> 60 m / behind building"),
)

val CONSTRUCTION_TYPES = listOf(
    Choice("construction", "Construction"),
    Choice("demolition", "Demolition / destruction"),
    Choice("renovation", "Renovation / street works"),
)

val ACTIVITY_LEVELS = listOf(
    Choice("active_loud", "Active and loud (drilling, hammering...)"),
    Choice("active_quiet", "Active but quiet"),
    Choice("inactive", "Inactive (pause, night)"),
)

// --- the forms --------------------------------------------------------------

/**
 * `hanoi_noise_form_v2.xlsx`. The `video_traffic` question is omitted: in-app
 * video capture is not in phase 1, and the field is optional in the form.
 */
val NOISE_FORM_V2 = FormSpec(
    id = "hanoi_noise_v1",
    version = "2026061204",
    title = "Hanoi Urban Noise Survey",
    questions = listOf(
        SelectOneQ("site", "Study site", SITES, required = true),
        SelectOneQ("collector", "Who is collecting?", COLLECTORS, required = true),
        GeoPointQ(
            "location", "GPS location (wait for accuracy < 10 m)",
            hint = "Stand still a few seconds for better accuracy",
        ),
        MediaQ(
            "audio_sample", "Audio recording (>= 10 seconds)", MediaKind.AUDIO,
            required = true, hint = "Record at least 10 s of ambient sound",
        ),
        DecimalQ(
            "noise_db", "Noise level (dB) from sound meter app", 20.0, 120.0,
            required = true, hint = "Read LAeq / average value from the dB app",
        ),
        SelectOneQ(
            "noise_class", "Main noise category", CATEGORIES,
            required = true, hint = "Dominant sound source",
        ),
        SelectOneQ("dist_to_road", "Approx. distance to nearest road", DISTANCE_BANDS, required = true),
        TextQ("note", "Note (optional)", hint = "Unusual events: horn burst, rain, festival..."),
        SelectOneQ("phone_orientation", "Phone held", PHONE_ORIENTATIONS),
        SelectOneQ("mic_to_source", "Mic relative to the main source", MIC_DIRECTIONS),
        DecimalQ(
            "dist_to_source_m", "Estimated distance to the MAIN source (m)", 0.0, 1000.0,
            hint = "The dominant source selected in \"Main noise category\"",
        ),
        IntegerQ(
            "count_motorbikes", "Motorbikes passing during measurement", 0, 500,
            hint = "Count during the ~15 s of measurement (estimate if many)",
        ),
        IntegerQ("count_cars", "Cars passing during measurement", 0, 500),
        IntegerQ("count_heavy", "Buses / trucks passing during measurement", 0, 500),
        IntegerQ("count_ev", "Of which electric vehicles (VinFast taxis, e-bikes...)", 0, 500),
        SelectOneQ(
            "construction_nearby", "Construction/demolition audible from here?", YES_NO,
            hint = "If yes and not yet logged, also fill the \"Construction sites\" form",
        ),
    ),
)

/** `hanoi_construction_form.xlsx`. */
val CONSTRUCTION_FORM_V1 = FormSpec(
    id = "hanoi_construction_v1",
    version = "2026061203",
    title = "Hanoi Construction Sites Log",
    questions = listOf(
        SelectOneQ("collector", "Who is logging?", COLLECTORS, required = true),
        GeoPointQ(
            "site_location", "Construction site location (stand at the edge)",
            hint = "Then take 2-3 NORMAL measurements walking away — the radius is computed from those",
        ),
        SelectOneQ("site_type", "Type", CONSTRUCTION_TYPES, required = true),
        SelectOneQ("activity_level", "Activity level right now", ACTIVITY_LEVELS, required = true),
        MediaQ("site_photo", "Photo of the site", MediaKind.IMAGE),
        TextQ("description", "Description (what is being built/demolished, machinery...)"),
    ),
)

/**
 * Fields the app records that the deployed v2 form does not have: the level
 * measured by *this app's microphone*, and what measured it.
 *
 * They are a separate quantity from `noise_db`, which is a trimmed Decibel X
 * reading from one of three cross-calibrated handsets. An arbitrary phone's
 * microphone departs from a reference by several decibels, in a way that depends
 * on handset, OS and level, and is not a constant offset — see
 * `docs/metrology.md`. Merging the two columns would silently corrupt the only
 * dataset this project has.
 *
 * These are emitted only when [org.noisehanoi.mobile.settings.Settings.extendedForm]
 * is on, i.e. once a v3 form carrying them is deployed on Kobo. Until then the
 * app submits a strictly v2-conformant instance and keeps the app-measured value
 * locally.
 */
val APP_EXTENSION_FIELDS = listOf(
    "app_noise_db", "measure_method", "device_model", "os_version", "app_version", "contributor_id",
)

/**
 * Version of `mobile/forms/hanoi_noise_app_v3.xlsx`, the form that carries
 * [APP_EXTENSION_FIELDS]. Same `id_string` as v2, so Kobo treats it as a new
 * version of the same form and the project keeps its submissions.
 *
 * Must equal `VERSION` in `mobile/forms/build_app_form.py`: an instance declares
 * its version, and Kobo checks it.
 */
const val NOISE_FORM_V3_VERSION = "2026082002"
