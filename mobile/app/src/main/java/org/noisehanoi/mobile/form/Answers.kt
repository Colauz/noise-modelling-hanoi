package org.noisehanoi.mobile.form

/**
 * A GPS fix as the form needs it: ODK writes `lat lon altitude accuracy`.
 *
 * [timeMillis] is when the platform says the fix was taken, which is not when we
 * received it. `getLastKnownLocation` will hand back a position from hours ago
 * without comment, and a stale fix with a good accuracy figure will beat a fresh
 * one on every test that looks only at accuracy — right up to the point where it
 * is submitted as the place a measurement was taken.
 */
data class GeoPoint(
    val latitude: Double,
    val longitude: Double,
    val altitude: Double = 0.0,
    val accuracyM: Double = 0.0,
    val timeMillis: Long = 0L,
) {
    fun toOdkValue(): String = "$latitude $longitude $altitude $accuracyM"

    fun ageMillis(now: Long = System.currentTimeMillis()): Long = now - timeMillis
}

/** An attachment already written to disk, referenced by name from the instance. */
data class Attachment(val fieldName: String, val fileName: String, val absolutePath: String)

/**
 * Answers to one filling of a form.
 *
 * Immutable, and that is the whole point. The first version held a mutable map
 * and published a revision counter so the screen could know something had
 * changed; the screen keyed each question on that counter, which meant every
 * keystroke tore down and rebuilt the text field the user was typing in, and the
 * field lost focus after each character. A value class that returns a copy lets
 * Compose compare old and new by itself and redraw only what moved.
 *
 * Values are held in the exact lexical form they will take in the instance XML,
 * so what is validated on screen is what is submitted.
 */
data class Answers(
    val spec: FormSpec,
    val values: Map<String, String> = emptyMap(),
    val attachments: Map<String, Attachment> = emptyMap(),
) {
    operator fun get(name: String): String? = values[name]

    /** Blank clears the answer: an unanswered question emits no element at all. */
    fun with(name: String, value: String?): Answers =
        if (value.isNullOrBlank()) copy(values = values - name)
        else copy(values = values + (name to value))

    fun withGeoPoint(name: String, point: GeoPoint?): Answers =
        with(name, point?.toOdkValue())

    fun withAttachment(attachment: Attachment): Answers = copy(
        values = values + (attachment.fieldName to attachment.fileName),
        attachments = attachments + (attachment.fieldName to attachment),
    )

    /** The attachment this field held before [withAttachment] replaced it, if any. */
    fun previousAttachment(fieldName: String): Attachment? = attachments[fieldName]

    /** Field names whose answer is missing or outside the XLSForm constraint. */
    fun problems(): Map<String, String> {
        val out = LinkedHashMap<String, String>()
        for (q in spec.questions) {
            val raw = values[q.name]
            if (raw.isNullOrBlank()) {
                if (q.required) out[q.name] = "Required"
                continue
            }
            when (q) {
                is DecimalQ -> {
                    val v = raw.toDoubleOrNull()
                    if (v == null) out[q.name] = "Not a number"
                    else if (v < q.min || v > q.max) out[q.name] = "Must be between ${fmt(q.min)} and ${fmt(q.max)}"
                }
                is IntegerQ -> {
                    val v = raw.toIntOrNull()
                    if (v == null) out[q.name] = "Not a whole number"
                    else if (v < q.min || v > q.max) out[q.name] = "Must be between ${q.min} and ${q.max}"
                }
                is SelectOneQ ->
                    if (q.choices.none { it.name == raw }) out[q.name] = "Unknown choice"
                else -> Unit
            }
        }
        return out
    }

    val isComplete: Boolean get() = problems().isEmpty()

    private fun fmt(v: Double) = if (v == v.toLong().toDouble()) v.toLong().toString() else v.toString()
}

/**
 * Normalises what a numeric keyboard can produce into what XML expects.
 *
 * A decimal comma is what a French or Vietnamese keyboard offers, and rejecting
 * it as "not a number" would be an app telling its users their own locale is a
 * typing mistake. ODK instances are always written with a point.
 */
fun normaliseNumber(input: String): String = input.replace(',', '.').trim()
